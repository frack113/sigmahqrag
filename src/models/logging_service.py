# This file has been deprecated.
# Logging is now handled by Python's built-in logging module.
# No separate service needed for standard logging functionality.
import logging


class LoggingService:
    """
    Deprecated: Use Python's built-in logging module directly.

    Standard Python logging provides all necessary functionality:
    - Logger setup with log levels
    - Formatters and handlers
    - Console/file output
    - Log rotation

    Example usage:
        import logging

        logger = logging.getLogger(__name__)
        logger.info("Message")
    """


# Convenience function for quick logging (optional)
def get_logger(name: str, level: int | None = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (usually __name__)
        level: Log level (None uses default)

    Returns:
        Logger instance
    """
    import logging

    logger = logging.getLogger(name)

    if level is not None:
        logger.setLevel(level)

    return logger
