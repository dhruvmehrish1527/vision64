"""Structured logging setup.

Keeps a single, JSON-ish line format that is greppable in production logs
(Railway/Render capture stdout) and readable in development. Engine and coach
calls log their latency so slow paths are visible.
"""

from __future__ import annotations

import logging
import sys
import time
from contextlib import contextmanager
from typing import Iterator

from app.core.config import get_settings


def configure_logging() -> None:
    """Install a root handler once, formatted for the current environment."""
    settings = get_settings()
    level = logging.INFO if settings.is_production else logging.DEBUG

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-7s %(name)s :: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Quiet down noisy third parties. `chess.engine` logs every UCI info line at
    # DEBUG — thousands of lines per game review — so cap it at WARNING.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("chess.engine").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


@contextmanager
def timed(logger: logging.Logger, label: str) -> Iterator[None]:
    """Log how long a block took — used around engine and coach calls."""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info("%s completed in %.0f ms", label, elapsed_ms)
