"""
Fixed class list for the Phase 4 piping-symbol/fitting detector.

This is the single source of truth for class id -> class name across the
detection engine, pipeline, and API schema. It must match the class order
the YOLOv11 weights were trained with (`data.yaml` `names:` list) exactly -
if the weights file's class count doesn't match `len(CLASS_NAMES)`, the
engine treats that as a configuration error rather than silently mapping
detections to the wrong labels.
"""

CLASS_NAMES: list[str] = [
    "elbow",
    "tee",
    "reducer",
    "gate_valve",
    "globe_valve",
    "check_valve",
    "flange",
    "support",
    "weld",
]

CLASS_ID_TO_NAME: dict[int, str] = {i: name for i, name in enumerate(CLASS_NAMES)}
