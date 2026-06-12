"""
logger.py - Centralized logging setup.
Creates rotating file logs + console output.
"""

import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logger(name: str = "guess_bot", level: str = "INFO") -> logging.Logger:
    """
    Setup and return a configured logger.
    
    Args:
        name: Logger name (shown in log lines)
        level: Log level string (DEBUG/INFO/WARNING/ERROR)
    
    Returns:
        Configured Logger instance
    """
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Prevent duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    # ── Formatter ────────────────────────────────────────────
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # ── Console Handler ───────────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    # ── File Handler (rotating, max 5MB, keep 3 files) ───────
    file_handler = RotatingFileHandler(
        "logs/bot.log",
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger


# Create the default bot logger
logger = setup_logger()
