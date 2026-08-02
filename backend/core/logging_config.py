"""
core/logging_config.py — Structured Logging Setup
===================================================
Call setup_logging() in main.py (or let uvicorn handle it).
"""

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger with a clean, coloured console handler."""
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s — %(message)s"
    datefmt = "%H:%M:%S"

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        datefmt=datefmt,
        stream=sys.stdout,
    )

    # Suppress noisy third-party loggers
    for noisy in ("ultralytics", "mediapipe", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
