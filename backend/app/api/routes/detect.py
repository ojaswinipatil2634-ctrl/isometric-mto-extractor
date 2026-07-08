"""
/detect endpoint.

PHASE 4 SCOPE ONLY:
    Run YOLOv11 (Ultralytics) against an uploaded drawing (after
    Phase 2's preprocessing) to detect piping symbols and fittings:
    elbows, tees, reducers, gate/globe/check valves, flanges, supports,
    and welds. No pipe/graph extraction (Phase 5/6), no AI verification
    (Phase 9) - Gemini is never used here or anywhere in the extraction
    path.

If ultralytics is not installed, the trained weights file is missing,
or the model otherwise fails to load or process the image, this
returns a structured 503 DETECTION_UNAVAILABLE error (via the app-wide
AppError handler) instead of crashing or fabricating a result.
"""
import logging

from fastapi import APIRouter, Depends, UploadFile, File

from app.schemas.detect import BoundingBox as BoundingBoxSchema, Detection as DetectionSchema, DetectResponse
from app.services.detection.pipeline import DetectionPipeline
from app.services.upload_validation_service import UploadValidationService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["detection"])


def get_upload_validation_service() -> UploadValidationService:
    return UploadValidationService()


def get_detection_pipeline() -> DetectionPipeline:
    return DetectionPipeline()


@router.post("/detect", response_model=DetectResponse)
async def run_detection(
    file: UploadFile = File(...),
    validation_service: UploadValidationService = Depends(get_upload_validation_service),
    pipeline: DetectionPipeline = Depends(get_detection_pipeline),
) -> DetectResponse:
    contents = await validation_service.validate(file)

    result = pipeline.run(contents, file.content_type or "")

    logger.info(
        "Detection '%s': %d object(s) detected, threshold=%.2f",
        file.filename, len(result.detections), result.confidence_threshold,
    )

    detections_schema = [
        DetectionSchema(
            class_name=d.class_name,
            confidence=d.confidence,
            bbox=BoundingBoxSchema(x1=d.bbox_xyxy[0], y1=d.bbox_xyxy[1], x2=d.bbox_xyxy[2], y2=d.bbox_xyxy[3]),
        )
        for d in result.detections
    ]

    return DetectResponse(
        status="detected",
        filename=file.filename or "unknown",
        engine_available=result.engine_available,
        detections=detections_schema,
        detection_count=len(detections_schema),
        counts_by_class=result.counts_by_class,
        confidence_threshold=result.confidence_threshold,
        warnings=result.warnings,
        processing_time_ms=result.processing_time_ms,
    )
