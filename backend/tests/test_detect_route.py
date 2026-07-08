"""
Tests for POST /api/v1/detect.

Two kinds of coverage here:
  - a dependency-overridden "happy path" using a fake pipeline, so the
    endpoint's request/response wiring and schema serialization are
    verified without needing ultralytics/torch or real weights
  - the real, non-mocked unavailable-engine path (no weights file is
    shipped in this repo), confirming the endpoint returns a clean 503
    rather than a 500 or a fabricated result
"""
import io

import pytest

from app.api.routes.detect import get_detection_pipeline
from app.core.errors import DetectionUnavailableError
from app.main import app
from app.services.detection.pipeline import DetectionItemResult, DetectionResult
from tests.fixtures import encode_png_bytes, make_line_drawing


class FakePipeline:
    def __init__(self, result: DetectionResult | None = None, error: Exception | None = None):
        self._result = result
        self._error = error

    def run(self, contents: bytes, content_type: str) -> DetectionResult:
        if self._error:
            raise self._error
        return self._result


def test_detect_endpoint_returns_detections_for_a_valid_upload(client):
    fake_result = DetectionResult(
        engine_available=True,
        detections=[
            DetectionItemResult(class_name="gate_valve", confidence=0.91, bbox_xyxy=(10.0, 20.0, 50.0, 60.0)),
            DetectionItemResult(class_name="elbow", confidence=0.77, bbox_xyxy=(100.0, 120.0, 140.0, 160.0)),
        ],
        counts_by_class={"gate_valve": 1, "elbow": 1},
        confidence_threshold=0.25,
        warnings=[],
        processing_time_ms=42.0,
    )
    app.dependency_overrides[get_detection_pipeline] = lambda: FakePipeline(result=fake_result)
    try:
        img = make_line_drawing()
        files = {"file": ("drawing.png", io.BytesIO(encode_png_bytes(img)), "image/png")}

        response = client.post("/api/v1/detect", files=files)

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "detected"
        assert body["engine_available"] is True
        assert body["detection_count"] == 2
        assert body["counts_by_class"] == {"gate_valve": 1, "elbow": 1}
        assert body["detections"][0]["class_name"] == "gate_valve"
        assert body["detections"][0]["bbox"] == {"x1": 10.0, "y1": 20.0, "x2": 50.0, "y2": 60.0}
        assert body["confidence_threshold"] == 0.25
    finally:
        app.dependency_overrides.pop(get_detection_pipeline, None)


def test_detect_endpoint_rejects_unsupported_file_type(client):
    files = {"file": ("notes.txt", io.BytesIO(b"not a drawing"), "text/plain")}

    response = client.post("/api/v1/detect", files=files)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_FILE"


def test_detect_endpoint_returns_structured_error_when_engine_unavailable_via_override(client):
    app.dependency_overrides[get_detection_pipeline] = lambda: FakePipeline(
        error=DetectionUnavailableError("Detection engine is unavailable.", details={"reason": "simulated"})
    )
    try:
        img = make_line_drawing()
        files = {"file": ("drawing.png", io.BytesIO(encode_png_bytes(img)), "image/png")}

        response = client.post("/api/v1/detect", files=files)

        assert response.status_code == 503
        assert response.json()["error"]["code"] == "DETECTION_UNAVAILABLE"
    finally:
        app.dependency_overrides.pop(get_detection_pipeline, None)


def test_detect_endpoint_returns_structured_error_with_real_pipeline_when_weights_missing(client):
    """No dependency override here - exercises the real DetectionPipeline
    and the real get_detection_engine(), which genuinely fails because no
    weights file is shipped in this repo. Confirms the app-wide behavior
    end-to-end: unavailable detection never crashes the request and
    never fabricates a result."""
    img = make_line_drawing()
    files = {"file": ("drawing.png", io.BytesIO(encode_png_bytes(img)), "image/png")}

    response = client.post("/api/v1/detect", files=files)

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "DETECTION_UNAVAILABLE"
