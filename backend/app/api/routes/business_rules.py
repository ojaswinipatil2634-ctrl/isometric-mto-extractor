"""
/business-rules endpoint.

PHASE 7 SCOPE ONLY:
    Take Phase 6's constructed graph and:
      - Generate flange-joint hardware (gaskets, stud bolts, nuts) for
        every detected flange node, sized from Phase 3's OCR-extracted
        NPS/material class where available.
      - Detect duplicate fittings (Phase 4 detections of the same class
        with heavily overlapping bounding boxes), impossible connections
        (fittings joined by a near-zero-length pipe run), missing
        fittings (branch points with no detected fitting), unterminated
        pipes (dead ends with no detected terminator), and invalid
        reducers (a reducer not sitting between exactly two runs).

No persistence (Phase 8), no AI (Phase 9) - Gemini is never used here or
anywhere in the extraction path; every check and every generated
quantity comes from deterministic graph/geometry/lookup-table logic.

Reuses UploadValidationService from Phase 1 so file-type/size rules
stay defined in exactly one place.
"""
import logging

from fastapi import APIRouter, Depends, UploadFile, File

from app.schemas.business_rules import (
    BusinessRulesResponse,
    DuplicateFittingSchema,
    HardwareLineItemSchema,
    RuleViolationSchema,
)
from app.services.business_rules.pipeline import BusinessRulesPipeline
from app.services.upload_validation_service import UploadValidationService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["business-rules"])


def get_upload_validation_service() -> UploadValidationService:
    return UploadValidationService()


def get_business_rules_pipeline() -> BusinessRulesPipeline:
    return BusinessRulesPipeline()


@router.post("/business-rules", response_model=BusinessRulesResponse)
async def evaluate_business_rules(
    file: UploadFile = File(...),
    validation_service: UploadValidationService = Depends(get_upload_validation_service),
    pipeline: BusinessRulesPipeline = Depends(get_business_rules_pipeline),
) -> BusinessRulesResponse:
    contents = await validation_service.validate(file)

    result = pipeline.run(contents, file.content_type or "")

    logger.info(
        "Business rules '%s': %d violation(s), %d duplicate(s), %d hardware item(s)",
        file.filename, len(result.violations), len(result.duplicate_fittings), len(result.hardware),
    )

    hardware_schema = [
        HardwareLineItemSchema(
            item_type=item.item_type,
            node_id=item.node_id,
            quantity=item.quantity,
            size=item.size,
            is_estimated=item.is_estimated,
        )
        for item in result.hardware
    ]

    violations_schema = [
        RuleViolationSchema(
            rule_code=v.rule_code, severity=v.severity, message=v.message, node_ids=v.node_ids
        )
        for v in result.violations
    ]

    duplicates_schema = [
        DuplicateFittingSchema(
            class_name=d.class_name,
            detection_indices=d.detection_indices,
            iou=d.iou,
            bbox_a=d.bbox_a,
            bbox_b=d.bbox_b,
        )
        for d in result.duplicate_fittings
    ]

    return BusinessRulesResponse(
        status="evaluated",
        filename=file.filename or "unknown",
        hardware=hardware_schema,
        hardware_count=len(hardware_schema),
        violations=violations_schema,
        violation_count=len(violations_schema),
        duplicate_fittings=duplicates_schema,
        duplicate_fitting_count=len(duplicates_schema),
        steps_applied=result.steps_applied,
        warnings=result.warnings,
        processing_time_ms=result.processing_time_ms,
    )
