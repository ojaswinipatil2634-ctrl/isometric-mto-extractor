from app.services.business_rules.duplicate_detection import find_duplicate_fittings
from app.services.detection.pipeline import DetectionItemResult


def test_identical_bboxes_same_class_flagged_as_duplicate():
    detections = [
        DetectionItemResult("flange", 0.9, (100, 100, 150, 150)),
        DetectionItemResult("flange", 0.85, (101, 101, 151, 151)),
    ]

    violations = find_duplicate_fittings(detections)

    assert len(violations) == 1
    assert violations[0].class_name == "flange"
    assert violations[0].iou > 0.9


def test_different_classes_not_flagged_even_if_overlapping():
    detections = [
        DetectionItemResult("flange", 0.9, (100, 100, 150, 150)),
        DetectionItemResult("gate_valve", 0.9, (100, 100, 150, 150)),
    ]

    violations = find_duplicate_fittings(detections)

    assert violations == []


def test_low_overlap_not_flagged():
    detections = [
        DetectionItemResult("elbow", 0.9, (0, 0, 50, 50)),
        DetectionItemResult("elbow", 0.9, (45, 45, 95, 95)),
    ]

    violations = find_duplicate_fittings(detections, iou_threshold=0.5)

    assert violations == []


def test_no_overlap_not_flagged():
    detections = [
        DetectionItemResult("tee", 0.9, (0, 0, 50, 50)),
        DetectionItemResult("tee", 0.9, (500, 500, 550, 550)),
    ]

    violations = find_duplicate_fittings(detections)

    assert violations == []


def test_empty_detections_returns_empty():
    assert find_duplicate_fittings([]) == []


def test_single_detection_returns_empty():
    assert find_duplicate_fittings([DetectionItemResult("flange", 0.9, (0, 0, 10, 10))]) == []
