"""
Request/response schemas for the /extract endpoint.

Phase 1 scope: this endpoint only validates the uploaded file and
acknowledges receipt. No OCR, detection, or AI processing happens yet
- those arrive in later phases and will extend `ExtractResponse`.
"""
from pydantic import BaseModel, Field


class ExtractResponse(BaseModel):
    status: str = Field(..., examples=["received"])
    filename: str
    content_type: str
    size_bytes: int


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])
    app_name: str
    environment: str
