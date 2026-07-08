"""
/preprocess endpoint.

PHASE 2 SCOPE ONLY:
    Deskew, denoise, resize, enhance contrast, and adaptive-threshold an
    uploaded drawing, then return the processed image. No OCR, no AI,
    no symbol detection - those are Phases 3, 9, and 4 respectively.

Reuses UploadValidationService from Phase 1 so file-type/size rules
stay defined in exactly one place.
"""
import logging

from fastapi import APIRouter, Depends, UploadFile, File

from app.schemas.preprocess import PreprocessResponse
from app.services.preprocessing.pipeline import PreprocessingPipeline, encode_png_base64
from app.services.upload_validation_service import UploadValidationService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["preprocess"])


def get_upload_validation_service() -> UploadValidationService:
    return UploadValidationService()


def get_preprocessing_pipeline() -> PreprocessingPipeline:
    return PreprocessingPipeline()


@router.post("/preprocess", response_model=PreprocessResponse)
async def preprocess(
    file: UploadFile = File(...),
    validation_service: UploadValidationService = Depends(get_upload_validation_service),
    pipeline: PreprocessingPipeline = Depends(get_preprocessing_pipeline),
) -> PreprocessResponse:
    contents = await validation_service.validate(file)

    result = pipeline.run(contents, file.content_type or "")

    logger.info(
        "Preprocessed '%s': %dx%d -> %dx%d in %.1fms",
        file.filename, result.original_width, result.original_height,
        result.processed_width, result.processed_height, result.processing_time_ms,
    )

    return PreprocessResponse(
        status="processed",
        filename=file.filename or "unknown",
        original_width=result.original_width,
        original_height=result.original_height,
        processed_width=result.processed_width,
        processed_height=result.processed_height,
        skew_angle_corrected_degrees=result.skew_angle_corrected_degrees,
        resize_scale_factor=result.resize_scale_factor,
        steps_applied=result.steps_applied,
        processing_time_ms=result.processing_time_ms,
        processed_image_base64=encode_png_base64(result.processed_image),
        preview_image_base64=encode_png_base64(result.preview_image),
    )
