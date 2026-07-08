"""
Tests for POST /api/v1/ocr.

Two kinds of coverage here:
  - a dependency-overridden "happy path" using a fake pipeline, so the
    endpoint's request/response wiring and schema serialization are
    verified without needing PaddleOCR installed
  - the real, non-mocked unavailable-engine path (PaddleOCR genuinely
    isn't installed in this test environment), confirming the endpoint
    returns a clean 503 rather than a 500 or a fabricated result
"""
import io
import importlib.util

import pytest

from app.api.routes.ocr import get_ocr_pipeline
from app.core.errors import OcrUnavailableError
from app.main import app
from app.services.ocr import engine as ocr_engine
from app.services.ocr.field_extractor import ExtractedFields, FieldValue
from app.services.ocr.pipeline import OcrResult, TextBlockResult
from tests.fixtures import encode_png_bytes, make_line_drawing

_PADDLEOCR_INSTALLED = importlib.util.find_spec("paddleocr") is not None


def _empty_field() -> FieldValue:
    return FieldValue(value=None, confidence=None, source_text=None, bbox=None)


class FakePipeline:
    def __init__(self, result: OcrResult | None = None, error: Exception | None = None):
        self._result = result
        self._error = error

    def run(self, contents: bytes, content_type: str) -> OcrResult:
        if self._error:
            raise self._error
        return self._result


def test_ocr_endpoint_returns_extracted_fields_for_a_valid_upload(client):
    fake_result = OcrResult(
        engine_available=True,
        text_blocks=[TextBlockResult(text="DWG NO. MTO-1", confidence=0.95, bbox=[[0, 0], [1, 0], [1, 1], [0, 1]])],
        extracted_fields=ExtractedFields(
            drawing_number=FieldValue(value="MTO-1", confidence=0.95, source_text="DWG NO. MTO-1", bbox=None),
            revision=_empty_field(),
            line_number=_empty_field(),
            service=_empty_field(),
            material_class=_empty_field(),
            nps=[],
            dimensions=[],
        ),
        average_confidence=0.95,
        warnings=[],
        processing_time_ms=12.3,
    )
    app.dependency_overrides[get_ocr_pipeline] = lambda: FakePipeline(result=fake_result)
    try:
        img = make_line_drawing()
        files = {"file": ("drawing.png", io.BytesIO(encode_png_bytes(img)), "image/png")}

        response = client.post("/api/v1/ocr", files=files)

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "extracted"
        assert body["engine_available"] is True
        assert body["text_block_count"] == 1
        assert body["extracted_fields"]["drawing_number"]["value"] == "MTO-1"
        assert body["average_confidence"] == 0.95
    finally:
        app.dependency_overrides.pop(get_ocr_pipeline, None)


def test_ocr_endpoint_rejects_unsupported_file_type(client):
    files = {"file": ("notes.txt", io.BytesIO(b"not a drawing"), "text/plain")}

    response = client.post("/api/v1/ocr", files=files)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_FILE"


def test_ocr_endpoint_returns_structured_error_when_engine_unavailable_via_override(client):
    app.dependency_overrides[get_ocr_pipeline] = lambda: FakePipeline(
        error=OcrUnavailableError("OCR engine is unavailable.", details={"reason": "simulated"})
    )
    try:
        img = make_line_drawing()
        files = {"file": ("drawing.png", io.BytesIO(encode_png_bytes(img)), "image/png")}

        response = client.post("/api/v1/ocr", files=files)

        assert response.status_code == 503
        assert response.json()["error"]["code"] == "OCR_UNAVAILABLE"
    finally:
        app.dependency_overrides.pop(get_ocr_pipeline, None)


@pytest.mark.skipif(_PADDLEOCR_INSTALLED, reason="paddleocr is installed in this environment")
def test_ocr_endpoint_returns_structured_error_with_real_pipeline_when_paddleocr_missing(client):
    """No dependency override here - exercises the real OcrPipeline and
    the real get_ocr_engine(), which genuinely fails because paddleocr
    isn't installed in this test environment. Confirms the app-wide
    behavior end-to-end: unavailable OCR never crashes the request and
    never fabricates a result."""
    ocr_engine.reset_engine_cache_for_tests()
    img = make_line_drawing()
    files = {"file": ("drawing.png", io.BytesIO(encode_png_bytes(img)), "image/png")}

    response = client.post("/api/v1/ocr", files=files)

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "OCR_UNAVAILABLE"
    ocr_engine.reset_engine_cache_for_tests()
