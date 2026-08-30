"""Abstract forecast provider contract.

Forecast providers supply predicted/forecasted environmental values
from external services (e.g., Open-Meteo weather forecasts).

They are separate from observation providers because:
- Different data characteristics (predicted vs observed)
- Different uncertainty profiles
- Different update frequencies
- Different provenance requirements

Phase 0 establishes this contract. Concrete implementations
belong to Phase 1+.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .data_provider import ProviderHealth


class ForecastProvider(ABC):
    """Abstract interface for external forecast providers.

    Forecast providers differ from data providers in that they
    supply future-looking predictions from external services,
    not historical observations.
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier for this forecast provider."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name."""
        ...

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Check if the forecast provider is reachable."""
        ...
