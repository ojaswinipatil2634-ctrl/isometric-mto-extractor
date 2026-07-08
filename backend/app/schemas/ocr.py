"""Request/response schemas for the Phase 3 /ocr endpoint."""
from pydantic import BaseModel, Field


class TextBlock(BaseModel):
    text: str
    confidence: float
    bbox: list[list[float]] = Field(
        ..., description="4-point polygon [[x, y], ...] as returned by PaddleOCR."
    )


class FieldValue(BaseModel):
    value: str | None
    confidence: float | None
    source_text: str | None
    bbox: list[list[float]] | None


class ExtractedFields(BaseModel):
    drawing_number: FieldValue
    revision: FieldValue
    line_number: FieldValue
    service: FieldValue
    material_class: FieldValue
    nps: list[FieldValue]
    dimensions: list[FieldValue]


class OcrResponse(BaseModel):
    status: str = Field(..., examples=["extracted"])
    filename: str
    engine_available: bool
    text_blocks: list[TextBlock]
    text_block_count: int
    extracted_fields: ExtractedFields
    average_confidence: float | None
    warnings: list[str]
    processing_time_ms: float
