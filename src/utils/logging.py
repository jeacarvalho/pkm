"""Logging configuration for Obsidian RAG."""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional


def get_logger(
    name: str, log_file: Optional[Path] = None, level: str = "INFO"
) -> logging.Logger:
    """Get a configured logger instance.

    Args:
        name: Logger name (typically __name__).
        log_file: Path to log file. If None, logs to stdout only.
        level: Logging level (DEBUG, INFO, WARNING, ERROR).

    Returns:
        Configured logger instance.

    Example:
        >>> logger = get_logger(__name__, Path("./logs/app.log"))
        >>> logger.info("Application started")
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    logger.handlers = []

    # Formatters
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (with rotation)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_skipped_logger(log_file: Path) -> logging.Logger:
    """Get a logger specifically for skipped/failed notes.

    Args:
        log_file: Path to the skipped notes log file.

    Returns:
        Logger instance for skipped notes.
    """
    logger = logging.getLogger("skipped_notes")
    logger.setLevel(logging.INFO)

    # Clear existing handlers
    logger.handlers = []

    # Create file handler
    log_file.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    logger.addHandler(handler)

    return logger
