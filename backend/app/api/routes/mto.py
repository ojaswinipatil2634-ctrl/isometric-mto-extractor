"""
/mto endpoints.

PHASE 8 SCOPE ONLY:
    Run the full extraction pipeline (Phase 3 OCR + Phase 6 graph +
    Phase 7 business rules combined) and persist the result to SQLite,
    then serve it back via history/detail/export. Nothing new is
    extracted here - Gemini is never used, and no phase before this one
    is modified; this is composition + persistence + export over what
    they already produce.

Endpoints:
    POST   /mto                    - run the full pipeline, persist, return it
    GET    /mto/history             - list past runs (summary only)
    GET    /mto/{run_id}            - full stored detail for one run
    GET    /mto/{run_id}/export     - download as CSV, JSON, or Excel
"""
import logging

from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import RunNotFoundError
from app.models.mto_run import MTOExtractionRun
from app.repositories.mto_run_repository import MTORunRepository
from app.schemas.business_rules import HardwareLineItemSchema, RuleViolationSchema
from app.schemas.mto import (
    MTOExtractionResponse,
    MTOHistoryItemSchema,
    MTOHistoryResponse,
    SymbolDetectionInfoSchema,
)
from app.services.mto.export_service import to_csv_bytes, to_json_bytes, to_xlsx_bytes
from app.services.mto.persistence_service import build_run_record
from app.services.mto.pipeline import MTOExtractionPipeline
from app.services.upload_validation_service import UploadValidationService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["mto"])

_EXPORT_MEDIA_TYPES = {
    "csv": "text/csv",
    "json": "application/json",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def get_upload_validation_service() -> UploadValidationService:
    return UploadValidationService()


def get_mto_pipeline() -> MTOExtractionPipeline:
    return MTOExtractionPipeline()


def _run_to_response(run: MTOExtractionRun) -> MTOExtractionResponse:
    return MTOExtractionResponse(
        id=run.id,
        status="extracted",
        filename=run.filename,
        created_at=run.created_at,
        drawing_number=run.drawing_number,
        revision=run.revision,
        line_number=run.line_number,
        service=run.service,
        material_class=run.material_class,
        nps_values=run.nps_values,
        items=run.items,
        mto_summary=run.mto_summary,
        extraction_source=run.extraction_source,
        used_mock=run.used_mock,
        node_count=run.node_count,
        edge_count=run.edge_count,
        branch_count=run.branch_count,
        dead_end_count=run.dead_end_count,
        loop_count=run.loop_count,
        is_fully_connected=run.is_fully_connected,
        hardware=[HardwareLineItemSchema(**item) for item in run.hardware],
        violations=[RuleViolationSchema(**v) for v in run.violations],
        duplicate_fitting_count=run.duplicate_fitting_count,
        symbol_detection=SymbolDetectionInfoSchema(
            enabled=run.symbol_detection_enabled,
            reason=run.symbol_detection_reason,
        ),
        warnings=run.warnings,
        processing_time_ms=run.processing_time_ms,
    )


@router.post("/mto", response_model=MTOExtractionResponse)
async def run_and_persist_extraction(
    file: UploadFile = File(...),
    validation_service: UploadValidationService = Depends(get_upload_validation_service),
    pipeline: MTOExtractionPipeline = Depends(get_mto_pipeline),
    db: Session = Depends(get_db),
) -> MTOExtractionResponse:
    contents = await validation_service.validate(file)
    filename = file.filename or "unknown"

    result = pipeline.run(contents, file.content_type or "", filename)

    record = build_run_record(filename, result)
    saved = MTORunRepository(db).create(record)

    logger.info(
        "Persisted MTO run #%d for '%s': %d hardware item(s), %d violation(s)",
        saved.id, filename, len(saved.hardware), len(saved.violations),
    )

    return _run_to_response(saved)


@router.get("/mto/history", response_model=MTOHistoryResponse)
async def list_extraction_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> MTOHistoryResponse:
    repo = MTORunRepository(db)
    runs = repo.list_recent(limit=limit, offset=offset)
    total = repo.count_all()

    items = [
        MTOHistoryItemSchema(
            id=run.id,
            filename=run.filename,
            created_at=run.created_at,
            drawing_number=run.drawing_number,
            revision=run.revision,
            node_count=run.node_count,
            hardware_count=len(run.hardware),
            violation_count=len(run.violations),
        )
        for run in runs
    ]

    return MTOHistoryResponse(items=items, total_count=total, limit=limit, offset=offset)


@router.get("/mto/{run_id}", response_model=MTOExtractionResponse)
async def get_extraction_run(run_id: int, db: Session = Depends(get_db)) -> MTOExtractionResponse:
    run = MTORunRepository(db).get_by_id(run_id)
    if run is None:
        raise RunNotFoundError(f"No MTO extraction run found with id {run_id}.")

    return _run_to_response(run)


@router.get("/mto/{run_id}/export")
async def export_extraction_run(
    run_id: int,
    format: str = Query("json", pattern="^(csv|json|xlsx)$"),
    db: Session = Depends(get_db),
) -> Response:
    run = MTORunRepository(db).get_by_id(run_id)
    if run is None:
        raise RunNotFoundError(f"No MTO extraction run found with id {run_id}.")

    if format == "csv":
        content = to_csv_bytes(run)
    elif format == "xlsx":
        content = to_xlsx_bytes(run)
    else:
        content = to_json_bytes(run)

    filename = f"mto_run_{run_id}.{format}"
    return Response(
        content=content,
        media_type=_EXPORT_MEDIA_TYPES[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
