"""Application error model.

Provides a consistent error taxonomy for all layers.
Every error carries a machine-readable code and a human-readable message.

Error categories:
- CLIENT_INVALID_REQUEST: Malformed or invalid client input
- CONFIGURATION_ERROR: Missing or invalid server configuration
- DATA_SOURCE_UNAVAILABLE: External data provider is unreachable
- INVALID_EXTERNAL_DATA: External data failed validation
- INTERNAL_ERROR: Unexpected application failure
- PREDICTION_UNAVAILABLE: Prediction model not available or not configured
- INSUFFICIENT_DATA: Not enough data to produce a result
"""

from __future__ import annotations

from enum import StrEnum


class ErrorCode(StrEnum):
    """Machine-readable error codes.

    Used in API error responses for programmatic handling.
    Each code maps to a specific HTTP status code.
    """

    INTERNAL_ERROR = "INTERNAL_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    DATA_SOURCE_UNAVAILABLE = "DATA_SOURCE_UNAVAILABLE"
    INVALID_EXTERNAL_DATA = "INVALID_EXTERNAL_DATA"
    CLIENT_INVALID_REQUEST = "CLIENT_INVALID_REQUEST"
    PREDICTION_UNAVAILABLE = "PREDICTION_UNAVAILABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ApplicationError(Exception):
    """Base application error.

    All domain and infrastructure errors should inherit from this
    to ensure consistent error handling across the application.

    Attributes:
        code: Machine-readable error code.
        message: Human-readable error description.
        details: Optional additional context (must not contain secrets).
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: dict | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class DataSourceUnavailableError(ApplicationError):
    """Raised when an external data provider cannot be reached."""

    def __init__(
        self,
        provider: str,
        message: str = "Data provider is unavailable",
        details: dict | None = None,
    ) -> None:
        merged_details = {"provider": provider, **(details or {})}
        super().__init__(
            code=ErrorCode.DATA_SOURCE_UNAVAILABLE,
            message=f"[{provider}] {message}",
            details=merged_details,
        )


class InsufficientDataError(ApplicationError):
    """Raised when there is not enough data to perform an operation."""

    def __init__(
        self,
        message: str = "Insufficient data available",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            code=ErrorCode.INSUFFICIENT_DATA,
            message=message,
            details=details,
        )


class ConfigurationError(ApplicationError):
    """Raised for configuration problems."""

    def __init__(
        self,
        message: str = "Configuration error",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            code=ErrorCode.CONFIGURATION_ERROR,
            message=message,
            details=details,
        )


class InvalidExternalDataError(ApplicationError):
    """Raised when external data fails validation.

    This covers: malformed JSON, missing required fields,
    invalid timestamps, unrecognized units, out-of-range values.
    """

    def __init__(
        self,
        message: str = "External data failed validation",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            code=ErrorCode.INVALID_EXTERNAL_DATA,
            message=message,
            details=details,
        )
