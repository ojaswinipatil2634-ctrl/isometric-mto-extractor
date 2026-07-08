"""
Fitting association stage.

Best-effort enrichment: if Phase 4's symbol/fitting detector is
available and found anything, tag each graph node with the nearest
detected fitting class (elbow, tee, gate_valve, etc.) within
`max_distance_px` of the node's position. A node with no sufficiently
close detection is left untagged - this never guesses a fitting type
without a detection to back it up.
"""
import math
from dataclasses import dataclass

from app.services.detection.pipeline import DetectionItemResult
from app.services.graph_construction.node_builder import Point

DEFAULT_MAX_DISTANCE_PX = 40.0


@dataclass
class FittingMatch:
    class_name: str
    confidence: float
    distance_px: float


def _bbox_center(bbox_xyxy: tuple[float, float, float, float]) -> Point:
    x1, y1, x2, y2 = bbox_xyxy
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def associate_fittings(
    node_positions: dict[int, Point],
    detections: list[DetectionItemResult],
    max_distance_px: float = DEFAULT_MAX_DISTANCE_PX,
) -> dict[int, FittingMatch]:
    if not detections or not node_positions:
        return {}

    detection_centers = [(_bbox_center(d.bbox_xyxy), d) for d in detections]

    matches: dict[int, FittingMatch] = {}
    for node_id, node_point in node_positions.items():
        best_distance = math.inf
        best_detection = None
        for center, detection in detection_centers:
            distance = math.hypot(node_point[0] - center[0], node_point[1] - center[1])
            if distance < best_distance:
                best_distance = distance
                best_detection = detection

        if best_detection is not None and best_distance <= max_distance_px:
            matches[node_id] = FittingMatch(
                class_name=best_detection.class_name,
                confidence=best_detection.confidence,
                distance_px=round(best_distance, 2),
            )

    return matches
