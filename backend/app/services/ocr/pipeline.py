"""
OCR pipeline orchestrator.

Runs the Phase 2 preprocessing pipeline, feeds the result into the
PaddleOCR engine, converts raw OCR lines into structured TextBlocks, and
extracts title-block fields from them via pure regex rules
(field_extractor.py). Gemini is never involved here - see the
project-wide rule that Gemini only *reviews*, never *extracts*.
"""
import logging
import time
from dataclasses import dataclass, field

from app.services.ocr import field_extractor
from app.services.ocr.engine import OcrEngineProtocol, RawOcrLine, get_ocr_engine
from app.services.preprocessing.pipeline import PreprocessingPipeline

logger = logging.getLogger(__name__)


@dataclass
class TextBlockResult:
    text: str
    confidence: float
    bbox: list[list[float]]


@dataclass
class OcrResult:
    engine_available: bool
    text_blocks: list[TextBlockResult] = field(default_factory=list)
    extracted_fields: "field_extractor.ExtractedFields | None" = None
    average_confidence: float | None = None
    warnings: list[str] = field(default_factory=list)
    processing_time_ms: float = 0.0


class OcrPipeline:
    """
    Orchestrates preprocessing -> OCR -> field extraction.

    The OCR engine is resolved via `get_ocr_engine` at call time (not
    injected at construction), so `OcrUnavailableError` is raised fresh
    on every request rather than only at app startup - this matters
    because the very first call is what triggers PaddleOCR's lazy model
    download, and that's exactly the call most likely to fail on a
    machine with no internet access or missing weights.
    """

    def __init__(
        self,
        preprocessing_pipeline: PreprocessingPipeline | None = None,
        engine_factory=get_ocr_engine,
    ) -> None:
        self._preprocessing_pipeline = preprocessing_pipeline or PreprocessingPipeline()
        self._engine_factory = engine_factory

    def run(self, contents: bytes, content_type: str) -> OcrResult:
        start = time.perf_counter()

        preprocessed = self._preprocessing_pipeline.run(contents, content_type)
        # OCR reads text best off the contrast-enhanced preview rather
        # than the binarized output - adaptive thresholding can break
        # thin glyph strokes that OCR relies on for recognition.
        image_for_ocr = preprocessed.preview_image

        engine: OcrEngineProtocol = self._engine_factory()
        raw_lines: list[RawOcrLine] = engine.recognize(image_for_ocr)

        blocks = [
            TextBlockResult(text=line.text, confidence=line.confidence, bbox=line.bbox) for line in raw_lines
        ]

        extracted = field_extractor.extract_fields(blocks)

        confidences = [b.confidence for b in blocks]
        avg_conf = round(sum(confidences) / len(confidences), 4) if confidences else None

        warnings: list[str] = []
        if not blocks:
            warnings.append("No text was detected in the processed image.")

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "OCR pipeline complete in %.1fms: %d text block(s) detected, avg confidence=%s",
            elapsed_ms, len(blocks), avg_conf,
        )

        return OcrResult(
            engine_available=True,
            text_blocks=blocks,
            extracted_fields=extracted,
            average_confidence=avg_conf,
            warnings=warnings,
            processing_time_ms=round(elapsed_ms, 1),
        )
