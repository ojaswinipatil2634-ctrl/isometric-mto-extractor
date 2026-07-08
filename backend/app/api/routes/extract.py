"""
/extract endpoint.

PHASE 1 SCOPE ONLY:
    Validate the uploaded drawing and acknowledge receipt.
    No OCR, no OpenCV, no YOLO, no Gemini - those are added in
    Phases 2 through 9 respectively, each behind its own service.

The route itself stays thin: it delegates validation to
UploadValidationService and contains no business logic, per the
project's separation-of-concerns rule.
"""
import logging

from fastapi import APIRouter, Depends, UploadFile, File

from app.schemas.extract import ExtractResponse
from app.services.upload_validation_service import UploadValidationService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["extract"])


def get_upload_validation_service() -> UploadValidationService:
    return UploadValidationService()


@router.post("/extract", response_model=ExtractResponse)
async def extract(
    file: UploadFile = File(...),
    validation_service: UploadValidationService = Depends(get_upload_validation_service),
) -> ExtractResponse:
    contents = await validation_service.validate(file)

    logger.info(
        "Accepted upload '%s' (%s, %d bytes)",
        file.filename,
        file.content_type,
        len(contents),
    )

    return ExtractResponse(
        status="received",
        filename=file.filename or "unknown",
        content_type=file.content_type or "unknown",
        size_bytes=len(contents),
    )
