"""
PramaanX — Logging Configuration
----------------------------------
Privacy note:
  Logs must NEVER contain raw passport numbers, full DOBs,
  biometric data, or uploaded document content.
  Mask sensitive fields before passing them to any logger.
"""

import logging
import sys

from app.core.config import settings


def _mask(value: str | None, keep: int = 3) -> str:
    """Return a masked version of a sensitive value for safe logging."""
    if not value:
        return "<empty>"
    if len(value) <= keep:
        return "*" * len(value)
    return value[:keep] + "*" * (len(value) - keep)


def setup_logging() -> None:
    """Configure the root logger for the application."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    fmt = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%S"

    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt=datefmt,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Suppress noisy third-party loggers
    for noisy in ("easyocr", "torch", "torchvision", "PIL", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
