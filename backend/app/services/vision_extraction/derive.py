"""
Turns a `VisionExtractionRaw` (Gemini or mock output) into the final
`VisionMTOItem` rows the API/CSV/JSON/Excel export actually serve.

Rules implemented here (per take-home spec section 2.2):
- Pipe is quantified by total length in meters, one row per NPS.
- Fittings/flanges/valves are quantified by count ("EA").
- One gasket per flanged joint, one bolt SET per flanged joint. A
  "flanged joint" = one flange face, so the FLANGE quantity IS the
  joint count for MTO purposes - the same convention already used (and
  explained) in the reference isometric-mto submission.
- Bolt count/diameter comes from `business_rules/bolt_table.py`
  (reused as-is, unchanged) keyed by NPS + rating class; unmatched
  combinations fall back to a conservative default and are flagged via
  a lower confidence score + remark rather than presented as exact.
"""
import re

from app.schemas.vision_extraction import VisionExtractionRaw, VisionMTOItem
from app.services.business_rules.bolt_table import lookup_bolt_spec

_NPS_NUMBER_RE = re.compile(r"(\d+(?:\.\d+)?)")
_RATING_NUMBER_RE = re.compile(r"(\d{2,4})")

_CATEGORY_LABELS = {
    "elbow_90_lr": "90° LR Elbow, BW, ASME B16.9",
    "elbow_45_lr": "45° LR Elbow, BW, ASME B16.9",
    "elbow_90_sr": "90° SR Elbow, BW, ASME B16.9",
    "tee_equal": "Equal Tee, BW, ASME B16.9",
    "tee_reducing": "Reducing Tee, BW, ASME B16.9",
    "reducer_concentric": "Concentric Reducer, BW, ASME B16.9",
    "reducer_eccentric": "Eccentric Reducer, BW, ASME B16.9",
    "cap": "Pipe Cap, BW, ASME B16.9",
    "coupling": "Coupling, SW/THD, ASME B16.11",
    "weldolet": "Weldolet Branch Connection, ASME B16.11",
    "gate_valve": "Gate Valve",
    "globe_valve": "Globe Valve",
    "check_valve": "Check Valve",
    "ball_valve": "Ball Valve",
    "butterfly_valve": "Butterfly Valve",
    "weld_neck_flange": "Weld-Neck Flange, ASME B16.5",
    "slip_on_flange": "Slip-On Flange, ASME B16.5",
    "blind_flange": "Blind Flange, ASME B16.5",
}


def _describe(subtype: str) -> str:
    return _CATEGORY_LABELS.get(subtype, subtype.replace("_", " ").title())


def _parse_nps_inches(size_nps: str | None) -> float | None:
    if not size_nps:
        return None
    match = _NPS_NUMBER_RE.search(size_nps)
    return float(match.group(1)) if match else None


def _parse_rating_class(rating: str | None) -> int | None:
    if not rating:
        return None
    match = _RATING_NUMBER_RE.search(rating)
    return int(match.group(1)) if match else None


def build_mto_items(raw: VisionExtractionRaw) -> list[VisionMTOItem]:
    items: list[VisionMTOItem] = []
    item_no = 1
    confidence = raw.overall_confidence

    # --- Pipe, grouped by NPS ---
    pipe_by_nps: dict[str, float] = {}
    for seg in raw.pipe_segments:
        if seg.length_m <= 0:
            continue
        pipe_by_nps[seg.nps] = pipe_by_nps.get(seg.nps, 0.0) + seg.length_m

    for nps, total_len in sorted(pipe_by_nps.items()):
        items.append(
            VisionMTOItem(
                item_no=item_no,
                category="PIPE",
                description="Pipe, Seamless, BE, ASME B36.10",
                size_nps=nps,
                unit="M",
                quantity=round(total_len, 2),
                length_m=round(total_len, 2),
                confidence=confidence,
            )
        )
        item_no += 1

    # --- Fittings / flanges / valves ---
    flanged_joint_count = 0
    for f in raw.fittings:
        if f.quantity <= 0:
            continue
        items.append(
            VisionMTOItem(
                item_no=item_no,
                category=f.category,
                description=_describe(f.subtype),
                size_nps=f.size_nps,
                schedule_rating=f.schedule_rating,
                material_spec=f.material_spec,
                end_type=f.end_type,
                unit="EA",
                quantity=f.quantity,
                confidence=confidence,
            )
        )
        item_no += 1
        if f.category == "FLANGE":
            flanged_joint_count += f.quantity
            bolt_spec, is_estimated = lookup_bolt_spec(_parse_nps_inches(f.size_nps), _parse_rating_class(f.rating))

            items.append(
                VisionMTOItem(
                    item_no=item_no,
                    category="GASKET",
                    description="Spiral Wound Gasket, SS316/Graphite, ASME B16.20",
                    size_nps=f.size_nps,
                    schedule_rating=f.rating,
                    unit="EA",
                    quantity=f.quantity,
                    confidence=confidence,
                    remarks="1 per flanged joint",
                )
            )
            item_no += 1
            items.append(
                VisionMTOItem(
                    item_no=item_no,
                    category="BOLT",
                    description=f"Stud Bolt & Nut Set, {bolt_spec.bolt_diameter_in}, ASTM A193 B7 / A194 2H",
                    size_nps=f.size_nps,
                    schedule_rating=f.rating,
                    unit="SET",
                    quantity=f.quantity,
                    confidence=confidence * 0.85 if is_estimated else confidence,
                    remarks=(
                        "Bolt size/count estimated - verify against ASME B16.5/B16.47 before procurement"
                        if is_estimated
                        else f"{bolt_spec.bolt_count} bolts per set"
                    ),
                )
            )
            item_no += 1

    return items
