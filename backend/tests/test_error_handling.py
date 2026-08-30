"""Tests for error handling.

Verifies that:
- Application errors carry correct codes and messages
- API error responses follow consistent structure
- Unhandled errors are safely caught
"""

from __future__ import annotations

from app.core.errors import (
    ApplicationError,
    ConfigurationError,
    DataSourceUnavailableError,
    ErrorCode,
    InsufficientDataError,
)


class TestApplicationError:
    def test_basic_error(self) -> None:
        err = ApplicationError(ErrorCode.INTERNAL_ERROR, "Something broke")
        assert err.code == ErrorCode.INTERNAL_ERROR
        assert err.message == "Something broke"
        assert err.details == {}

    def test_error_with_details(self) -> None:
        err = ApplicationError(
            ErrorCode.DATA_SOURCE_UNAVAILABLE,
            "Source is down",
            details={"provider": "openaq", "retry_after": 60},
        )
        assert err.details["provider"] == "openaq"
        assert err.details["retry_after"] == 60

    def test_error_is_exception(self) -> None:
        err = ApplicationError(ErrorCode.INTERNAL_ERROR, "test")
        assert isinstance(err, Exception)
        assert str(err) == "test"


class TestDataSourceUnavailableError:
    def test_provider_in_message(self) -> None:
        err = DataSourceUnavailableError("openaq", "Connection timeout")
        assert "openaq" in err.message
        assert err.code == ErrorCode.DATA_SOURCE_UNAVAILABLE
        assert err.details["provider"] == "openaq"

    def test_default_message(self) -> None:
        err = DataSourceUnavailableError("open-meteo")
        assert "unavailable" in err.message.lower()


class TestInsufficientDataError:
    def test_default_message(self) -> None:
        err = InsufficientDataError()
        assert err.code == ErrorCode.INSUFFICIENT_DATA

    def test_custom_message(self) -> None:
        err = InsufficientDataError("Only 2 days of data available")
        assert "2 days" in err.message


class TestConfigurationError:
    def test_configuration_error(self) -> None:
        err = ConfigurationError("Missing database URL")
        assert err.code == ErrorCode.CONFIGURATION_ERROR


class TestAPIErrorResponses:
    """Tests for actual API error response format."""

    def test_404_returns_json_error(self, client) -> None:
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_method_not_allowed(self, client) -> None:
        response = client.post("/api/v1/health")
        assert response.status_code == 405
