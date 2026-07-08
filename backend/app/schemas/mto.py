"""
Pydantic schemas defining the structured MTO (Material Take-Off) contract.

This is the strict JSON shape we require from Gemini Vision, and also the
shape the mock pipeline must produce, so that both code paths are
indistinguishable to the frontend.
"""
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field, field_validator


class ComponentType(str, Enum):
    PIPE = "pipe"
    ELBOW = "elbow"
    TEE = "tee"
    REDUCER = "reducer"
    FLANGE = "flange"
    VALVE = "valve"
    GASKET = "gasket"
    BOLT_SET = "bolt_set"
    WELD = "weld"
    SUPPORT = "support"


class DrawingMetadata(BaseModel):
    drawing_number: str = Field(..., description="Drawing / document number")
    revision: str = Field(default="A", description="Revision letter/number")
    line_number: str = Field(default="UNKNOWN", description="Piping line number")
    material_class: str = Field(default="UNKNOWN", description="Piping material class, e.g. A106-B")
    service: str = Field(default="UNKNOWN", description="Process service, e.g. Cooling Water")
    nps: str = Field(default="UNKNOWN", description="Nominal pipe size, e.g. 6\"")


class PipeSegment(BaseModel):
    nps: str
    length_m: float = Field(ge=0)
    schedule: str = Field(default="STD")


class Fitting(BaseModel):
    type: ComponentType
    nps: str
    quantity: int = Field(ge=0)
    rating: str | None = Field(default=None, description="Pressure rating, e.g. 150#, if applicable")

    @field_validator("quantity")
    @classmethod
    def non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("quantity cannot be negative")
        return v


class Weld(BaseModel):
    weld_type: str = Field(default="Butt Weld")
    quantity: int = Field(ge=0)


class Support(BaseModel):
    support_type: str = Field(default="Pipe Support")
    quantity: int = Field(ge=0)


class ExtractionRaw(BaseModel):
    """The raw shape we ask Gemini to return. Deliberately permissive on
    numeric formatting since vision models are inconsistent about units —
    normalization happens downstream in the pipeline, not in this schema.
    """
    metadata: DrawingMetadata
    pipe_segments: list[PipeSegment] = Field(default_factory=list)
    fittings: list[Fitting] = Field(default_factory=list)
    welds: list[Weld] = Field(default_factory=list)
    supports: list[Support] = Field(default_factory=list)
    confidence: float = Field(default=0.75, ge=0, le=1)


class MTOLineItem(BaseModel):
    """A single row in the final Material Take-Off table."""
    component: str
    nps: str
    unit: str  # "m" for pipe, "ea" for count-based items
    quantity: float
    rating: str | None = None
    notes: str | None = None


class MTOSummary(BaseModel):
    total_pipe_length_m: float
    total_fittings: int
    total_flanged_joints: int
    total_gaskets: int
    total_bolt_sets: int
    total_valves: int
    total_welds: int


class MTOResult(BaseModel):
    """The full API response contract returned by POST /api/extract."""
    metadata: DrawingMetadata
    line_items: list[MTOLineItem]
    summary: MTOSummary
    confidence: float
    mock_mode: bool
    warnings: list[str] = Field(default_factory=list)
