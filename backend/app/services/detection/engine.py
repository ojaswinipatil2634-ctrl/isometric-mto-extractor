"""
YOLOv11 (Ultralytics) symbol/fitting detection engine wrapper.

`ultralytics` is a heavy dependency (pulls in torch), and the trained
weights file is a project-specific artifact that isn't shipped in this
repo. Per project rules, if detection is unavailable for *any* reason -
ultralytics not installed, weights file missing, model fails to load,
inference fails on a given image - we must return a structured error
and never fabricate a detection result.

To make that possible, this module is the *only* place in the app that
ever imports `ultralytics`, and it does so lazily (inside a function,
not at module import time). That means:

    - the rest of the app can import this module freely without paying
      the cost of loading torch/ultralytics until detection is actually
      used
    - a missing weights file is checked *before* attempting to import
      ultralytics at all, so "no weights" and "ultralytics not
      installed" are reported as distinct, honest reasons instead of
      being conflated
    - the failure (whichever kind) is cached, so repeated requests
      don't keep retrying a slow, doomed initialization on every call
"""
import logging
import os
import threading
from typing import Protocol

from app.core.config import get_settings
from app.core.errors import DetectionUnavailableError
from app.services.detection.classes import CLASS_NAMES

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_engine_instance: "YoloDetectionEngine | None" = None
_engine_init_failed_reason: str | None = None


class RawDetection:
    """One raw detection in the underlying model's native class-id space."""

    __slots__ = ("class_id", "confidence", "bbox_xyxy")

    def __init__(self, class_id: int, confidence: float, bbox_xyxy: tuple[float, float, float, float]) -> None:
        self.class_id = class_id
        self.confidence = confidence
        self.bbox_xyxy = bbox_xyxy

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"RawDetection(class_id={self.class_id}, confidence={self.confidence:.3f})"


class DetectionEngineProtocol(Protocol):
    """Interface the rest of the app depends on, so tests can substitute
    a fake engine without touching real Ultralytics/torch."""

    def detect(self, image, confidence_threshold: float) -> list[RawDetection]: ...


class YoloDetectionEngine:
    """Thin adapter around an Ultralytics `YOLO` model's `.predict()` call."""

    def __init__(self, model) -> None:
        self._model = model

    def detect(self, image, confidence_threshold: float) -> list[RawDetection]:
        """
        image: BGR numpy array (as produced by the preprocessing pipeline).
        Returns one RawDetection per detected object at or above
        confidence_threshold.

        Raises:
            DetectionUnavailableError: if the underlying model raises
                while processing this specific image (corrupt state, out
                of memory, etc). This is deliberately a *different*
                error path than initialization failure, but the same
                error type, since both mean "no result is available" and
                neither should be papered over with a fabricated one.
        """
        try:
            results = self._model.predict(image, conf=confidence_threshold, verbose=False)
        except Exception as exc:
            raise DetectionUnavailableError(
                "YOLO detector failed while processing the image.",
                details={"reason": str(exc)},
            ) from exc

        detections: list[RawDetection] = []
        if not results:
            return detections

        # Ultralytics returns one Results object per input image; we only
        # ever pass a single image, so we only look at results[0].
        boxes = results[0].boxes
        if boxes is None:
            return detections

        for box in boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            x1, y1, x2, y2 = (float(v) for v in box.xyxy[0])
            detections.append(RawDetection(class_id=class_id, confidence=confidence, bbox_xyxy=(x1, y1, x2, y2)))
        return detections


def get_detection_engine() -> "YoloDetectionEngine":
    """
    Lazily builds and caches a single YOLO model instance for the process.

    Raises:
        DetectionUnavailableError: if the weights file is missing,
            ultralytics is not installed, or the model fails to load.
            Never fabricates a result; the caller is expected to surface
            this as a clean 503.
    """
    global _engine_instance, _engine_init_failed_reason

    if _engine_instance is not None:
        return _engine_instance

    if _engine_init_failed_reason is not None:
        raise DetectionUnavailableError(
            "Detection engine is unavailable.", details={"reason": _engine_init_failed_reason}
        )

    with _lock:
        # Re-check inside the lock - another thread may have already
        # initialized (or failed to initialize) the engine while we
        # were waiting for it.
        if _engine_instance is not None:
            return _engine_instance
        if _engine_init_failed_reason is not None:
            raise DetectionUnavailableError(
                "Detection engine is unavailable.", details={"reason": _engine_init_failed_reason}
            )

        settings = get_settings()

        # Check the weights file *before* importing ultralytics, so a
        # missing-weights message is never mistaken for a broken install.
        if not os.path.isfile(settings.YOLO_WEIGHTS_PATH):
            _engine_init_failed_reason = (
                f"YOLO weights file not found at '{settings.YOLO_WEIGHTS_PATH}'. "
                "Train or place a weights file at this path (see YOLO_WEIGHTS_PATH in .env)."
            )
            logger.error("Detection engine unavailable: %s", _engine_init_failed_reason)
            raise DetectionUnavailableError(
                "Detection engine is unavailable.", details={"reason": _engine_init_failed_reason}
            )

        try:
            from ultralytics import YOLO  # deferred import - see module docstring
        except Exception as exc:
            _engine_init_failed_reason = (
                f"ultralytics is not installed or failed to import ({type(exc).__name__}: {exc})"
            )
            logger.error("Detection engine unavailable: %s", _engine_init_failed_reason)
            raise DetectionUnavailableError(
                "Detection engine is unavailable.", details={"reason": _engine_init_failed_reason}
            ) from exc

        try:
            model = YOLO(settings.YOLO_WEIGHTS_PATH)
            model.to(settings.YOLO_DEVICE)
        except Exception as exc:
            _engine_init_failed_reason = f"YOLO model failed to load ({type(exc).__name__}: {exc})"
            logger.error("Detection engine unavailable: %s", _engine_init_failed_reason)
            raise DetectionUnavailableError(
                "Detection engine is unavailable.", details={"reason": _engine_init_failed_reason}
            ) from exc

        model_class_count = len(getattr(model, "names", {}) or {})
        if model_class_count != len(CLASS_NAMES):
            _engine_init_failed_reason = (
                f"Weights file class count ({model_class_count}) does not match the "
                f"expected {len(CLASS_NAMES)} piping symbol classes. Refusing to use "
                "this model to avoid mislabeled detections."
            )
            logger.error("Detection engine unavailable: %s", _engine_init_failed_reason)
            raise DetectionUnavailableError(
                "Detection engine is unavailable.", details={"reason": _engine_init_failed_reason}
            )

        _engine_instance = YoloDetectionEngine(model)
        logger.info(
            "YOLO detection engine initialized (weights=%s, device=%s, classes=%d)",
            settings.YOLO_WEIGHTS_PATH, settings.YOLO_DEVICE, model_class_count,
        )
        return _engine_instance


def reset_engine_cache_for_tests() -> None:
    """Test-only helper: clears the cached engine/failure so each test
    can exercise initialization behavior independently."""
    global _engine_instance, _engine_init_failed_reason
    with _lock:
        _engine_instance = None
        _engine_init_failed_reason = None
