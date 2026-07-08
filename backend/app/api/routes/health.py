"""Health check endpoint - used by Docker healthchecks and the frontend."""
from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.extract import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        environment=settings.ENVIRONMENT,
    )
