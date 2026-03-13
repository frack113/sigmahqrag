# Main Entry Point - Gradio Version with Auto-Reload
import sys
import signal
import logging
from typing import Optional

# Configure logging for development
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from src.application.app import SigmaHQGradioApp

def signal_handler(signum, frame):
    """Handle graceful shutdown on SIGINT/SIGTERM."""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)

def main():
    """Main entry point with auto-reload support."""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Determine if running in development mode
    is_dev_mode = "--dev" in sys.argv or "--reload" in sys.argv or "dev" in sys.argv
    
    logger.info(f"Starting SigmaHQ RAG Application in {'development' if is_dev_mode else 'production'} mode")
    
    app = SigmaHQGradioApp()
    
    try:
        if is_dev_mode:
            # Development mode with auto-reload
            app.launch(
                port=8000,
                dev_mode=True,
                reload=True,
                debug=True
            )
        else:
            # Production mode
            app.launch(port=8000)
            
    except KeyboardInterrupt:
        logger.info("Application shutdown requested")
    except Exception as e:
        logger.error(f"Application error: {e}")
        if is_dev_mode:
            logger.error("In development mode, this might be due to a code change. The app should auto-reload.")
        raise
    finally:
        app.cleanup()

if __name__ in {"__main__", "__mp_main__"}:
    main()
