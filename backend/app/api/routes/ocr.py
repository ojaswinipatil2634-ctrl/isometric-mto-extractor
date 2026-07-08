"""
/ocr endpoint.

PHASE 3 SCOPE ONLY:
    Run PaddleOCR against an uploaded drawing (after Phase 2's
    preprocessing) and extract structured title-block fields (drawing
    number, revision, line number, service, material class, NPS,
    dimensions) via regex rules. No symbol detection (Phase 4), no
    AI verification (Phase 9) - Gemini is never used here or anywhere
    in the extraction path.

If PaddleOCR/paddlepaddle are not installed, or the engine otherwise
fails to initialize or process the image, this returns a structured
503 OCR_UNAVAILABLE error (via the app-wide AppError handler) instead
of crashing or fabricating a result.
"""
import logging

from fastapi import APIRouter, Depends, UploadFile, File

from app.schemas.ocr import (
    ExtractedFields as ExtractedFieldsSchema,
    FieldValue as FieldValueSchema,
    OcrResponse,
    TextBlock as TextBlockSchema,
)
from app.services.ocr import field_extractor
from app.services.ocr.pipeline import OcrPipeline
from app.services.upload_validation_service import UploadValidationService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ocr"])


def get_upload_validation_service() -> UploadValidationService:
    return UploadValidationService()


def get_ocr_pipeline() -> OcrPipeline:
    return OcrPipeline()


def _field_to_schema(fv: field_extractor.FieldValue) -> FieldValueSchema:
    return FieldValueSchema(value=fv.value, confidence=fv.confidence, source_text=fv.source_text, bbox=fv.bbox)


@router.post("/ocr", response_model=OcrResponse)
async def run_ocr(
    file: UploadFile = File(...),
    validation_service: UploadValidationService = Depends(get_upload_validation_service),
    pipeline: OcrPipeline = Depends(get_ocr_pipeline),
) -> OcrResponse:
    contents = await validation_service.validate(file)

    result = pipeline.run(contents, file.content_type or "")

    logger.info(
        "OCR '%s': %d text block(s), avg confidence=%s",
        file.filename, len(result.text_blocks), result.average_confidence,
    )

    extracted = result.extracted_fields
    extracted_schema = ExtractedFieldsSchema(
        drawing_number=_field_to_schema(extracted.drawing_number),
        revision=_field_to_schema(extracted.revision),
        line_number=_field_to_schema(extracted.line_number),
        service=_field_to_schema(extracted.service),
        material_class=_field_to_schema(extracted.material_class),
        nps=[_field_to_schema(f) for f in extracted.nps],
        dimensions=[_field_to_schema(f) for f in extracted.dimensions],
    )

    return OcrResponse(
        status="extracted",
        filename=file.filename or "unknown",
        engine_available=result.engine_available,
        text_blocks=[TextBlockSchema(text=b.text, confidence=b.confidence, bbox=b.bbox) for b in result.text_blocks],
        text_block_count=len(result.text_blocks),
        extracted_fields=extracted_schema,
        average_confidence=result.average_confidence,
        warnings=result.warnings,
        processing_time_ms=result.processing_time_ms,
    )
