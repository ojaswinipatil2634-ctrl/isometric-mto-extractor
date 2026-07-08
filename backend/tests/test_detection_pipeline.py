"""
Tests for `DetectionPipeline` (preprocessing -> detection -> structured
result), using a fake engine injected via `engine_factory=` so these
tests don't depend on ultralytics/torch being installed.
"""
from app.services.detection.engine import RawDetection
from app.services.detection.pipeline import DetectionPipeline
from tests.fixtures import encode_png_bytes, make_line_drawing


class FakeEngine:
    def __init__(self, detections: list[RawDetection]):
        self._detections = detections

    def detect(self, image, confidence_threshold: float) -> list[RawDetection]:
        return self._detections


def _run_pipeline_with_fake_detections(detections: list[RawDetection]):
    pipeline = DetectionPipeline(engine_factory=lambda: FakeEngine(detections))
    img = make_line_drawing()
    return pipeline.run(encode_png_bytes(img), "image/png")


def test_pipeline_maps_class_ids_to_names_and_counts_them():
    detections = [
        RawDetection(class_id=0, confidence=0.9, bbox_xyxy=(1, 2, 3, 4)),   # elbow
        RawDetection(class_id=0, confidence=0.8, bbox_xyxy=(5, 6, 7, 8)),   # elbow
        RawDetection(class_id=3, confidence=0.95, bbox_xyxy=(9, 10, 11, 12)),  # gate_valve
    ]

    result = _run_pipeline_with_fake_detections(detections)

    assert result.engine_available is True
    assert len(result.detections) == 3
    assert result.counts_by_class == {"elbow": 2, "gate_valve": 1}
    assert result.warnings == []


def test_pipeline_warns_when_nothing_detected():
    result = _run_pipeline_with_fake_detections([])

    assert result.detections == []
    assert result.counts_by_class == {}
    assert any("no symbols" in w.lower() for w in result.warnings)


def test_pipeline_ignores_and_warns_about_unrecognized_class_ids():
    detections = [
        RawDetection(class_id=0, confidence=0.9, bbox_xyxy=(1, 2, 3, 4)),
        RawDetection(class_id=999, confidence=0.5, bbox_xyxy=(1, 2, 3, 4)),
    ]

    result = _run_pipeline_with_fake_detections(detections)

    assert len(result.detections) == 1
    assert result.detections[0].class_name == "elbow"
    assert any("unrecognized class id" in w.lower() for w in result.warnings)


def test_pipeline_preserves_bounding_box_coordinates():
    detections = [RawDetection(class_id=6, confidence=0.6, bbox_xyxy=(11.5, 22.5, 33.5, 44.5))]

    result = _run_pipeline_with_fake_detections(detections)

    assert result.detections[0].class_name == "flange"
    assert result.detections[0].bbox_xyxy == (11.5, 22.5, 33.5, 44.5)
