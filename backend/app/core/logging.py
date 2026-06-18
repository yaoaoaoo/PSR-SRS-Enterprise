"""Structured logging setup using Python standard library logging.

Configures a console handler with a consistent format and level driven
by ``settings.LOG_LEVEL``.
"""

from __future__ import annotations

import logging
import sys

from app.core.config import settings

LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def setup_logging() -> None:
    """Configure root logger with console output at the configured level."""
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    root = logging.getLogger()
    root.setLevel(level)
    # Remove any pre-existing handlers to avoid duplicate output
    root.handlers.clear()
    root.addHandler(handler)

    # Quiet down noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info("Logging configured | level=%s", settings.LOG_LEVEL.upper())
