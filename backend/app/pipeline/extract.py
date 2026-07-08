"""
End-to-end extraction pipeline orchestrator.

Steps (per spec):
1. Validate file
2. Convert PDF -> image
3. Resize / enhance image
4. Send image to Gemini Vision (or use mock)
5. Validate JSON with Pydantic (done inside gemini_service / mock_service)
6. Normalize units + derive gaskets/bolt sets + compute summary (business_logic)
7. Return validated MTOResult
"""
from __future__ import annotations

import logging

from app.config import Settings
from app.pipeline.business_logic import build_mto
from app.schemas.mto import MTOResult
from app.services import image_service
from app.services.gemini_service import GeminiExtractionError, extract_from_image
from app.services.mock_service import mock_extraction

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES_DEFAULT = 20 * 1024 * 1024


class ValidationError(Exception):
    pass


def validate_upload(filename: str, size_bytes: int, settings: Settings) -> None:
    if not any(filename.lower().endswith(ext) for ext in settings.allowed_extensions):
        raise ValidationError(
            f"Unsupported file type. Allowed: {', '.join(settings.allowed_extensions)}"
        )
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise ValidationError(f"File exceeds max size of {settings.max_upload_mb}MB")
    if size_bytes == 0:
        raise ValidationError("Uploaded file is empty")


def run_pipeline(raw_bytes: bytes, filename: str, settings: Settings) -> MTOResult:
    """Run the full pipeline and always return a valid MTOResult.

    Mock mode (no API key) and any live-call failure both fall through to
    the mock extraction — the app must never crash on the user.
    """
    validate_upload(filename, len(raw_bytes), settings)

    if settings.mock_mode:
        logger.info("No GEMINI_API_KEY configured — running in mock mode")
        extraction = mock_extraction(filename)
        return build_mto(extraction, mock_mode=True)

    # Live path
    try:
        image = image_service.bytes_to_image(raw_bytes, filename)
        image = image_service.preprocess(image)
        png_bytes = image_service.image_to_png_bytes(image)
        extraction = extract_from_image(png_bytes, settings)
        return build_mto(extraction, mock_mode=False)
    except GeminiExtractionError as exc:
        logger.warning("Gemini extraction failed (%s) — falling back to mock", exc)
        extraction = mock_extraction(filename)
        result = build_mto(extraction, mock_mode=True)
        result.warnings.insert(
            0, f"Live Gemini extraction failed ({exc}); showing mock data instead."
        )
        return result
    except image_service.UnsupportedFileError as exc:
        raise ValidationError(str(exc)) from exc
