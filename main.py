# Main Entry Point - Gradio Application
"""
SigmaHQ RAG - Gradio Application

Uses Gradio's native features for async operations.
Port conflicts are reported as errors (no automatic retry).

Run with: uv run python main.py
"""

import sys
import signal
import logging
import os

os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

from pathlib import Path

from src.shared.exceptions import MissingConfigError
from src.application.application import SigmaHQApplication


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
    """Validate that config.json exists before starting application."""
    if config_path is None:
        config_path = Path("data/config.json")

    if not config_path.exists():
        raise MissingConfigError(
            f"Required configuration file not found: {config_path}"
        )

    return config_path


def main() -> None:
    """Main entry point for Gradio application."""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Starting SigmaHQ RAG")

    config_path = validate_config_path()
    logger.info(f"Using configuration from: {config_path}")

    app = SigmaHQApplication(config_path=str(config_path))

    try:
        # Gradio will raise OSError if port is already in use
        # Error message will indicate the conflict
        app.launch()
    except OSError as e:
        logger.error(f"Failed to start application: {e}")
        logger.error("Please ensure port %s is not already in use or change the port in config.json", 
                    app.config["network"]["port"])
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Application shutdown requested")


if __name__ == "__main__":
    main()