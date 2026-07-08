"""
Deterministic mock extraction.

Used whenever GEMINI_API_KEY is absent, or as a fallback if a live
Gemini call fails/returns an invalid payload. Ported from the
reference `isometric-mto` submission's `mock_service.py`, which
implements exactly the graceful-degradation behavior the take-home
spec requires (section 3.3): "if no API key is configured, the app
must still run end-to-end and return a clearly-labelled mock/sample
MTO". Values resemble a small cooling-water line so gasket/bolt-set
derivation downstream produces sensible, reviewable numbers.
"""
from app.schemas.vision_extraction import (
    FittingRaw,
    PipeSegmentRaw,
    VisionDrawingMetadata,
    VisionExtractionRaw,
)


def mock_extraction(filename: str) -> VisionExtractionRaw:
    return VisionExtractionRaw(
        metadata=VisionDrawingMetadata(
            drawing_number=f"MOCK-{abs(hash(filename)) % 9000 + 1000}",
            revision="B",
            line_number='6"-CW-1024-A1A',
            nps='6"',
            material_class="A1A",
            service="Cooling Water",
        ),
        pipe_segments=[
            PipeSegmentRaw(nps='6"', length_m=12.4, schedule="STD", material_spec="ASTM A106 Gr.B"),
            PipeSegmentRaw(nps='4"', length_m=5.2, schedule="STD", material_spec="ASTM A106 Gr.B"),
        ],
        fittings=[
            FittingRaw(
                category="FITTING", subtype="elbow_90_lr", size_nps='6"', schedule_rating="SCH 40",
                material_spec="ASTM A234 WPB", end_type="BW", quantity=4,
            ),
            FittingRaw(
                category="FITTING", subtype="elbow_90_lr", size_nps='4"', schedule_rating="SCH 40",
                material_spec="ASTM A234 WPB", end_type="BW", quantity=2,
            ),
            FittingRaw(
                category="FITTING", subtype="tee_equal", size_nps='6"', schedule_rating="SCH 40",
                material_spec="ASTM A234 WPB", end_type="BW", quantity=1,
            ),
            FittingRaw(
                category="FITTING", subtype="reducer_concentric", size_nps='6"x4"', schedule_rating="SCH 40",
                material_spec="ASTM A234 WPB", end_type="BW", quantity=1,
            ),
            FittingRaw(
                category="FLANGE", subtype="weld_neck_flange", size_nps='6"', schedule_rating="CL150",
                material_spec="ASTM A105", end_type="FLGD", quantity=6, rating="CL150",
            ),
            FittingRaw(
                category="FLANGE", subtype="weld_neck_flange", size_nps='4"', schedule_rating="CL150",
                material_spec="ASTM A105", end_type="FLGD", quantity=2, rating="CL150",
            ),
            FittingRaw(
                category="VALVE", subtype="gate_valve", size_nps='6"', schedule_rating="CL150",
                material_spec="ASTM A216 WCB", end_type="FLGD", quantity=2, rating="CL150",
            ),
        ],
        overall_confidence=0.6,
    )
