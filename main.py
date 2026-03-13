# Main Entry Point - Gradio Application (Optimized with Native Gradio Features)
"""
SigmaHQ RAG - Optimized Gradio Application

This application uses Gradio's native features for async operations:
- queue=True: Enables built-in request queuing per user
- concurrency_limit=1: Serializes requests naturally
- Gradio handles async/await automatically when queue=True

To run: uv run python main.py [--reload]
"""

import sys
import signal
import logging

from src.application.application import create_application, create_default_application


# Configure logging to stderr only (not duplicate with Gradio's logs)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)

logger = logging.getLogger(__name__)


def signal_handler(signum, frame):
    """Handle graceful shutdown on SIGINT/SIGTERM."""
    logger.info("Received shutdown signal, cleaning up...")
    sys.exit(0)


def main():
    """Main entry point for Gradio application."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Starting SigmaHQ RAG")

    # Create application (uses native Gradio async support via queue=True)
    app = create_application()

    try:
        app.launch()
    except KeyboardInterrupt:
        logger.info("Application shutdown requested")


if __name__ == "__main__":
    main()
