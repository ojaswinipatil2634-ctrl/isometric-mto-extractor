"""
Gemini verification pipeline orchestrator - Phase 9.

Builds a review context from Phase 3 OCR + Phase 4 detection + Phase 6
graph + Phase 7 business rules (each best-effort, same graceful-
degradation pattern already used in Phase 6/7/8), converts the drawing
to a plain PNG via Phase 2 preprocessing, and asks Gemini to review it -
never extract. If GEMINI_API_KEY isn't configured, or the request fails
for any reason, this returns `available=False` with a warning - never a
crash, never a fabricated review, per the project-wide Gemini rule and
this phase's specific "skip cleanly if no API key" requirement.
"""
import logging
import time
from dataclasses import dataclass, field

import cv2

from app.core.errors import AppError
from app.services.business_rules.pipeline import BusinessRulesPipeline
from app.services.detection.pipeline import DetectionPipeline
from app.services.gemini_verification.client import GeminiVerificationClient
from app.services.graph_construction.pipeline import GraphConstructionPipeline
from app.services.ocr.pipeline import OcrPipeline
from app.services.preprocessing.pipeline import PreprocessingPipeline

logger = logging.getLogger(__name__)


@dataclass
class GeminiVerificationResult:
    available: bool = False
    corrections: list[str] = field(default_factory=list)
    missing_items: list[str] = field(default_factory=list)
    ocr_flags: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    processing_time_ms: float = 0.0


class GeminiVerificationPipeline:
    def __init__(
        self,
        preprocessing_pipeline: PreprocessingPipeline | None = None,
        ocr_pipeline: OcrPipeline | None = None,
        detection_pipeline: DetectionPipeline | None = None,
        graph_pipeline: GraphConstructionPipeline | None = None,
        business_rules_pipeline: BusinessRulesPipeline | None = None,
        gemini_client: GeminiVerificationClient | None = None,
    ) -> None:
        self._preprocessing_pipeline = preprocessing_pipeline or PreprocessingPipeline()
        self._ocr_pipeline = ocr_pipeline or OcrPipeline()
        self._detection_pipeline = detection_pipeline or DetectionPipeline()
        self._graph_pipeline = graph_pipeline or GraphConstructionPipeline()
        self._business_rules_pipeline = business_rules_pipeline or BusinessRulesPipeline()
        self._gemini_client = gemini_client or GeminiVerificationClient()

    def run(self, contents: bytes, content_type: str) -> GeminiVerificationResult:
        start = time.perf_counter()

        # Fail fast and cheap: if there's no API key, skip before running
        # any of the (comparatively expensive) upstream pipelines at all.
        if not self._gemini_client.is_configured:
            return GeminiVerificationResult(
                available=False,
                warnings=["Gemini verification skipped - GEMINI_API_KEY is not configured."],
                processing_time_ms=round((time.perf_counter() - start) * 1000, 1),
            )

        warnings: list[str] = []

        preprocessed = self._preprocessing_pipeline.run(contents, content_type)
        success, png_buffer = cv2.imencode(".png", preprocessed.preview_image)
        image_bytes = png_buffer.tobytes() if success else b""
        if not success:
            warnings.append("Could not re-encode the drawing as PNG for Gemini review.")

        context: dict = {}

        try:
            ocr_result = self._ocr_pipeline.run(contents, content_type)
            fields = ocr_result.extracted_fields
            context["ocr_fields"] = (
                {
                    "drawing_number": fields.drawing_number.value,
                    "revision": fields.revision.value,
                    "line_number": fields.line_number.value,
                    "service": fields.service.value,
                    "material_class": fields.material_class.value,
                    "nps": [f.value for f in fields.nps if f.value],
                }
                if fields is not None
                else None
            )
        except AppError as exc:
            context["ocr_fields"] = None
            warnings.append(f"OCR context unavailable for Gemini review ({exc.code}).")

        try:
            detection_result = self._detection_pipeline.run(contents, content_type)
            context["detections"] = detection_result.counts_by_class
        except AppError as exc:
            context["detections"] = None
            warnings.append(f"Detection context unavailable for Gemini review ({exc.code}).")

        graph_result = self._graph_pipeline.run(contents, content_type)
        context["graph_summary"] = {
            "node_count": len(graph_result.node_positions),
            "edge_count": len(graph_result.edges),
            "branch_count": len(graph_result.analysis.branch_node_ids),
            "dead_end_count": len(graph_result.analysis.dead_end_node_ids),
            "loop_count": len(graph_result.analysis.loops),
            "is_fully_connected": graph_result.analysis.is_fully_connected,
        }

        business_rules_result = self._business_rules_pipeline.run(contents, content_type)
        context["business_rules_summary"] = {
            "hardware_count": len(business_rules_result.hardware),
            "violation_count": len(business_rules_result.violations),
            "violations": [
                {"rule_code": v.rule_code, "message": v.message} for v in business_rules_result.violations
            ],
        }

        review = self._gemini_client.review(image_bytes, context)
        if not review.available:
            warnings.append(f"Gemini verification unavailable: {review.error}")

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "Gemini verification complete in %.1fms: available=%s, %d correction(s), "
            "%d missing item(s), %d OCR flag(s)",
            elapsed_ms, review.available, len(review.corrections), len(review.missing_items),
            len(review.ocr_flags),
        )

        return GeminiVerificationResult(
            available=review.available,
            corrections=review.corrections,
            missing_items=review.missing_items,
            ocr_flags=review.ocr_flags,
            warnings=warnings,
            processing_time_ms=round(elapsed_ms, 1),
        )
