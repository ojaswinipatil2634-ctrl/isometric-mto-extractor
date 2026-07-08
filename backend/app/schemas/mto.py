"""Request/response schemas for the Phase 8 /mto endpoints."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.business_rules import HardwareLineItemSchema, RuleViolationSchema
from app.schemas.vision_extraction import VisionMTOItem as MTOItemSchema


class SymbolDetectionInfoSchema(BaseModel):
    """
    Informational only - never gates whether an MTO/CSV is produced.
    `enabled=False` just means this run's graph/hardware/violations were
    built from OCR + pipe geometry alone, because no YOLO weights file
    was available; the rest of the response is unaffected.
    """

    enabled: bool
    reason: str | None = None


class MTOExtractionResponse(BaseModel):
    id: int
    status: str = Field(..., examples=["extracted"])
    filename: str
    created_at: datetime

    drawing_number: str | None = None
    revision: str | None = None
    line_number: str | None = None
    service: str | None = None
    material_class: str | None = None
    nps_values: list[str]

    # Actual MTO line items - the primary deliverable (spec section 3.4).
    items: list[MTOItemSchema]
    mto_summary: dict
    extraction_source: str  # "gemini" | "mock"
    used_mock: bool

    node_count: int
    edge_count: int
    branch_count: int
    dead_end_count: int
    loop_count: int
    is_fully_connected: bool

    hardware: list[HardwareLineItemSchema]
    violations: list[RuleViolationSchema]
    duplicate_fitting_count: int

    symbol_detection: SymbolDetectionInfoSchema

    warnings: list[str]
    processing_time_ms: float


class MTOHistoryItemSchema(BaseModel):
    id: int
    filename: str
    created_at: datetime
    drawing_number: str | None = None
    revision: str | None = None
    node_count: int
    hardware_count: int
    violation_count: int


class MTOHistoryResponse(BaseModel):
    items: list[MTOHistoryItemSchema]
    total_count: int
    limit: int
    offset: int
