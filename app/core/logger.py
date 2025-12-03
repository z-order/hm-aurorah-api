"""
Logger utility for consistent logging across modules
"""

import logging
import sys


class ColorFormatter(logging.Formatter):
    """Formatter with color support like uvicorn."""

    COLORS = {
        logging.DEBUG: "\033[36m",  # Cyan
        logging.INFO: "\033[32m",  # Green
        logging.WARNING: "\033[33m",  # Yellow
        logging.ERROR: "\033[31m",  # Red
        logging.CRITICAL: "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, "")
        # Pad levelname first, then apply color (so escape codes don't affect alignment)
        record.levelname = f"{color}{record.levelname + self.RESET + ':':<13}"
        return super().format(record)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Get a logger with uvicorn's handler for consistent formatting.

    Args:
        name: Logger name (typically __name__)
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Add a StreamHandler with uvicorn-like format if no handlers exist
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        handler.setFormatter(ColorFormatter("%(levelname)s [%(name)s:%(funcName)s] %(message)s"))
        logger.addHandler(handler)
        logger.propagate = False

    return logger
