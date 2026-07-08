"""Request/response schema for the Phase 9 /verify endpoint."""
from pydantic import BaseModel, Field


class VerificationResponse(BaseModel):
    status: str = Field(..., examples=["reviewed"])
    filename: str
    available: bool = Field(
        ..., description="False if Gemini verification was skipped (no API key, or the request failed)."
    )
    corrections: list[str]
    missing_items: list[str]
    ocr_flags: list[str]
    warnings: list[str]
    processing_time_ms: float
