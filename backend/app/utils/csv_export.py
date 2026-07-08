"""CSV export utility for MTO results, built with pandas as required."""
from __future__ import annotations

import io

import pandas as pd

from app.schemas.mto import MTOResult


def mto_to_csv(result: MTOResult) -> str:
    """Render an MTOResult as CSV text, with a header block of metadata
    followed by the line-item table.
    """
    rows = [
        {
            "Component": li.component,
            "NPS": li.nps,
            "Unit": li.unit,
            "Quantity": li.quantity,
            "Rating": li.rating or "",
            "Notes": li.notes or "",
        }
        for li in result.line_items
    ]
    df = pd.DataFrame(rows, columns=["Component", "NPS", "Unit", "Quantity", "Rating", "Notes"])

    buf = io.StringIO()
    buf.write(f"# Drawing Number,{result.metadata.drawing_number}\n")
    buf.write(f"# Revision,{result.metadata.revision}\n")
    buf.write(f"# Line Number,{result.metadata.line_number}\n")
    buf.write(f"# Material Class,{result.metadata.material_class}\n")
    buf.write(f"# Service,{result.metadata.service}\n")
    buf.write(f"# Mock Mode,{result.mock_mode}\n")
    buf.write("\n")
    df.to_csv(buf, index=False)
    return buf.getvalue()
