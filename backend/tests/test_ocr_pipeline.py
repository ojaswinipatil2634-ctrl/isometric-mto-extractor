"""
Tests for OcrPipeline's orchestration: preprocessing -> OCR -> field
extraction -> result assembly.

Uses a fake engine (implementing the same `.recognize()` interface as
`PaddleOcrEngine`) injected via `OcrPipeline(engine_factory=...)`, so
these tests exercise the real orchestration logic without depending on
PaddleOCR being installed. The engine-unavailable path itself (when
PaddleOCR genuinely isn't installed) is covered separately in
test_ocr_engine.py against the real `get_ocr_engine()`.
"""
import pytest

from app.core.errors import OcrUnavailableError
from app.services.ocr.engine import RawOcrLine
from app.services.ocr.pipeline import OcrPipeline
from tests.fixtures import encode_png_bytes, make_line_drawing


class FakeEngine:
    """Stub OCR engine returning a fixed, known set of text lines -
    stands in for PaddleOCR so the pipeline's own logic (not PaddleOCR's
    accuracy) is what's under test here."""

    def __init__(self, lines: list[RawOcrLine]):
        self._lines = lines

    def recognize(self, image) -> list[RawOcrLine]:
        return self._lines


def _line(text, confidence=0.9, bbox=None):
    return RawOcrLine(text=text, confidence=confidence, bbox=bbox or [[0, 0], [10, 0], [10, 10], [0, 10]])


def test_pipeline_runs_preprocessing_then_ocr_then_field_extraction():
    img = make_line_drawing()
    png_bytes = encode_png_bytes(img)

    fake_lines = [_line("DWG NO. MTO-4321-00", 0.96), _line("REV. A", 0.9)]
    pipeline = OcrPipeline(engine_factory=lambda: FakeEngine(fake_lines))

    result = pipeline.run(png_bytes, "image/png")

    assert result.engine_available is True
    assert len(result.text_blocks) == 2
    assert result.text_blocks[0].text == "DWG NO. MTO-4321-00"
    assert result.extracted_fields.drawing_number.value == "MTO-4321-00"
    assert result.extracted_fields.revision.value == "A"
    assert result.average_confidence == pytest.approx((0.96 + 0.9) / 2, abs=1e-4)
    assert result.warnings == []
    assert result.processing_time_ms > 0


def test_pipeline_reports_warning_when_no_text_detected():
    img = make_line_drawing()
    png_bytes = encode_png_bytes(img)

    pipeline = OcrPipeline(engine_factory=lambda: FakeEngine([]))

    result = pipeline.run(png_bytes, "image/png")

    assert result.text_blocks == []
    assert result.average_confidence is None
    assert "No text was detected" in result.warnings[0]
    assert result.extracted_fields.drawing_number.value is None


def test_pipeline_propagates_ocr_unavailable_error():
    img = make_line_drawing()
    png_bytes = encode_png_bytes(img)

    def failing_factory():
        raise OcrUnavailableError("OCR engine is unavailable.", details={"reason": "simulated"})

    pipeline = OcrPipeline(engine_factory=failing_factory)

    with pytest.raises(OcrUnavailableError):
        pipeline.run(png_bytes, "image/png")
