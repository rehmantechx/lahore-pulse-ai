"""Application services.

Use-case level services that orchestrate domain logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from loguru import logger


@dataclass
class ServiceContext:
    """Common context for all service operations."""

    request_id: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict = field(default_factory=dict)

    def log(self, message: str, **kwargs: object) -> None:
        """Log with context."""
        logger.bind(
            request_id=self.request_id,
            **kwargs,
        ).info(message)
