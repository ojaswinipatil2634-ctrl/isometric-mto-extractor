"""
Detection pipeline orchestrator.

Runs the Phase 2 preprocessing pipeline, feeds the result into the
YOLOv11 detection engine, and converts raw model output into structured
DetectionResults with human-readable class names. Gemini is never
involved here - see the project-wide rule that Gemini only *reviews*,
never *extracts*.
"""
import logging
import time
from collections import Counter
from dataclasses import dataclass, field

from app.core.config import get_settings
from app.services.detection.classes import CLASS_ID_TO_NAME
from app.services.detection.engine import DetectionEngineProtocol, RawDetection, get_detection_engine
from app.services.preprocessing.pipeline import PreprocessingPipeline

logger = logging.getLogger(__name__)


@dataclass
class DetectionItemResult:
    class_name: str
    confidence: float
    bbox_xyxy: tuple[float, float, float, float]


@dataclass
class DetectionResult:
    engine_available: bool
    detections: list[DetectionItemResult] = field(default_factory=list)
    counts_by_class: dict[str, int] = field(default_factory=dict)
    confidence_threshold: float = 0.0
    warnings: list[str] = field(default_factory=list)
    processing_time_ms: float = 0.0


class DetectionPipeline:
    """
    Orchestrates preprocessing -> YOLO symbol/fitting detection.

    The detection engine is resolved via `get_detection_engine` at call
    time (not injected at construction), so `DetectionUnavailableError`
    is raised fresh on every request rather than only at app startup -
    the weights file could be added/removed between requests without
    restarting the server.
    """

    def __init__(
        self,
        preprocessing_pipeline: PreprocessingPipeline | None = None,
        engine_factory=get_detection_engine,
    ) -> None:
        self._preprocessing_pipeline = preprocessing_pipeline or PreprocessingPipeline()
        self._engine_factory = engine_factory

    def run(self, contents: bytes, content_type: str) -> DetectionResult:
        start = time.perf_counter()
        settings = get_settings()
        confidence_threshold = settings.YOLO_CONFIDENCE_THRESHOLD

        preprocessed = self._preprocessing_pipeline.run(contents, content_type)
        # Detect against the contrast-enhanced preview (same coordinate
        # space OCR runs against, see ocr/pipeline.py) rather than the
        # binarized output - thresholding can erase the fill/line-weight
        # cues the detector relies on to tell fittings apart.
        image_for_detection = preprocessed.preview_image

        engine: DetectionEngineProtocol = self._engine_factory()
        raw_detections: list[RawDetection] = engine.detect(image_for_detection, confidence_threshold)

        items: list[DetectionItemResult] = []
        unknown_class_ids: set[int] = set()
        for raw in raw_detections:
            class_name = CLASS_ID_TO_NAME.get(raw.class_id)
            if class_name is None:
                # Defensive only - get_detection_engine() already refuses
                # to load a model whose class count doesn't match ours,
                # so this should be unreachable in practice.
                unknown_class_ids.add(raw.class_id)
                continue
            items.append(
                DetectionItemResult(class_name=class_name, confidence=raw.confidence, bbox_xyxy=raw.bbox_xyxy)
            )

        counts_by_class = dict(Counter(item.class_name for item in items))

        warnings: list[str] = []
        if not items:
            warnings.append("No symbols or fittings were detected in the processed image.")
        if unknown_class_ids:
            warnings.append(
                f"Ignored {len(unknown_class_ids)} detection(s) with unrecognized class id(s): "
                f"{sorted(unknown_class_ids)}."
            )

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "Detection pipeline complete in %.1fms: %d object(s) detected (threshold=%.2f)",
            elapsed_ms, len(items), confidence_threshold,
        )

        return DetectionResult(
            engine_available=True,
            detections=items,
            counts_by_class=counts_by_class,
            confidence_threshold=confidence_threshold,
            warnings=warnings,
            processing_time_ms=round(elapsed_ms, 1),
        )
