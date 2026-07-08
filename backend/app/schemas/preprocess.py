"""Request/response schemas for the Phase 2 /preprocess endpoint."""
from pydantic import BaseModel, Field


class PreprocessResponse(BaseModel):
    status: str = Field(..., examples=["processed"])
    filename: str
    original_width: int
    original_height: int
    processed_width: int
    processed_height: int
    skew_angle_corrected_degrees: float
    resize_scale_factor: float
    steps_applied: list[str]
    processing_time_ms: float
    processed_image_base64: str = Field(
        ..., description="Final binarized (adaptive threshold) output, PNG-encoded, base64."
    )
    preview_image_base64: str = Field(
        ..., description="Contrast-enhanced (pre-threshold) preview image, PNG-encoded, base64, for human viewing."
    )
