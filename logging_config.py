"""Centralized logging configuration for the Knowledge Manager application."""

import logging
import logging.handlers
import sys
from pathlib import Path

from config import LOG_LEVEL, LOG_FILE


def setup_logging(name: str = None) -> logging.Logger:
    """
    Configure and return a logger instance with structured formatting.

    Args:
        name: Logger name (typically __name__ from the calling module)

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name or __name__)

    # Avoid duplicate handlers if logger already configured
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    simple_formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler (always enabled)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if LOG_LEVEL.upper() == "DEBUG" else logging.INFO)
    console_handler.setFormatter(simple_formatter if LOG_LEVEL.upper() != "DEBUG" else detailed_formatter)
    logger.addHandler(console_handler)

    # File handler (optional, configured via LOG_FILE environment variable)
    if LOG_FILE:
        log_path = Path(LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            filename=LOG_FILE,
            maxBytes=10_000_000,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to root logger to avoid duplicate logs
    logger.propagate = False

    return logger


# Create a default logger for the application
default_logger = setup_logging("knowledge_manager")


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance
    """
    return setup_logging(name)
