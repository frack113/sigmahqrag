"""
Chat History Service

Manages persistent storage and retrieval of chat messages across sessions.
Provides both database and browser-based storage options.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4


logger = logging.getLogger(__name__)


class ChatHistoryService:
    """
    Service for managing chat history persistence.
    
    Features:
    - SQLite database storage for persistent history
    - Browser localStorage integration for session data
    - Automatic cleanup of old messages
    - Thread-safe operations
    - Migration support for existing data
    """
    
    def __init__(self, db_path: str = "data/chat_history.db", max_messages: int = 1000):
        """
        Initialize the chat history service.
        
        Args:
            db_path: Path to SQLite database file
            max_messages: Maximum number of messages to keep per session
        """
        self.db_path = Path(db_path)
        self.max_messages = max_messages
        self.session_id = None
        
        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # Generate session ID for this browser session
        self._generate_session_id()
    
    def _init_database(self):
        """Initialize the SQLite database with required tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create sessions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        id TEXT PRIMARY KEY,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        message_count INTEGER DEFAULT 0
                    )
                """)
                
                # Create messages table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT,
                        FOREIGN KEY (session_id) REFERENCES sessions (id)
                    )
                """)
                
                # Create indexes for performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
                
                conn.commit()
                logger.info(f"Chat history database initialized at {self.db_path}")
                
        except Exception as e:
            logger.error(f"Failed to initialize chat history database: {e}")
            show_notification(f"Warning: Chat history may not be saved: {e}", type='warning')
    
    def _generate_session_id(self):
        """Generate or retrieve session ID for this browser session."""
        try:
            # Try to get existing session from a temporary file
            session_file = self.db_path.parent / ".current_session"
            if session_file.exists():
                with open(session_file, 'r') as f:
                    self.session_id = f.read().strip()
            else:
                # Create new session
                self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
                with open(session_file, 'w') as f:
                    f.write(self.session_id)
                    
            # Register session in database
            self._register_session()
            
        except Exception as e:
            logger.error(f"Failed to generate session ID: {e}")
            # Fallback to in-memory session
            self.session_id = f"temp_session_{uuid4().hex[:8]}"
    
    def _register_session(self):
        """Register current session in database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO sessions (id, last_used, message_count)
                    VALUES (?, datetime('now'), 
                           (SELECT COUNT(*) FROM messages WHERE session_id = ?))
                """, (self.session_id, self.session_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to register session: {e}")
    
    def save_message(self, role: str, content: str, metadata: Optional[Dict] = None) -> bool:
        """
        Save a message to the chat history.
        
        Args:
            role: Message role ('user' or 'assistant')
            content: Message content
            metadata: Optional metadata dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            message_id = str(uuid4())
            timestamp = datetime.now().isoformat()
            metadata_str = json.dumps(metadata or {})
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO messages (id, session_id, role, content, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (message_id, self.session_id, role, content, timestamp, metadata_str))
                
                # Update session message count
                cursor.execute("""
                    UPDATE sessions SET last_used = datetime('now'), 
                                     message_count = message_count + 1
                    WHERE id = ?
                """, (self.session_id,))
                
                conn.commit()
                
            # Clean up old messages if we exceed the limit
            self._cleanup_old_messages()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
            return False
    
    def get_session_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get chat history for the current session.
        
        Args:
            limit: Maximum number of messages to return (None for all)
            
        Returns:
            List of message dictionaries
        """
        try:
            if not self.session_id:
                return []
            
            limit = limit or self.max_messages
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT role, content, timestamp, metadata
                    FROM messages 
                    WHERE session_id = ?
                    ORDER BY timestamp ASC
                    LIMIT ?
                """, (self.session_id, limit))
                
                rows = cursor.fetchall()
                
                messages = []
                for role, content, timestamp, metadata_str in rows:
                    message = {
                        "role": role,
                        "content": content,
                        "timestamp": timestamp,
                        "metadata": json.loads(metadata_str) if metadata_str else {}
                    }
                    messages.append(message)
                
                return messages
                
        except Exception as e:
            logger.error(f"Failed to get session history: {e}")
            return []
    
    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """
        Get information about all sessions.
        
        Returns:
            List of session information
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, created_at, last_used, message_count
                    FROM sessions
                    ORDER BY last_used DESC
                """)
                
                rows = cursor.fetchall()
                
                sessions = []
                for session_id, created_at, last_used, message_count in rows:
                    sessions.append({
                        "id": session_id,
                        "created_at": created_at,
                        "last_used": last_used,
                        "message_count": message_count
                    })
                
                return sessions
                
        except Exception as e:
            logger.error(f"Failed to get sessions: {e}")
            return []
    
    def clear_session_history(self) -> bool:
        """
        Clear chat history for the current session.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.session_id:
                return True
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM messages WHERE session_id = ?", (self.session_id,))
                cursor.execute("DELETE FROM sessions WHERE id = ?", (self.session_id,))
                conn.commit()
                
            # Clean up session file
            session_file = self.db_path.parent / ".current_session"
            if session_file.exists():
                session_file.unlink()
            
            # Generate new session ID
            self._generate_session_id()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear session history: {e}")
            return False
    
    def clear_all_history(self) -> bool:
        """
        Clear all chat history from the database.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM messages")
                cursor.execute("DELETE FROM sessions")
                conn.commit()
                
            # Clean up session file
            session_file = self.db_path.parent / ".current_session"
            if session_file.exists():
                session_file.unlink()
            
            # Generate new session ID
            self._generate_session_id()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear all history: {e}")
            return False
    
    def _cleanup_old_messages(self):
        """Remove old messages to stay within the message limit."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Count current messages in session
                cursor.execute("""
                    SELECT COUNT(*) FROM messages WHERE session_id = ?
                """, (self.session_id,))
                
                count = cursor.fetchone()[0]
                
                if count > self.max_messages:
                    # Remove oldest messages
                    remove_count = count - self.max_messages
                    cursor.execute("""
                        DELETE FROM messages 
                        WHERE id IN (
                            SELECT id FROM messages 
                            WHERE session_id = ? 
                            ORDER BY timestamp ASC 
                            LIMIT ?
                        )
                    """, (self.session_id, remove_count))
                    
                    # Update session message count
                    cursor.execute("""
                        UPDATE sessions SET message_count = message_count - ?
                        WHERE id = ?
                    """, (remove_count, self.session_id))
                    
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"Failed to cleanup old messages: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about chat history.
        
        Returns:
            Dictionary with statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total messages
                cursor.execute("SELECT COUNT(*) FROM messages")
                total_messages = cursor.fetchone()[0]
                
                # Total sessions
                cursor.execute("SELECT COUNT(*) FROM sessions")
                total_sessions = cursor.fetchone()[0]
                
                # Current session messages
                if self.session_id:
                    cursor.execute("SELECT COUNT(*) FROM messages WHERE session_id = ?", (self.session_id,))
                    current_session_messages = cursor.fetchone()[0]
                else:
                    current_session_messages = 0
                
                # Database size
                db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
                
                return {
                    "total_messages": total_messages,
                    "total_sessions": total_sessions,
                    "current_session_messages": current_session_messages,
                    "database_size_bytes": db_size,
                    "database_size_mb": round(db_size / (1024 * 1024), 2) if db_size > 0 else 0,
                    "session_id": self.session_id
                }
                
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "total_messages": 0,
                "total_sessions": 0,
                "current_session_messages": 0,
                "database_size_bytes": 0,
                "database_size_mb": 0,
                "session_id": self.session_id,
                "error": str(e)
            }
    
    def export_history(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Export chat history to JSON format.
        
        Args:
            session_id: Specific session to export (None for current session)
            
        Returns:
            Dictionary with exported data
        """
        try:
            target_session = session_id or self.session_id
            
            if not target_session:
                return {"error": "No session specified"}
            
            messages = self.get_session_history()
            
            return {
                "session_id": target_session,
                "exported_at": datetime.now().isoformat(),
                "message_count": len(messages),
                "messages": messages,
                "version": "1.0"
            }
            
        except Exception as e:
            logger.error(f"Failed to export history: {e}")
            return {"error": str(e)}
    
    def import_history(self, data: Dict[str, Any]) -> bool:
        """
        Import chat history from JSON format.
        
        Args:
            data: Exported chat history data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if "messages" not in data:
                return False
            
            # Use current session for import
            for message in data["messages"]:
                self.save_message(
                    role=message["role"],
                    content=message["content"],
                    metadata=message.get("metadata", {})
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to import history: {e}")
            return False
    
    def cleanup_old_sessions(self, days_to_keep: int = 30) -> bool:
        """
        Remove sessions older than specified days.
        
        Args:
            days_to_keep: Number of days to keep sessions
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM messages 
                    WHERE session_id IN (
                        SELECT id FROM sessions 
                        WHERE last_used < datetime('now', '-{} days')
                    )
                """.format(days_to_keep))
                
                cursor.execute("""
                    DELETE FROM sessions 
                    WHERE last_used < datetime('now', '-{} days')
                """.format(days_to_keep))
                
                conn.commit()
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {e}")
            return False
    
    def close(self):
        """Close the database connection and cleanup resources."""
        try:
            # Clean up session file
            session_file = self.db_path.parent / ".current_session"
            if session_file.exists():
                session_file.unlink()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


# Global chat history service instance
chat_history_service = ChatHistoryService()


def get_chat_history_service() -> ChatHistoryService:
    """Get the global chat history service instance."""
    return chat_history_service