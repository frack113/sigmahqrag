"""
Logging service for SigmaHQ RAG application.

Provides centralized logging functionality across the application.
"""

import logging


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with standard configuration.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Configure handlers only if not already configured
    if not logger.handlers:
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        # Create file handler for debug logs
        file_handler = logging.FileHandler('logs/app.log')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        # Add handlers to logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        # Set default level
        if logger.level == logging.NOTSET:
            logger.setLevel(logging.INFO)

    return logger