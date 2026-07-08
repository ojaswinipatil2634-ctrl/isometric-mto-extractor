"""
Duplicate fitting detection.

Flags pairs of Phase 4 detections of the SAME class whose bounding
boxes overlap heavily (high IoU) as likely duplicate detections of one
physical symbol - a common object-detector artifact (multiple anchors
firing on the same object) rather than two genuinely distinct fittings
drawn on top of each other.

Pure geometry (IoU) - no learned model, per project rules.
"""
from dataclasses import dataclass

from app.services.detection.pipeline import DetectionItemResult

DEFAULT_IOU_THRESHOLD = 0.5

BBox = tuple[float, float, float, float]


@dataclass
class DuplicateFittingViolation:
    class_name: str
    detection_indices: tuple[int, int]
    iou: float
    bbox_a: BBox
    bbox_b: BBox


def _iou(a: BBox, b: BBox) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b

    inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
    inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    if inter_area == 0.0:
        return 0.0

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter_area

    return inter_area / union if union > 0 else 0.0


def find_duplicate_fittings(
    detections: list[DetectionItemResult], iou_threshold: float = DEFAULT_IOU_THRESHOLD
) -> list[DuplicateFittingViolation]:
    violations: list[DuplicateFittingViolation] = []

    for i in range(len(detections)):
        for j in range(i + 1, len(detections)):
            a, b = detections[i], detections[j]
            if a.class_name != b.class_name:
                continue

            iou = _iou(a.bbox_xyxy, b.bbox_xyxy)
            if iou >= iou_threshold:
                violations.append(
                    DuplicateFittingViolation(
                        class_name=a.class_name,
                        detection_indices=(i, j),
                        iou=round(iou, 3),
                        bbox_a=a.bbox_xyxy,
                        bbox_b=b.bbox_xyxy,
                    )
                )

    return violations
