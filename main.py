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
import os

# Disable Hugging Face telemetry to prevent external web requests
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

from pathlib import Path
from src.shared.config_manager import MissingConfigError
from src.application.application import create_application, SigmaHQApplication


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


def validate_config_path(config_path: Path | None = None) -> Path:
    """Validate that config.json exists before starting application.

    Args:
        config_path: Optional path to config file (defaults to data/config.json)

    Returns:
        Path to the configuration file

    Raises:
        MissingConfigError: If config.json does not exist
    """
    if config_path is None:
        config_path = Path("data/config.json")

    if not config_path.exists():
        raise MissingConfigError(
            f"Required configuration file not found: {config_path}"
        )

    return config_path


def main():
    """Main entry point for Gradio application.

    Configuration Requirements:
    - data/config.json MUST exist at startup
    - All values come from config.json (no DEFAULT_* fallbacks)
    """
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Starting SigmaHQ RAG")

    # Validate configuration file exists before starting application
    # This is a required step - application will not start without config.json
    config_path = validate_config_path()
    logger.info(f"Using configuration from: {config_path}")

    # Create application (uses Gradio's native async support via queue=True)
    app = SigmaHQApplication(config_path=str(config_path))

    try:
        app.launch()
    except KeyboardInterrupt:
        logger.info("Application shutdown requested")


if __name__ == "__main__":
    main()
