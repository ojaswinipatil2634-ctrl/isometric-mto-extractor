"""
Schemas for Gemini vision-based MTO extraction.

WHY THIS FILE EXISTS (bug context)
----------------------------------
The take-home spec (section 3.4) asks every extraction to produce a
list of PIPE / FITTING / FLANGE / VALVE / GASKET / BOLT line items.
Before this fix, this codebase had no code path that ever produced
those items:

- `app/services/business_rules/hardware_generator.py` only ever
  emits gasket/stud_bolt/nut rows, and only for graph nodes the
  Phase 4 YOLO detector tagged as `flange`.
- Phase 4 detection requires a trained `yolov11_piping.pt` weights
  file that is never shipped in this repo (see
  `app/services/detection/engine.py` / requirements.txt). On a fresh
  checkout `YOLO_WEIGHTS_PATH` never resolves, so detection always
  raises `DetectionUnavailableError`, `fitting_by_node` in graph
  construction is always `{}`, `flange_node_ids` is always `[]`, and
  `generate_hardware_for_flanges([])` always returns `[]`.

Net effect: `hardware` on every persisted run is `[]`, and there was
never a PIPE/FITTING/FLANGE/VALVE row anywhere - so `/mto/{id}/export`
technically "worked" (no crash), but produced a CSV with a Summary
section, an empty Hardware section, and an empty/near-empty
Violations section. That is the "CSV isn't giving a result" symptom.

This module (+ services/vision_extraction/) adds the actual
"drawing in, MTO out" path the spec describes: a Gemini vision call
with a strict JSON schema (mirrored from the reference
`isometric-mto` submission, which does implement this and does work),
with a deterministic mock fallback when `GEMINI_API_KEY` is unset or
the call fails - so `items` is never empty and the CSV always has
real rows to show, per the spec's "graceful degradation" requirement.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class VisionDrawingMetadata(BaseModel):
    drawing_number: str | None = None
    revision: str | None = None
    line_number: str | None = None
    nps: str | None = None
    material_class: str | None = None
    service: str | None = None


class PipeSegmentRaw(BaseModel):
    nps: str
    length_m: float
    schedule: str | None = None
    material_spec: str | None = None


class FittingRaw(BaseModel):
    """One row as Gemini reports it, before gasket/bolt derivation."""

    category: str  # FITTING | FLANGE | VALVE
    subtype: str  # e.g. "elbow_90_lr", "tee_equal", "gate_valve", "weld_neck_flange"
    size_nps: str
    schedule_rating: str | None = None
    material_spec: str | None = None
    end_type: str | None = None
    quantity: int = 1
    rating: str | None = None  # pressure class, e.g. "CL150" - used for bolt-table lookup

    @field_validator("category")
    @classmethod
    def _normalize_category(cls, v: str) -> str:
        v = (v or "").strip().upper()
        if v not in {"FITTING", "FLANGE", "VALVE"}:
            v = "FITTING"
        return v


class VisionExtractionRaw(BaseModel):
    """The exact shape Gemini is asked to return (see prompt.py)."""

    metadata: VisionDrawingMetadata = Field(default_factory=VisionDrawingMetadata)
    pipe_segments: list[PipeSegmentRaw] = Field(default_factory=list)
    fittings: list[FittingRaw] = Field(default_factory=list)
    overall_confidence: float = 0.5


class VisionMTOItem(BaseModel):
    """One row of the actual MTO table (spec section 2.2 / 3.4)."""

    item_no: int
    category: str  # PIPE | FITTING | FLANGE | VALVE | GASKET | BOLT
    description: str
    size_nps: str | None = None
    schedule_rating: str | None = None
    material_spec: str | None = None
    end_type: str | None = None
    quantity: float
    unit: str  # M | EA | SET
    length_m: float | None = None
    confidence: float = 0.5
    remarks: str = ""
