"""
backend/utils/logger.py - Logging Utility for CampusAI

Provides a standardized logger for all modules in the CampusAI ecosystem.
"""

import sys
import logging
from typing import Optional

# Set up root logger format
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Configure root logger once
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Get or create a named logger with consistent formatting.

    Args:
        name: Name of the logger module (e.g. 'campusai.chat').
        level: Optional logging level override (e.g. logging.DEBUG).

    Returns:
        logging.Logger instance.
    """
    logger = logging.getLogger(name)
    if level is not None:
        logger.setLevel(level)
    return logger
