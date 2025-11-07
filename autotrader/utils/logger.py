"""Utility helpers for consistent logging configuration."""

from __future__ import annotations

import logging
from typing import Optional


def setup_logging(level: int = logging.INFO) -> None:
    """Configure application-wide logging.

    If logging has already been configured elsewhere the function returns
    immediately without altering the existing configuration. This prevents test
    suites or embedding applications from losing their logging setup.
    """

    if logging.getLogger().handlers:
        return

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a module specific logger instance."""

    return logging.getLogger(name if name else __name__)
