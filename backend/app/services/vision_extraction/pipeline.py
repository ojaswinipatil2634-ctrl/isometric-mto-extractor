"""
Vision extraction pipeline orchestrator.

This is the actual "drawing in, MTO out" path from the take-home spec
(section 3.3), added because the pre-existing Phase 4-8 stack can
never produce PIPE/FITTING/FLANGE/VALVE rows on a fresh checkout (see
schemas/vision_extraction.py docstring for the full root-cause
explanation).

Flow: reuse Phase 2 preprocessing to get a clean PNG -> call Gemini
with the extraction prompt -> on any failure (no key, network error,
invalid JSON/schema) fall back to the deterministic mock extraction ->
derive the final MTO item rows (pipe grouped by NPS, fittings/flanges/
valves by count, gasket/bolt-set rows per flanged joint).

Per the spec's graceful-degradation requirement, `run()` never raises
and `items` is never empty just because Gemini isn't configured -
`used_mock` / `extraction_source` tell the caller (and the exported
CSV/JSON) which path actually produced the data.
"""
import logging
import time
from dataclasses import dataclass, field

import cv2

from app.schemas.vision_extraction import VisionDrawingMetadata, VisionMTOItem
from app.services.preprocessing.pipeline import PreprocessingPipeline
from app.services.vision_extraction.client import GeminiExtractionClient
from app.services.vision_extraction.derive import build_mto_items
from app.services.vision_extraction.mock import mock_extraction

logger = logging.getLogger(__name__)


@dataclass
class VisionExtractionResult:
    metadata: VisionDrawingMetadata = field(default_factory=VisionDrawingMetadata)
    items: list[VisionMTOItem] = field(default_factory=list)
    extraction_source: str = "mock"  # "gemini" | "mock"
    used_mock: bool = True
    overall_confidence: float = 0.5
    warnings: list[str] = field(default_factory=list)
    processing_time_ms: float = 0.0


class VisionExtractionPipeline:
    def __init__(
        self,
        preprocessing_pipeline: PreprocessingPipeline | None = None,
        gemini_client: GeminiExtractionClient | None = None,
    ) -> None:
        self._preprocessing_pipeline = preprocessing_pipeline or PreprocessingPipeline()
        self._gemini_client = gemini_client or GeminiExtractionClient()

    def run(self, contents: bytes, content_type: str, filename: str) -> VisionExtractionResult:
        start = time.perf_counter()
        warnings: list[str] = []

        raw = None
        source = "mock"

        if self._gemini_client.is_configured:
            try:
                preprocessed = self._preprocessing_pipeline.run(contents, content_type)
                success, png_buffer = cv2.imencode(".png", preprocessed.preview_image)
                if success:
                    raw, error = self._gemini_client.extract(png_buffer.tobytes())
                    if raw is not None:
                        source = "gemini"
                    else:
                        warnings.append(f"Gemini extraction failed, using mock MTO instead: {error}")
                else:
                    warnings.append("Could not re-encode the drawing as PNG for Gemini; using mock MTO instead.")
            except Exception as exc:  # pragma: no cover - defensive: preprocessing must never block fallback
                warnings.append(f"Preprocessing before Gemini call failed, using mock MTO instead: {exc}")
        else:
            warnings.append("GEMINI_API_KEY is not configured - returning a clearly-labelled mock MTO.")

        if raw is None:
            raw = mock_extraction(filename)
            source = "mock"

        items = build_mto_items(raw)

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "Vision extraction complete in %.1fms: source=%s, %d item(s)",
            elapsed_ms, source, len(items),
        )

        return VisionExtractionResult(
            metadata=raw.metadata,
            items=items,
            extraction_source=source,
            used_mock=(source == "mock"),
            overall_confidence=raw.overall_confidence,
            warnings=warnings,
            processing_time_ms=round(elapsed_ms, 1),
        )
