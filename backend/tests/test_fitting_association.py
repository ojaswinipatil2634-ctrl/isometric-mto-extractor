from app.services.detection.pipeline import DetectionItemResult
from app.services.graph_construction.fitting_association import associate_fittings


def test_associates_nearest_fitting_within_range():
    node_positions = {0: (100.0, 100.0), 1: (500.0, 500.0)}
    detections = [
        DetectionItemResult(class_name="elbow", confidence=0.9, bbox_xyxy=(90, 90, 110, 110)),
    ]

    matches = associate_fittings(node_positions, detections, max_distance_px=40.0)

    assert 0 in matches
    assert matches[0].class_name == "elbow"
    assert 1 not in matches


def test_does_not_associate_fitting_outside_max_distance():
    node_positions = {0: (100.0, 100.0)}
    detections = [
        DetectionItemResult(class_name="tee", confidence=0.8, bbox_xyxy=(900, 900, 920, 920)),
    ]

    matches = associate_fittings(node_positions, detections, max_distance_px=40.0)

    assert matches == {}


def test_no_detections_returns_empty_without_fabricating():
    node_positions = {0: (100.0, 100.0)}

    matches = associate_fittings(node_positions, [], max_distance_px=40.0)

    assert matches == {}


def test_no_nodes_returns_empty():
    detections = [DetectionItemResult(class_name="flange", confidence=0.7, bbox_xyxy=(0, 0, 10, 10))]

    matches = associate_fittings({}, detections)

    assert matches == {}
