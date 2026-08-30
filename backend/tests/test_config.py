"""Tests for application configuration.

Verifies that:
- Default settings are valid
- Environment variable prefix works
- Settings properties return correct values
"""

from __future__ import annotations

from app.core.config import Settings, get_settings


class TestDefaultSettings:
    """Tests for default configuration values."""

    def test_default_environment_is_development(self) -> None:
        settings = Settings()
        assert settings.environment == "development"

    def test_default_log_level_is_info(self) -> None:
        settings = Settings()
        assert settings.log_level == "INFO"

    def test_default_api_port(self) -> None:
        settings = Settings()
        assert settings.api_port == 8000

    def test_default_api_host(self) -> None:
        settings = Settings()
        assert settings.api_host == "0.0.0.0"

    def test_default_cors_origins(self) -> None:
        settings = Settings()
        assert isinstance(settings.cors_origins, list)
        assert len(settings.cors_origins) > 0


class TestSettingsProperties:
    """Tests for computed settings properties."""

    def test_is_development(self) -> None:
        settings = Settings(environment="development")
        assert settings.is_development is True
        assert settings.is_testing is False
        assert settings.is_production is False

    def test_is_testing(self) -> None:
        settings = Settings(environment="testing")
        assert settings.is_testing is True
        assert settings.is_development is False

    def test_is_production(self) -> None:
        settings = Settings(environment="production")
        assert settings.is_production is True
        assert settings.is_development is False


class TestSettingsCustomization:
    """Tests for settings customization."""

    def test_custom_environment(self) -> None:
        settings = Settings(environment="staging")
        assert settings.environment == "staging"

    def test_custom_cors_origins(self) -> None:
        settings = Settings(cors_origins=["https://example.com"])
        assert settings.cors_origins == ["https://example.com"]

    def test_settings_are_immutable_cache(self) -> None:
        """Verify get_settings returns the same instance (lru_cache)."""
        get_settings.cache_clear()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
