"""
SigmaHQ RAG - Gradio Application

Main Gradio application class that creates a single-page, tabbed interface
with async operations and streaming responses for slow local LLMs.
"""

import gradio as gr
import asyncio
import threading
import sys
import os
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
current_dir = os.getcwd()
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import core services from NiceGUI app
from src.models.config_service import ConfigService
from src.models.data_service import DataService
from src.models.logging_service import get_logger
from src.models.chat_history_service import get_chat_history_service

# Import Gradio components
from src.gradio_app.components.chat_interface import ChatInterface
from src.gradio_app.components.data_management import DataManagement
from src.gradio_app.components.github_management import GitHubManagement
from src.gradio_app.components.file_management import FileManagement
from src.gradio_app.components.config_management import ConfigManagement
from src.gradio_app.components.logs_viewer import LogsViewer

logger = get_logger(__name__)


class SigmaHQGradioApp:
    """
    Main Gradio application class for SigmaHQ RAG.
    
    Features:
    - Single-page, tabbed interface
    - Async operations for all LLM interactions
    - Streaming responses for better UX with slow LLMs
    - Browser-filling responsive layout
    - Background task management
    """
    
    def __init__(self):
        # Initialize core services (same as NiceGUI version)
        self.config_service = ConfigService()
        self.data_service = DataService()
        self.chat_history_service = get_chat_history_service()
        
        # Load configuration
        self.config = self.config_service.get_config_with_defaults()
        
        # Initialize RAG services
        self.rag_chat_service = self._initialize_rag_service()
        
        # Initialize tab components
        self.chat_interface = ChatInterface(self.rag_chat_service, self.chat_history_service)
        self.data_management = DataManagement(self.data_service, self.config_service)
        self.github_management = GitHubManagement()
        self.file_management = FileManagement()
        self.config_management = ConfigManagement(self.config_service)
        self.logs_viewer = LogsViewer()
        
        # Initialize GitHub management data
        self._init_github_data()
        
        # Application state
        self.app: Optional[gr.Blocks] = None
        self.executor = ThreadPoolExecutor(max_workers=3)
        
        # CSS for the interface
        self.css = """
        /* Custom CSS for browser-filling layout */
        .gradio-container {
            max-width: 100% !important;
            padding: 0 !important;
            margin: 0 !important;
            height: 100vh;
            overflow: hidden;
        }
        
        .gr-column {
            height: 100%;
        }
        
        .gr-tabitem {
            height: 100%;
        }
        
        .gr-chatbot {
            height: 100%;
            overflow-y: auto;
        }
        
        .gr-textbox {
            height: 100%;
        }
        
        /* Responsive design for different screen sizes */
        @media (max-width: 768px) {
            .gr-column {
                padding: 10px !important;
            }
        }
        
        /* Custom scrollbar styling */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #f1f1f1;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #555;
        }
        """
        
        # LLM configuration for slow models
        self.llm_config = {
            'timeout': 300,  # 5 minutes timeout
            'retry_attempts': 3,
            'streaming_chunk_size': 64,  # Smaller chunks for better UX
            'progress_update_interval': 1.0,  # Update progress every second
        }
    
    def _init_github_data(self):
        """Initialize GitHub management component with data."""
        try:
            # The new GitHub management component handles its own initialization
            # in the _init_data_sync method, so we don't need custom initialization here
            logger.info("GitHub management component will initialize itself")
            
        except Exception as e:
            logger.error(f"Error setting up GitHub initialization: {e}")
    
    def _initialize_rag_service(self):
        """Initialize RAG chat service with proper configuration."""
        try:
            # Get server configuration
            server_config = self.config.get('server', {})
            base_url = server_config.get('base_url', 'http://localhost:1234')
            
            # Get RAG configuration
            rag_config = self.config.get('rag', {})
            
            # Import RAG service
            from src.models.rag_chat_service import create_rag_chat_service
            
            return create_rag_chat_service(
                base_url=base_url,
                rag_enabled=rag_config.get('enabled', True),
                rag_n_results=rag_config.get('n_results', 3),
                rag_min_score=rag_config.get('min_score', 0.1),
                conversation_history_limit=rag_config.get('history_limit', 10),
            )
        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {e}")
            # Fallback to basic service
            from src.models.rag_chat_service import create_rag_chat_service
            return create_rag_chat_service(
                base_url="http://localhost:1234",
                rag_enabled=False,
                rag_n_results=3,
                rag_min_score=0.1,
                conversation_history_limit=10,
            )
    
    def create_interface(self) -> gr.Blocks:
        """Create the main Gradio interface with tabs."""
        with gr.Blocks() as self.app:
            # Application header
            gr.Markdown("""
            # 🤖 SigmaHQ RAG Application
            **Asynchronous Interface** - Non-blocking operations for slow local LLMs
            """)
            
            # Create tabs for each main functionality
            with gr.Tabs() as tabs:
                # Chat Tab
                with gr.TabItem("💬 Chat", id="chat"):
                    self.chat_interface.create_tab()
                
                # Data Management Tab
                with gr.TabItem("📊 Data", id="data"):
                    self.data_management.create_tab()
                
                # GitHub Management Tab
                with gr.TabItem("📁 GitHub", id="github"):
                    self.github_management.create_tab()
                
                # File Management Tab
                with gr.TabItem("📂 Files", id="files"):
                    self.file_management.create_tab()
                
                # Configuration Tab
                with gr.TabItem("⚙️ Config", id="config"):
                    self.config_management.create_tab()
                
                # Logs Tab
                with gr.TabItem("📋 Logs", id="logs"):
                    self.logs_viewer.create_tab()
        
        return self.app
    
    def launch(self, port: int = 8001):
        """Launch the Gradio application."""
        logger.info(f"Starting SigmaHQ RAG Gradio application on port {port}")
        
        # Create the interface
        self.create_interface()
        
        # Launch the application
        self.app.launch(
            server_port=port,
            server_name="0.0.0.0",  # Allow external access
            share=False,  # Don't create public share link
            debug=False,  # Disable debug mode for production
            show_error=True,  # Show errors in the interface
            favicon_path=None,  # Use default favicon
            auth=None,  # No authentication required
            ssl_verify=False,  # Disable SSL verification for local development
            theme=gr.themes.Soft(),  # Moved from Blocks constructor
            css=self.css  # Use the CSS from create_interface
        )
    
    def cleanup(self):
        """Clean up resources."""
        try:
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=True)
            if self.rag_chat_service:
                self.rag_chat_service.cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


def safe_llm_call(func, *args, **kwargs):
    """
    Safe wrapper for LLM calls with timeout and retry logic.
    
    Args:
        func: The async function to call
        *args: Arguments for the function
        **kwargs: Keyword arguments for the function
    
    Returns:
        The result of the function call or an error message
    """
    async def wrapper():
        try:
            # Add timeout protection
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=300  # 5 minutes timeout
            )
            return result
        except asyncio.TimeoutError:
            return "Error: LLM response timed out. Please try again."
        except Exception as e:
            return f"Error: {str(e)}"
    
    return wrapper()


if __name__ == "__main__":
    app = SigmaHQGradioApp()
    try:
        app.launch(port=8001)
    except KeyboardInterrupt:
        logger.info("Application shutdown requested")
    finally:
        app.cleanup()
