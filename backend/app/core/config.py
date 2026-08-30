"""Application configuration management.

Uses pydantic-settings for type-safe, environment-aware configuration.
All secrets are loaded from environment variables — never hard-coded.

Environment variables are prefixed with `LPA_` to avoid collisions.
Example: LPA_ENVIRONMENT=production, LPA_API_PORT=8000
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All fields map to environment variables with the `LPA_` prefix.
    Secrets must never appear in source code.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="LPA_",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────
    environment: str = Field(
        default="development",
        description="Runtime environment: development, testing, production",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    # ── API ──────────────────────────────────────────────────────
    api_host: str = Field(
        default="0.0.0.0",
        description="API server bind host",
    )
    api_port: int = Field(
        default=8000,
        description="API server bind port",
    )
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins",
    )

    # ── Database ─────────────────────────────────────────────────
    database_url: str = Field(
        default="sqlite:///data/lahore_pulse.db",
        description="SQLite database file path",
    )

    # ── External Providers ───────────────────────────────────────
    openaq_api_key: str | None = Field(
        default=None,
        description="OpenAQ API key (required for AQ measurements)",
    )
    open_meteo_api_key: str | None = Field(
        default=None,
        description="Open-Meteo API key (optional; free tier works without)",
    )
    aqicn_api_token: str | None = Field(
        default=None,
        description="AQICN/WAQI API token (required for real-time AQI)",
    )

    # ── AI Investigation Reasoning ──────────────────────────────
    ai_provider: str = Field(
        default="openai",
        description="AI provider for investigation reasoning (openai, openai-compatible)",
    )
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI or compatible API key (LPA_OPENAI_API_KEY)",
    )
    ai_model: str = Field(
        default="gpt-4o-mini",
        description="AI model for investigation reasoning",
    )
    ai_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="AI API base URL (override for OpenAI-compatible providers)",
    )

    # ── Ingestion Settings ──────────────────────────────────────
    open_meteo_base_url: str = Field(
        default="https://archive-api.open-meteo.com",
        description="Open-Meteo archive API base URL",
    )
    open_meteo_forecast_url: str = Field(
        default="https://api.open-meteo.com",
        description="Open-Meteo forecast API base URL",
    )
    open_meteo_aq_url: str = Field(
        default="https://air-quality-api.open-meteo.com",
        description="Open-Meteo air quality API base URL",
    )
    openaq_base_url: str = Field(
        default="https://api.openaq.org",
        description="OpenAQ API base URL",
    )
    aqicn_base_url: str = Field(
        default="https://api.waqi.info",
        description="AQICN/WAQI API base URL",
    )

    # ── Lahore Geographic Defaults ──────────────────────────────
    lahore_latitude: float = Field(
        default=31.5204,
        description="Lahore center latitude",
    )
    lahore_longitude: float = Field(
        default=74.3587,
        description="Lahore center longitude",
    )
    lahore_station_radius_km: float = Field(
        default=25.0,
        description="Radius in km for station discovery around Lahore center",
    )

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_testing(self) -> bool:
        return self.environment == "testing"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings.

    Settings are loaded once from environment variables and cached.
    In testing, call get_settings.cache_clear() before each test
    that needs different configuration.
    """
    return Settings()
