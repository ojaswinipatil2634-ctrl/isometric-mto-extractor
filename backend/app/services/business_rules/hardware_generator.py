"""
Flange-joint hardware generation.

For every graph node (Phase 6) tagged as a detected `flange` fitting,
generates the consumable hardware a real flanged joint needs: 1
gasket, N stud bolts, and 2N nuts (a stud bolt threads on both ends and
takes one nut per end). N and the bolt diameter come from
bolt_table.py, driven by the drawing's OCR-extracted NPS/material class
(Phase 3) as the best available estimate - a flanged joint's specific
size can't be tied to an individual graph node without per-run
dimension context, so the sheet's title-block NPS/class is used for
every flange on it.

Per project rules, Gemini never generates or extracts anything here -
this is a deterministic lookup, nothing else.
"""
from dataclasses import dataclass

from app.services.business_rules.bolt_table import lookup_bolt_spec


@dataclass
class HardwareLineItem:
    item_type: str  # "gasket" | "stud_bolt" | "nut"
    node_id: int
    quantity: int
    size: str
    is_estimated: bool


def generate_hardware_for_flanges(
    flange_node_ids: list[int], nps_inches: float | None, rating_class: int | None
) -> list[HardwareLineItem]:
    """Never fabricates a flange that wasn't detected - only produces
    line items for node ids the caller already confirmed are flanges."""
    if not flange_node_ids:
        return []

    bolt_spec, is_estimated = lookup_bolt_spec(nps_inches, rating_class)
    size_label = f'{nps_inches}" NPS' if nps_inches is not None else "unknown NPS"

    items: list[HardwareLineItem] = []
    for node_id in sorted(flange_node_ids):
        items.append(HardwareLineItem("gasket", node_id, 1, size_label, is_estimated))
        items.append(
            HardwareLineItem("stud_bolt", node_id, bolt_spec.bolt_count, bolt_spec.bolt_diameter_in, is_estimated)
        )
        items.append(
            HardwareLineItem("nut", node_id, bolt_spec.bolt_count * 2, bolt_spec.bolt_diameter_in, is_estimated)
        )
    return items
