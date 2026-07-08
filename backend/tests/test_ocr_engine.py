"""
Tests that the app degrades cleanly when PaddleOCR isn't installed.

Deliberately NOT mocked: this test suite runs in an environment where
`paddleocr` genuinely is not installed (it's a heavy, platform-specific
dependency not needed to test the app's graceful-degradation path), so
`get_ocr_engine()` hits a real `ModuleNotFoundError` and we assert the
app turns that into a clean `OcrUnavailableError` / 503 response rather
than crashing - exactly the behavior Phase 3 requires ("If OCR is
unavailable, return structured error. Do NOT fabricate OCR output.").

If paddleocr/paddlepaddle ARE installed in the environment running
these tests (e.g. on a fully provisioned Windows machine), the first
test is skipped since it would otherwise attempt a real model
download/initialization, which is out of scope for a unit test.
"""
import importlib.util

import pytest

from app.core.errors import OcrUnavailableError
from app.services.ocr import engine as ocr_engine

_PADDLEOCR_INSTALLED = importlib.util.find_spec("paddleocr") is not None


@pytest.fixture(autouse=True)
def _reset_engine_cache():
    ocr_engine.reset_engine_cache_for_tests()
    yield
    ocr_engine.reset_engine_cache_for_tests()


@pytest.mark.skipif(_PADDLEOCR_INSTALLED, reason="paddleocr is installed in this environment")
def test_get_ocr_engine_raises_structured_error_when_paddleocr_missing():
    with pytest.raises(OcrUnavailableError) as exc_info:
        ocr_engine.get_ocr_engine()

    assert exc_info.value.code == "OCR_UNAVAILABLE"
    assert exc_info.value.status_code == 503
    assert "paddleocr" in exc_info.value.details["reason"].lower()


@pytest.mark.skipif(_PADDLEOCR_INSTALLED, reason="paddleocr is installed in this environment")
def test_get_ocr_engine_caches_the_failure_instead_of_retrying_every_call():
    with pytest.raises(OcrUnavailableError):
        ocr_engine.get_ocr_engine()

    # Second call should hit the cached failure reason, not attempt
    # another (slow, doomed) import.
    with pytest.raises(OcrUnavailableError) as exc_info:
        ocr_engine.get_ocr_engine()
    assert exc_info.value.code == "OCR_UNAVAILABLE"


def test_recognize_wraps_engine_runtime_errors():
    """The engine adapter itself must not let raw engine exceptions
    escape as unhandled 500s - only OcrUnavailableError."""

    class ExplodingRawOcr:
        def ocr(self, image, cls=True):
            raise RuntimeError("simulated engine crash")

    wrapped = ocr_engine.PaddleOcrEngine(ExplodingRawOcr())

    with pytest.raises(OcrUnavailableError) as exc_info:
        wrapped.recognize(image="fake-image-array")

    assert exc_info.value.code == "OCR_UNAVAILABLE"
    assert "simulated engine crash" in exc_info.value.details["reason"]


def test_recognize_handles_no_text_detected_without_raising():
    class EmptyRawOcr:
        def ocr(self, image, cls=True):
            return [None]

    wrapped = ocr_engine.PaddleOcrEngine(EmptyRawOcr())

    lines = wrapped.recognize(image="fake-image-array")

    assert lines == []


def test_recognize_parses_paddleocr_raw_result_shape():
    """Matches PaddleOCR 2.x's actual `.ocr()` return shape:
    [ [ [bbox, (text, confidence)], ... ] ] - one outer list per image."""

    class FakeRawOcr:
        def ocr(self, image, cls=True):
            return [
                [
                    [[[0, 0], [100, 0], [100, 20], [0, 20]], ("DWG NO. MTO-1", 0.95)],
                    [[[0, 30], [100, 30], [100, 50], [0, 50]], ("REV A", 0.88)],
                ]
            ]

    wrapped = ocr_engine.PaddleOcrEngine(FakeRawOcr())

    lines = wrapped.recognize(image="fake-image-array")

    assert len(lines) == 2
    assert lines[0].text == "DWG NO. MTO-1"
    assert lines[0].confidence == pytest.approx(0.95)
    assert lines[1].text == "REV A"
