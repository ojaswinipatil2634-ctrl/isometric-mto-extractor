"""Request/response schemas for the Phase 7 /business-rules endpoint."""
from pydantic import BaseModel, Field


class HardwareLineItemSchema(BaseModel):
    item_type: str = Field(..., examples=["gasket", "stud_bolt", "nut"])
    node_id: int
    quantity: int
    size: str
    is_estimated: bool = Field(
        ..., description="True if the exact NPS/rating class wasn't available and a default was used."
    )


class RuleViolationSchema(BaseModel):
    rule_code: str = Field(
        ..., examples=["MISSING_FITTING", "UNTERMINATED_PIPE", "INVALID_REDUCER", "IMPOSSIBLE_CONNECTION"]
    )
    severity: str = Field(..., examples=["warning", "error"])
    message: str
    node_ids: list[int]


class DuplicateFittingSchema(BaseModel):
    class_name: str
    detection_indices: tuple[int, int]
    iou: float
    bbox_a: tuple[float, float, float, float]
    bbox_b: tuple[float, float, float, float]


class BusinessRulesResponse(BaseModel):
    status: str = Field(..., examples=["evaluated"])
    filename: str
    hardware: list[HardwareLineItemSchema]
    hardware_count: int
    violations: list[RuleViolationSchema]
    violation_count: int
    duplicate_fittings: list[DuplicateFittingSchema]
    duplicate_fitting_count: int
    steps_applied: list[str]
    warnings: list[str]
    processing_time_ms: float
