"""Abstract data provider contract.

Every external data source (OpenAQ, Open-Meteo, etc.) must implement
this interface. This ensures:

1. Source isolation: Business logic depends on this interface, not on
   HTTP clients or specific API formats.
2. Replaceability: Data sources can be swapped without changing consumers.
3. Testability: Providers can be mocked via this interface in tests.
4. Consistency: All providers expose the same health check interface.

Phase 0 establishes this contract. Concrete implementations
belong to Phase 1+.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ProviderHealth(BaseModel):
    """Health status of an external data provider.

    Returned by provider health checks to indicate availability
    and operational status.
    """

    available: bool = Field(
        ...,
        description="Whether the provider is currently reachable",
    )
    message: str = Field(
        default="",
        description="Human-readable health status message",
    )
    checked_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this health check was performed",
    )
    response_time_ms: float | None = Field(
        default=None,
        description="Provider response time in milliseconds",
    )


class DataProvider(ABC):
    """Abstract interface for external data providers.

    All environmental data sources must implement this interface.
    The interface is deliberately minimal for Phase 0 and will
    expand as provider capabilities are defined in later phases.

    Usage:
        class OpenAQProvider(DataProvider):
            @property
            def provider_id(self) -> str:
                return "openaq"

            async def health_check(self) -> ProviderHealth:
                # Implementation checks OpenAQ API availability
                ...
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier for this provider (e.g., 'openaq', 'open-meteo')."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name."""
        ...

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Check if the provider is currently reachable and operational.

        Returns:
            ProviderHealth indicating current availability status.
        """
        ...
