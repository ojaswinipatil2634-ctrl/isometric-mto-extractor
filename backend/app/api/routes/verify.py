"""
/verify endpoint.

PHASE 9 SCOPE ONLY:
    Send the drawing image, plus everything already extracted by Phases
    3/4/6/7 (OCR fields, detection counts, graph summary, business rules
    summary), to Gemini for REVIEW ONLY. Per the project-wide rule,
    Gemini may only:
      - suggest corrections to what was already extracted
      - point out things visible in the drawing that are missing from
        the extraction
      - flag OCR text that looks wrong
    Gemini must NEVER regenerate or replace the extraction - this
    endpoint never lets a Gemini response overwrite any field Phases
    1-8 already produced; it only surfaces Gemini's review alongside it.

If `GEMINI_API_KEY` isn't configured, or the request to Gemini fails for
any reason, this returns `available: false` with a warning explaining
why - status 200, never a crash, never a fabricated review.
"""
import logging

from fastapi import APIRouter, Depends, UploadFile, File

from app.schemas.verify import VerificationResponse
from app.services.gemini_verification.pipeline import GeminiVerificationPipeline
from app.services.upload_validation_service import UploadValidationService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["verification"])


def get_upload_validation_service() -> UploadValidationService:
    return UploadValidationService()


def get_gemini_verification_pipeline() -> GeminiVerificationPipeline:
    return GeminiVerificationPipeline()


@router.post("/verify", response_model=VerificationResponse)
async def verify_extraction(
    file: UploadFile = File(...),
    validation_service: UploadValidationService = Depends(get_upload_validation_service),
    pipeline: GeminiVerificationPipeline = Depends(get_gemini_verification_pipeline),
) -> VerificationResponse:
    contents = await validation_service.validate(file)

    result = pipeline.run(contents, file.content_type or "")

    logger.info(
        "Verification '%s': available=%s, %d correction(s), %d missing item(s), %d OCR flag(s)",
        file.filename, result.available, len(result.corrections), len(result.missing_items),
        len(result.ocr_flags),
    )

    return VerificationResponse(
        status="reviewed",
        filename=file.filename or "unknown",
        available=result.available,
        corrections=result.corrections,
        missing_items=result.missing_items,
        ocr_flags=result.ocr_flags,
        warnings=result.warnings,
        processing_time_ms=result.processing_time_ms,
    )
