"""
Database Setup and Initialization for SigmaHQ RAG Application

This module provides utilities for initializing and configuring the SQLite database
used by the SigmaHQ RAG application.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Any

from src.shared.constants import DATA_LOCAL_PATH

logger = logging.getLogger(__name__)


class DatabaseSetup:
    """Database setup and initialization utilities."""

    def __init__(self, db_path: str | Path | None = None):
        """
        Initialize database setup.

        Args:
            db_path: Path to the SQLite database file (defaults to data/local/sigmahq.db)
        """
        if db_path is None:
            db_path = DATA_LOCAL_PATH / "sigmahq.db"
        self.db_path = Path(db_path)
        self.db_dir = self.db_path.parent
        self.logger = logging.getLogger(__name__)

    def ensure_database_directory(self) -> bool:
        """
        Ensure the database directory exists.

        Returns:
            True if directory exists or was created successfully
        """
        try:
            self.db_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Database directory ensured: {self.db_dir}")
            return True
        except Exception as e:
            self.logger.error(f"Error creating database directory: {e}")
            return False

    def create_database_schema(self) -> bool:
        """
        Create the database schema with all required tables.

        Returns:
            True if schema created successfully
        """
        try:
            # Ensure database directory exists
            if not self.ensure_database_directory():
                return False

            # Connect to database (creates file if it doesn't exist)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Create chat history table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chat_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        model_used TEXT,
                        tokens_used INTEGER,
                        response_time REAL
                    )
                """)

                # Create documents table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_name TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        file_size INTEGER,
                        file_type TEXT,
                        upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                        processed BOOLEAN DEFAULT 0,
                        processing_date DATETIME,
                        chunks_count INTEGER DEFAULT 0,
                        embedding_model TEXT,
                        metadata TEXT
                    )
                """)

                # Create document chunks table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS document_chunks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        document_id INTEGER,
                        chunk_index INTEGER,
                        content TEXT NOT NULL,
                        embedding_vector TEXT,
                        metadata TEXT,
                        FOREIGN KEY (document_id) REFERENCES documents (id)
                    )
                """)

                # Create configuration table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS configuration (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        key TEXT UNIQUE NOT NULL,
                        value TEXT NOT NULL,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create logs table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS application_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        level TEXT NOT NULL,
                        logger TEXT NOT NULL,
                        message TEXT NOT NULL,
                        module TEXT,
                        function TEXT,
                        line INTEGER
                    )
                """)

                # Create GitHub repositories table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS github_repositories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        repo_name TEXT NOT NULL,
                        repo_url TEXT NOT NULL,
                        clone_url TEXT,
                        local_path TEXT,
                        last_sync DATETIME,
                        status TEXT DEFAULT 'pending',
                        error_message TEXT,
                        files_count INTEGER DEFAULT 0,
                        processed_files_count INTEGER DEFAULT 0
                    )
                """)

                # Create file operations table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS file_operations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        operation_type TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        status TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        error_message TEXT,
                        metadata TEXT
                    )
                """)

                # Create indexes for better performance
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_history(session_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_chat_timestamp ON chat_history(timestamp)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_documents_processed ON documents(processed)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_documents_upload_date ON documents(upload_date)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_chunks_document ON document_chunks(document_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_config_key ON configuration(key)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON application_logs(timestamp)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_logs_level ON application_logs(level)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_github_status ON github_repositories(status)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_file_ops_type ON file_operations(operation_type)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_file_ops_status ON file_operations(status)"
                )

                conn.commit()
                self.logger.info("Database schema created successfully")
                return True

        except Exception as e:
            self.logger.error(f"Error creating database schema: {e}")
            return False

    def insert_initial_configuration(self) -> bool:
        """
        Insert initial configuration values.

        Returns:
            True if configuration inserted successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Initial configuration values
                config_values = [
                    ("app_version", "1.0.0"),
                    ("database_version", "1.0.0"),
                    ("lm_studio_url", "http://localhost:1234"),
                    ("gradio_port", "8080"),
                    ("gradio_host", "0.0.0.0"),
                    ("default_model", "qwen/qwen3.5-9b"),
                    ("embedding_model", "text-embedding-all-minilm-l6-v2-embedding"),
                    ("chunk_size", "1000"),
                    ("chunk_overlap", "100"),
                    ("max_concurrent_uploads", "5"),
                    ("log_level", "INFO"),
                    ("auto_cleanup_logs", "true"),
                    ("max_log_age_days", "30"),
                ]

                for key, value in config_values:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO configuration (key, value, updated_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                    """,
                        (key, value),
                    )

                conn.commit()
                self.logger.info("Initial configuration inserted successfully")
                return True

        except Exception as e:
            self.logger.error(f"Error inserting initial configuration: {e}")
            return False

    def test_database_connection(self) -> bool:
        """
        Test database connection and basic operations.

        Returns:
            True if database is working correctly
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Test insert and select
                test_key = "test_connection"
                test_value = "success"

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO configuration (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """,
                    (test_key, test_value),
                )

                cursor.execute(
                    "SELECT value FROM configuration WHERE key = ?", (test_key,)
                )
                result = cursor.fetchone()

                # Clean up test data
                cursor.execute("DELETE FROM configuration WHERE key = ?", (test_key,))

                conn.commit()

                if result and result[0] == test_value:
                    self.logger.info("Database connection test successful")
                    return True
                else:
                    self.logger.error("Database connection test failed")
                    return False

        except Exception as e:
            self.logger.error(f"Database connection test failed: {e}")
            return False

    def get_database_info(self) -> dict[str, Any]:
        """
        Get information about the database.

        Returns:
            Dictionary with database information
        """
        info = {
            "database_path": str(self.db_path),
            "database_exists": self.db_path.exists(),
            "database_size": 0,
            "tables": [],
            "total_records": 0,
            "connection_test": False,
        }

        if info["database_exists"]:
            try:
                info["database_size"] = self.db_path.stat().st_size

                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()

                    # Get table names
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [row[0] for row in cursor.fetchall()]
                    info["tables"] = tables

                    # Get total records
                    total_records = 0
                    for table in tables:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        total_records += count

                    info["total_records"] = total_records

                    # Test connection
                    info["connection_test"] = self.test_database_connection()

            except Exception as e:
                self.logger.error(f"Error getting database info: {e}")

        return info

    def initialize_database(self) -> dict[str, Any]:
        """
        Complete database initialization process.

        Returns:
            Dictionary with initialization results
        """
        results = {
            "directory_created": False,
            "schema_created": False,
            "configuration_inserted": False,
            "connection_test_passed": False,
            "database_info": {},
        }

        self.logger.info("Starting database initialization...")

        # Step 1: Ensure directory exists
        results["directory_created"] = self.ensure_database_directory()

        # Step 2: Create schema
        if results["directory_created"]:
            results["schema_created"] = self.create_database_schema()

        # Step 3: Insert initial configuration
        if results["schema_created"]:
            results["configuration_inserted"] = self.insert_initial_configuration()

        # Step 4: Test connection
        if results["configuration_inserted"]:
            results["connection_test_passed"] = self.test_database_connection()

        # Get database info
        results["database_info"] = self.get_database_info()

        self.logger.info("Database initialization completed")
        return results


def setup_database() -> dict[str, Any]:
    """
    Convenience function to set up the database.

    Returns:
        Dictionary with setup results
    """
    db_setup = DatabaseSetup()
    return db_setup.initialize_database()


if __name__ == "__main__":
    # Test database setup
    results = setup_database()
    print("Database Setup Results:")
    for key, value in results.items():
        if key != "database_info":
            print(f"  {key}: {value}")

    print("\nDatabase Info:")
    for key, value in results["database_info"].items():
        print(f"  {key}: {value}")
