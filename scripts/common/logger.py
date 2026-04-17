"""
logger.py — Shared logging setup for all generated scripts.

Usage
-----
    from scripts.common.logger import get_logger

    log = get_logger(__name__)
    log.info("Hello, world!")
"""

from __future__ import annotations

import logging
import os
import sys

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_root_configured = False


def get_logger(name: str, level: int | None = None) -> logging.Logger:
    """Return a logger named *name*, configuring the root logger once.

    The log level is resolved from (in priority order):
    1. The *level* argument.
    2. The ``LOG_LEVEL`` environment variable.
    3. ``logging.INFO`` as the default.
    """
    global _root_configured
    if not _root_configured:
        _configure_root_logger()
        _root_configured = True

    logger = logging.getLogger(name)
    if level is not None:
        logger.setLevel(level)
    return logger


def _configure_root_logger() -> None:
    env_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    numeric = getattr(logging, env_level, logging.INFO)

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))

    root = logging.getLogger()
    root.setLevel(numeric)
    if not root.handlers:
        root.addHandler(handler)
