"""API route definitions."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse

from app.config import Settings, get_settings
from app.pipeline.extract import ValidationError, run_pipeline
from app.schemas.mto import MTOResult
from app.utils.csv_export import mto_to_csv

logger = logging.getLogger(__name__)
router = APIRouter()

# Simple in-memory cache of the last result, keyed by request, so the CSV
# export endpoint can re-render without requiring the client to resend the
# whole payload. For a production system this would be a real cache/DB;
# for this assessment scope an in-process store is sufficient and explicit.
_LAST_RESULT: dict[str, MTOResult] = {}


@router.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "mock_mode": settings.mock_mode,
        "model": settings.model_name,
    }


@router.post("/extract", response_model=MTOResult)
async def extract(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
) -> MTOResult:
    raw = await file.read()
    try:
        result = run_pipeline(raw, file.filename or "upload", settings)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive catch-all
        logger.exception("Unexpected pipeline failure")
        raise HTTPException(status_code=500, detail="Internal extraction error") from exc

    _LAST_RESULT["latest"] = result
    return result


@router.get("/export/csv", response_class=PlainTextResponse)
def export_csv() -> str:
    result = _LAST_RESULT.get("latest")
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="No extraction result available yet. Call /api/extract first.",
        )
    return mto_to_csv(result)
