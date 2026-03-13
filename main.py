# Main Entry Point - Gradio Application
import sys
import signal
import logging
import argparse
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from src.application.app import SigmaHQGradioApp


def signal_handler(signum, frame):
    """Handle graceful shutdown on SIGINT/SIGTERM."""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)


def main():
    """Main entry point for Gradio application."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="SigmaHQ RAG Application")
    parser.add_argument(
        "--host", type=str, default=None, help="Host to bind to (overrides config)"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to bind to"
    )
    parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload in development mode"
    )

    args = parser.parse_args()

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Set environment variables for Gradio configuration
    server_host = "0.0.0.0" if not args.host else args.host
    os.environ["GRADIO_SERVER_NAME"] = server_host
    os.environ["GRADIO_SERVER_PORT"] = str(args.port)
    
    if args.reload:
        os.environ["GRADIO_ALLOW_ORIGIN"] = "*http://*/*"

    logger.info(
        f"Starting application on {server_host}:{args.port}" +
        (" (auto-reload enabled)" if args.reload else "")
    )

    app = SigmaHQGradioApp()
    
    try:
        app.launch(reload=args.reload)
    except KeyboardInterrupt:
        logger.info("Application shutdown requested")
    finally:
        app.cleanup()


if __name__ in {"__main__", "__mp_main__"}:
    main()