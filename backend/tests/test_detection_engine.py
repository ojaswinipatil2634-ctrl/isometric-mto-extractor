"""
Tests that the app degrades cleanly when the YOLO detector can't run.

Deliberately NOT mocked for the "unavailable" paths: no weights file is
shipped in this repo, so `get_detection_engine()` hits a real missing-
weights condition, and this test environment also doesn't have
`ultralytics` installed. We assert the app turns both of those into a
clean `DetectionUnavailableError` / 503 response rather than crashing -
exactly the behavior Phase 4 requires ("If YOLO weights are unavailable,
return structured message. Do NOT fabricate detections.").
"""
import importlib.util

import pytest

from app.core.config import get_settings
from app.core.errors import DetectionUnavailableError
from app.services.detection import engine as detection_engine

_ULTRALYTICS_INSTALLED = importlib.util.find_spec("ultralytics") is not None


@pytest.fixture(autouse=True)
def _reset_engine_cache():
    detection_engine.reset_engine_cache_for_tests()
    yield
    detection_engine.reset_engine_cache_for_tests()


def test_get_detection_engine_raises_structured_error_when_weights_missing():
    settings = get_settings()
    # No weights file is shipped in this repo - the default path should
    # not exist in a clean checkout.
    assert not __import__("os").path.isfile(settings.YOLO_WEIGHTS_PATH)

    with pytest.raises(DetectionUnavailableError) as exc_info:
        detection_engine.get_detection_engine()

    assert exc_info.value.code == "DETECTION_UNAVAILABLE"
    assert exc_info.value.status_code == 503
    assert "weights" in exc_info.value.details["reason"].lower()


def test_get_detection_engine_caches_the_failure_instead_of_retrying_every_call():
    with pytest.raises(DetectionUnavailableError):
        detection_engine.get_detection_engine()

    # Second call should hit the cached failure reason, not attempt
    # another filesystem check / import.
    with pytest.raises(DetectionUnavailableError) as exc_info:
        detection_engine.get_detection_engine()
    assert exc_info.value.code == "DETECTION_UNAVAILABLE"


@pytest.mark.skipif(_ULTRALYTICS_INSTALLED, reason="ultralytics is installed in this environment")
def test_get_detection_engine_reports_missing_ultralytics_when_weights_exist(tmp_path, monkeypatch):
    """Distinguishes 'no weights file' from 'ultralytics not installed'
    by pointing YOLO_WEIGHTS_PATH at a file that does exist, then
    confirming the failure reason is about ultralytics, not about a
    missing file."""
    fake_weights = tmp_path / "fake_weights.pt"
    fake_weights.write_bytes(b"not a real checkpoint")

    class FakeSettings:
        YOLO_WEIGHTS_PATH = str(fake_weights)
        YOLO_DEVICE = "cpu"
        YOLO_CONFIDENCE_THRESHOLD = 0.25

    monkeypatch.setattr(detection_engine, "get_settings", lambda: FakeSettings())

    with pytest.raises(DetectionUnavailableError) as exc_info:
        detection_engine.get_detection_engine()

    assert exc_info.value.code == "DETECTION_UNAVAILABLE"
    assert "ultralytics" in exc_info.value.details["reason"].lower()


def test_detect_wraps_engine_runtime_errors():
    """The engine adapter itself must not let raw model exceptions
    escape as unhandled 500s - only DetectionUnavailableError."""

    class ExplodingModel:
        def predict(self, image, conf=0.25, verbose=False):
            raise RuntimeError("simulated model crash")

    wrapped = detection_engine.YoloDetectionEngine(ExplodingModel())

    with pytest.raises(DetectionUnavailableError) as exc_info:
        wrapped.detect(image="fake-image-array", confidence_threshold=0.25)

    assert exc_info.value.code == "DETECTION_UNAVAILABLE"
    assert "simulated model crash" in exc_info.value.details["reason"]


def test_detect_handles_no_objects_detected_without_raising():
    class EmptyBoxes:
        boxes = None

    class EmptyModel:
        def predict(self, image, conf=0.25, verbose=False):
            return [EmptyBoxes()]

    wrapped = detection_engine.YoloDetectionEngine(EmptyModel())

    detections = wrapped.detect(image="fake-image-array", confidence_threshold=0.25)

    assert detections == []


def test_detect_parses_ultralytics_results_shape():
    """Matches Ultralytics' `.predict()` return shape: a list of Results
    objects (one per input image), each with a `.boxes` iterable of
    box objects exposing `.cls`, `.conf`, `.xyxy` as 1-element tensors."""

    class FakeBox:
        def __init__(self, cls_id, confidence, xyxy):
            self.cls = [cls_id]
            self.conf = [confidence]
            self.xyxy = [xyxy]

    class FakeBoxes:
        def __init__(self, boxes):
            self._boxes = boxes

        def __iter__(self):
            return iter(self._boxes)

    class FakeResult:
        def __init__(self, boxes):
            self.boxes = FakeBoxes(boxes)

    class FakeModel:
        def predict(self, image, conf=0.25, verbose=False):
            return [
                FakeResult(
                    [
                        FakeBox(3, 0.91, (10.0, 20.0, 50.0, 60.0)),  # gate_valve
                        FakeBox(0, 0.77, (100.0, 120.0, 140.0, 160.0)),  # elbow
                    ]
                )
            ]

    wrapped = detection_engine.YoloDetectionEngine(FakeModel())

    detections = wrapped.detect(image="fake-image-array", confidence_threshold=0.25)

    assert len(detections) == 2
    assert detections[0].class_id == 3
    assert detections[0].confidence == pytest.approx(0.91)
    assert detections[0].bbox_xyxy == (10.0, 20.0, 50.0, 60.0)
    assert detections[1].class_id == 0
