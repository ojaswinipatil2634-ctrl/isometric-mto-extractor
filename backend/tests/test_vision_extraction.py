from app.schemas.vision_extraction import (
    FittingRaw,
    PipeSegmentRaw,
    VisionDrawingMetadata,
    VisionExtractionRaw,
)
from app.services.vision_extraction.client import GeminiExtractionClient
from app.services.vision_extraction.derive import build_mto_items
from app.services.vision_extraction.mock import mock_extraction
from app.services.vision_extraction.pipeline import VisionExtractionPipeline


def test_mock_extraction_is_deterministic_for_a_given_filename():
    a = mock_extraction("drawing.png")
    b = mock_extraction("drawing.png")
    assert a.metadata.drawing_number == b.metadata.drawing_number


def test_build_mto_items_groups_pipe_by_nps():
    raw = VisionExtractionRaw(
        pipe_segments=[
            PipeSegmentRaw(nps='6"', length_m=10.0),
            PipeSegmentRaw(nps='6"', length_m=2.4),
            PipeSegmentRaw(nps='4"', length_m=5.0),
        ],
    )

    items = build_mto_items(raw)
    pipe_items = [i for i in items if i.category == "PIPE"]

    assert {i.size_nps: i.quantity for i in pipe_items} == {'6"': 12.4, '4"': 5.0}
    assert all(i.unit == "M" for i in pipe_items)


def test_build_mto_items_derives_one_gasket_and_one_bolt_set_per_flange():
    raw = VisionExtractionRaw(
        fittings=[
            FittingRaw(
                category="FLANGE", subtype="weld_neck_flange", size_nps='6"',
                quantity=3, rating="CL150",
            ),
        ],
    )

    items = build_mto_items(raw)
    by_category = {i.category: i for i in items}

    assert by_category["FLANGE"].quantity == 3
    assert by_category["GASKET"].quantity == 3
    assert by_category["GASKET"].unit == "EA"
    assert by_category["BOLT"].quantity == 3
    assert by_category["BOLT"].unit == "SET"


def test_build_mto_items_skips_zero_quantity_rows():
    raw = VisionExtractionRaw(
        pipe_segments=[PipeSegmentRaw(nps='6"', length_m=0.0)],
        fittings=[FittingRaw(category="FITTING", subtype="elbow_90_lr", size_nps='6"', quantity=0)],
    )

    assert build_mto_items(raw) == []


def test_gemini_client_reports_unconfigured_without_api_key():
    client = GeminiExtractionClient(api_key=None)
    assert client.is_configured is False

    result, error = client.extract(b"not-a-real-png")
    assert result is None
    assert "GEMINI_API_KEY" in error


def test_pipeline_falls_back_to_mock_when_no_api_key_configured():
    pipeline = VisionExtractionPipeline(gemini_client=GeminiExtractionClient(api_key=None))

    result = pipeline.run(b"irrelevant-bytes", "image/png", "my_drawing.pdf")

    assert result.used_mock is True
    assert result.extraction_source == "mock"
    assert len(result.items) > 0
    assert any("GEMINI_API_KEY" in w for w in result.warnings)


def test_pipeline_falls_back_to_mock_when_gemini_call_fails():
    class _FailingClient:
        is_configured = True

        def extract(self, png_bytes):
            return None, "simulated network failure"

    pipeline = VisionExtractionPipeline(gemini_client=_FailingClient())

    # Uses a real image so preprocessing (encode-to-PNG) succeeds and the
    # (stubbed) Gemini call is actually attempted before falling back.
    from tests.fixtures import encode_png_bytes, make_l_shaped_pipe_drawing

    png_bytes = encode_png_bytes(make_l_shaped_pipe_drawing())
    result = pipeline.run(png_bytes, "image/png", "drawing.png")

    assert result.used_mock is True
    assert any("simulated network failure" in w for w in result.warnings)
    assert len(result.items) > 0


def test_metadata_defaults_are_all_none():
    assert VisionDrawingMetadata() == VisionDrawingMetadata(
        drawing_number=None, revision=None, line_number=None, nps=None, material_class=None, service=None,
    )
