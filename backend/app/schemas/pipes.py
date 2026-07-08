"""Request/response schemas for the Phase 5 /pipes endpoint."""
from pydantic import BaseModel, Field


class PipePoint(BaseModel):
    x: float
    y: float


class PipeSegmentSchema(BaseModel):
    start: PipePoint
    end: PipePoint
    length_px: float
    angle_degrees: float = Field(..., description="Segment angle, normalized to [0, 180) degrees.")
    orientation: str = Field(..., examples=["horizontal", "vertical", "diagonal"])
    source_segment_count: int = Field(
        ..., description="How many raw Hough segments were merged to produce this pipe run."
    )


class PipeExtractionResponse(BaseModel):
    status: str = Field(..., examples=["extracted"])
    filename: str
    raw_segment_count: int = Field(..., description="Number of raw Hough line segments before merging.")
    segments: list[PipeSegmentSchema]
    segment_count: int = Field(..., description="Number of merged pipe-run segments.")
    steps_applied: list[str]
    warnings: list[str]
    processing_time_ms: float
    skeleton_width: int
    skeleton_height: int
