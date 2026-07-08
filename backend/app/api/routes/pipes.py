"""
/pipes endpoint.

PHASE 5 SCOPE ONLY:
    Run the Phase 2 preprocessing pipeline, then skeletonize, then
    detect straight pipe runs via OpenCV's Hough transform, then merge
    collinear/adjacent raw segments into polylines. No graph
    construction (Phase 6), no business rules (Phase 7), no AI -
    OpenCV/scikit-image geometry only, per project rules.

Reuses UploadValidationService from Phase 1 so file-type/size rules
stay defined in exactly one place.
"""
import logging

from fastapi import APIRouter, Depends, UploadFile, File

from app.schemas.pipes import PipeExtractionResponse, PipePoint, PipeSegmentSchema
from app.services.pipe_extraction.pipeline import PipeExtractionPipeline
from app.services.upload_validation_service import UploadValidationService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["pipe-extraction"])


def get_upload_validation_service() -> UploadValidationService:
    return UploadValidationService()


def get_pipe_extraction_pipeline() -> PipeExtractionPipeline:
    return PipeExtractionPipeline()


@router.post("/pipes", response_model=PipeExtractionResponse)
async def extract_pipes(
    file: UploadFile = File(...),
    validation_service: UploadValidationService = Depends(get_upload_validation_service),
    pipeline: PipeExtractionPipeline = Depends(get_pipe_extraction_pipeline),
) -> PipeExtractionResponse:
    contents = await validation_service.validate(file)

    result = pipeline.run(contents, file.content_type or "")

    logger.info(
        "Pipe extraction '%s': %d raw segment(s) -> %d pipe run(s)",
        file.filename, result.raw_segment_count, len(result.segments),
    )

    segments_schema = [
        PipeSegmentSchema(
            start=PipePoint(x=seg.start[0], y=seg.start[1]),
            end=PipePoint(x=seg.end[0], y=seg.end[1]),
            length_px=seg.length_px,
            angle_degrees=seg.angle_degrees,
            orientation=seg.orientation,
            source_segment_count=seg.source_segment_count,
        )
        for seg in result.segments
    ]

    return PipeExtractionResponse(
        status="extracted",
        filename=file.filename or "unknown",
        raw_segment_count=result.raw_segment_count,
        segments=segments_schema,
        segment_count=len(segments_schema),
        steps_applied=result.steps_applied,
        warnings=result.warnings,
        processing_time_ms=result.processing_time_ms,
        skeleton_width=result.skeleton_image_shape[1],
        skeleton_height=result.skeleton_image_shape[0],
    )
