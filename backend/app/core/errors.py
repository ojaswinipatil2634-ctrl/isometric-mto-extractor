"""
Application-wide error types and FastAPI exception handlers.

Every error returned by the API follows the same JSON shape:

    {
        "error": {
            "code": "SOME_ERROR_CODE",
            "message": "Human readable message",
            "details": { ... optional ... }
        }
    }

This keeps the frontend's error handling logic in one place instead of
branching on HTTP status codes scattered across the codebase.
"""
import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for all expected, handled application errors."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "APP_ERROR"

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class InvalidFileError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "INVALID_FILE"


class FileTooLargeError(AppError):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    code = "FILE_TOO_LARGE"


class OcrUnavailableError(AppError):
    """Raised when PaddleOCR is not installed, fails to initialize, or
    fails while processing an image. Per project rules, OCR failures
    must surface as a clean structured error - never a fabricated
    result and never an unhandled 500."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "OCR_UNAVAILABLE"


class DetectionUnavailableError(AppError):
    """Raised when the YOLOv11 symbol detector can't run: ultralytics is
    not installed, the weights file is missing/unreadable, the model
    fails to load, or inference fails on a given image. Per project
    rules, detection failures must surface as a clean structured error -
    never a fabricated result and never an unhandled 500."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "DETECTION_UNAVAILABLE"


class RunNotFoundError(AppError):
    """Raised when a Phase 8 `/mto/{id}` history/detail/export request
    references a run id that doesn't exist in the database."""

    status_code = status.HTTP_404_NOT_FOUND
    code = "RUN_NOT_FOUND"


def _error_body(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning("Handled app error: %s - %s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception while processing request")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                "INTERNAL_SERVER_ERROR",
                "An unexpected error occurred. Please try again.",
            ),
        )
