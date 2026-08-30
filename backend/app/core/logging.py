"""Structured application logging.

Uses loguru for consistent, structured logging across all layers.
Logs must never contain API keys, passwords, tokens, or credentials.
"""

from __future__ import annotations

import sys

import loguru

# Module-level logger for convenience imports
logger = loguru.logger


def setup_logging(log_level: str = "INFO") -> None:
    """Configure application logging.

    Removes the default loguru handler and adds a structured
    stderr handler with consistent formatting.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    logger.remove()

    logger.add(
        sys.stderr,
        level=log_level.upper(),
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}"
        ),
        colorize=True,
        backtrace=True,
        diagnose=False,  # Never expose internals in production
    )

    logger.info(
        "Logging initialized",
        level=log_level.upper(),
    )
