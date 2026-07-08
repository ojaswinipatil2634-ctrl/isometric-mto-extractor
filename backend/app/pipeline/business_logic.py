"""
Domain business logic: turns a raw Gemini/mock extraction into the final
validated MTO the frontend renders.

Rules implemented here (per spec):
- Pipe is quantified by total length (meters), grouped by NPS.
- Fittings/flanges/valves are quantified by count.
- One gasket per flanged joint.
- One bolt set per flanged joint.
- A "flanged joint" = one flange face. In practice this means the flange
  count IS the joint count for MTO purposes (each flange listed represents
  one joint face requiring its own gasket + bolt set), which is the
  standard piping take-off convention.
"""
from __future__ import annotations

from app.schemas.mto import (
    ComponentType,
    ExtractionRaw,
    MTOLineItem,
    MTOResult,
    MTOSummary,
)

COMPONENT_LABELS = {
    ComponentType.ELBOW: "Elbow",
    ComponentType.TEE: "Tee",
    ComponentType.REDUCER: "Reducer",
    ComponentType.FLANGE: "Flange",
    ComponentType.VALVE: "Valve",
    ComponentType.GASKET: "Gasket",
    ComponentType.BOLT_SET: "Bolt Set",
}


def build_mto(extraction: ExtractionRaw, mock_mode: bool) -> MTOResult:
    warnings: list[str] = []
    line_items: list[MTOLineItem] = []

    # --- Pipe segments, grouped by NPS ---
    pipe_by_nps: dict[str, float] = {}
    for seg in extraction.pipe_segments:
        if seg.length_m <= 0:
            warnings.append(f"Ignored non-positive pipe length for NPS {seg.nps}")
            continue
        pipe_by_nps[seg.nps] = pipe_by_nps.get(seg.nps, 0.0) + seg.length_m

    for nps, total_len in sorted(pipe_by_nps.items()):
        line_items.append(
            MTOLineItem(
                component="Pipe",
                nps=nps,
                unit="m",
                quantity=round(total_len, 2),
            )
        )

    # --- Fittings / valves / flanges, grouped by (type, nps, rating) ---
    total_fittings = 0
    total_valves = 0
    flanged_joints = 0

    grouped: dict[tuple[ComponentType, str, str | None], int] = {}
    for f in extraction.fittings:
        key = (f.type, f.nps, f.rating)
        grouped[key] = grouped.get(key, 0) + f.quantity

    for (ctype, nps, rating), qty in sorted(grouped.items(), key=lambda kv: kv[0][0].value):
        if qty <= 0:
            continue
        line_items.append(
            MTOLineItem(
                component=COMPONENT_LABELS.get(ctype, ctype.value.title()),
                nps=nps,
                unit="ea",
                quantity=qty,
                rating=rating,
            )
        )
        if ctype == ComponentType.VALVE:
            total_valves += qty
        elif ctype == ComponentType.FLANGE:
            flanged_joints += qty
        else:
            total_fittings += qty

    # --- Derived: gaskets + bolt sets, one per flanged joint ---
    if flanged_joints > 0:
        line_items.append(
            MTOLineItem(
                component="Gasket",
                nps="Various",
                unit="ea",
                quantity=flanged_joints,
                notes="Derived: 1 per flanged joint",
            )
        )
        line_items.append(
            MTOLineItem(
                component="Bolt Set",
                nps="Various",
                unit="ea",
                quantity=flanged_joints,
                notes="Derived: 1 per flanged joint",
            )
        )

    # --- Welds ---
    total_welds = 0
    for w in extraction.welds:
        if w.quantity > 0:
            line_items.append(
                MTOLineItem(
                    component=w.weld_type,
                    nps="N/A",
                    unit="ea",
                    quantity=w.quantity,
                )
            )
            total_welds += w.quantity

    # --- Supports (bonus) ---
    for s in extraction.supports:
        if s.quantity > 0:
            line_items.append(
                MTOLineItem(
                    component=s.support_type,
                    nps="N/A",
                    unit="ea",
                    quantity=s.quantity,
                )
            )

    if not pipe_by_nps:
        warnings.append("No pipe segments detected; total pipe length is 0.")
    if extraction.confidence < 0.5:
        warnings.append("Low model confidence — please verify quantities manually.")

    summary = MTOSummary(
        total_pipe_length_m=round(sum(pipe_by_nps.values()), 2),
        total_fittings=total_fittings,
        total_flanged_joints=flanged_joints,
        total_gaskets=flanged_joints,
        total_bolt_sets=flanged_joints,
        total_valves=total_valves,
        total_welds=total_welds,
    )

    return MTOResult(
        metadata=extraction.metadata,
        line_items=line_items,
        summary=summary,
        confidence=extraction.confidence,
        mock_mode=mock_mode,
        warnings=warnings,
    )
