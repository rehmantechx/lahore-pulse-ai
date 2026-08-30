"""Centralized API error handlers.

Maps application errors to consistent HTTP responses.
Every error response follows the same structure:

{
    "error": {
        "code": "MACHINE_READABLE_CODE",
        "message": "Human-readable description",
        "details": { ... }
    }
}

This ensures clients can programmatically handle errors
while humans can understand them.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..core.errors import ApplicationError, ErrorCode


def register_error_handlers(app: FastAPI) -> None:
    """Register all error handlers on the FastAPI application."""

    @app.exception_handler(ApplicationError)
    async def application_error_handler(
        request: Request,
        exc: ApplicationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=_error_code_to_http_status(exc.code),
            content={
                "error": {
                    "code": exc.code.value,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        # Never expose internal details in error responses
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "An unexpected error occurred",
                }
            },
        )


def _error_code_to_http_status(code: ErrorCode) -> int:
    """Map application error codes to HTTP status codes."""
    mapping = {
        ErrorCode.CLIENT_INVALID_REQUEST: 400,
        ErrorCode.CONFIGURATION_ERROR: 500,
        ErrorCode.DATA_SOURCE_UNAVAILABLE: 503,
        ErrorCode.INVALID_EXTERNAL_DATA: 502,
        ErrorCode.INTERNAL_ERROR: 500,
        ErrorCode.PREDICTION_UNAVAILABLE: 503,
        ErrorCode.INSUFFICIENT_DATA: 422,
    }
    return mapping.get(code, 500)
