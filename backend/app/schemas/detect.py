"""Request/response schemas for the Phase 4 /detect endpoint."""
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class Detection(BaseModel):
    class_name: str = Field(..., examples=["gate_valve"])
    confidence: float
    bbox: BoundingBox


class DetectResponse(BaseModel):
    status: str = Field(..., examples=["detected"])
    filename: str
    engine_available: bool
    detections: list[Detection]
    detection_count: int
    counts_by_class: dict[str, int]
    confidence_threshold: float
    warnings: list[str]
    processing_time_ms: float
