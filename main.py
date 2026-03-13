# Main Entry Point - Gradio Version with Auto-Reload
import sys
import signal
import logging
import argparse
from typing import Optional
from pathlib import Path

# Configure logging for development
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from src.application.app import SigmaHQGradioApp
from src.infrastructure.production_setup import ProductionSetup, ProductionConfig
from src.shared.utils import get_app_directory


def signal_handler(signum, frame):
    """Handle graceful shutdown on SIGINT/SIGTERM."""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)


def main():
    """Main entry point with auto-reload support."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="SigmaHQ RAG Application")
    parser.add_argument(
        "--production", action="store_true", help="Run in production mode"
    )
    parser.add_argument(
        "--host", type=str, default=None, help="Host to bind to (overrides config)"
    )
    parser.add_argument(
        "--port", type=int, default=None, help="Port to bind to (overrides config)"
    )
    parser.add_argument(
        "--setup-only",
        action="store_true",
        help="Only setup production environment, do not start app",
    )
    parser.add_argument(
        "--dev", action="store_true", help="Run in development mode with auto-reload"
    )
    parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload in development mode"
    )

    args = parser.parse_args()

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Determine mode
    is_dev_mode = (
        args.dev
        or args.reload
        or "--dev" in sys.argv
        or "--reload" in sys.argv
        or "dev" in sys.argv
    )
    is_production_mode = args.production

    if is_production_mode:
        logger.info("Setting up production environment...")

        # Load production configuration
        app_dir = get_app_directory()
        prod_config = ProductionConfig()

        if (app_dir / "data" / "config" / "production.json").exists():
            import json

            with open(app_dir / "data" / "config" / "production.json", "r") as f:
                config_data = json.load(f)
            prod_config = ProductionConfig(**config_data)

        # Override with command line arguments
        if args.host:
            prod_config.host = args.host
        if args.port:
            prod_config.port = args.port

        # Create production setup
        production_setup = ProductionSetup(prod_config)

        # Setup production environment
        if not production_setup.setup_production_environment():
            logger.error("Failed to setup production environment")
            sys.exit(1)

        if args.setup_only:
            logger.info("Production environment setup completed successfully")
            return

        logger.info(
            f"Starting application in production mode on {prod_config.host}:{prod_config.port}"
        )
        app = SigmaHQGradioApp()
        app.launch(host=prod_config.host, port=prod_config.port, production_mode=True)

    elif is_dev_mode:
        logger.info("Starting application in development mode with auto-reload")
        app = SigmaHQGradioApp()
        app.launch(port=args.port or 8000, dev_mode=True, reload=True, debug=True)
    else:
        logger.info("Starting application in default mode")
        app = SigmaHQGradioApp()
        app.launch(port=args.port or 8000)

    try:
        # Keep the application running
        pass
    except KeyboardInterrupt:
        logger.info("Application shutdown requested")
    except Exception as e:
        logger.error(f"Application error: {e}")
        if is_dev_mode:
            logger.error(
                "In development mode, this might be due to a code change. The app should auto-reload."
            )
        raise
    finally:
        app.cleanup()


if __name__ in {"__main__", "__mp_main__"}:
    main()
