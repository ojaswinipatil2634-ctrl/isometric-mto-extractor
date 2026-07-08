"""
Mock extraction pipeline.

Used whenever GEMINI_API_KEY is absent (Settings.mock_mode == True), or as
a fallback if a live Gemini call fails. Produces a realistic, deterministic
sample MTO so the frontend and business logic can always be exercised
end-to-end without any external dependency.
"""
from __future__ import annotations

from app.schemas.mto import (
    DrawingMetadata,
    ExtractionRaw,
    Fitting,
    ComponentType,
    PipeSegment,
    Weld,
    Support,
)


def mock_extraction(filename: str) -> ExtractionRaw:
    """Return a realistic, fixed sample extraction.

    Values are chosen to resemble a typical small cooling-water line so the
    downstream business-logic derivations (gaskets/bolt sets per flanged
    joint) produce sensible, reviewable numbers.
    """
    return ExtractionRaw(
        metadata=DrawingMetadata(
            drawing_number=f"MOCK-{abs(hash(filename)) % 9000 + 1000}",
            revision="B",
            line_number="6\"-CW-1024-A1A",
            material_class="A106-B",
            service="Cooling Water",
            nps="6\"",
        ),
        pipe_segments=[
            PipeSegment(nps="6\"", length_m=12.4, schedule="STD"),
            PipeSegment(nps="4\"", length_m=5.2, schedule="STD"),
        ],
        fittings=[
            Fitting(type=ComponentType.ELBOW, nps="6\"", quantity=4, rating=None),
            Fitting(type=ComponentType.ELBOW, nps="4\"", quantity=2, rating=None),
            Fitting(type=ComponentType.TEE, nps="6\"", quantity=1, rating=None),
            Fitting(type=ComponentType.REDUCER, nps="6x4", quantity=1, rating=None),
            Fitting(type=ComponentType.FLANGE, nps="6\"", quantity=6, rating="150#"),
            Fitting(type=ComponentType.FLANGE, nps="4\"", quantity=2, rating="150#"),
            Fitting(type=ComponentType.VALVE, nps="6\"", quantity=2, rating="150#"),
        ],
        welds=[Weld(weld_type="Butt Weld", quantity=9)],
        supports=[Support(support_type="Pipe Shoe", quantity=3)],
        confidence=0.60,
    )
