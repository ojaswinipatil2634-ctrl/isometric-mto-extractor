"""
Business rules pipeline orchestrator.

Chains: Phase 6 graph construction (nodes/edges/fitting associations) +
Phase 4 raw detections (for duplicate-fitting checking) + Phase 3 OCR
(best-effort NPS/material class for hardware sizing) -> connectivity
rule checks -> duplicate-fitting check -> hardware generation.

Detection and OCR are both treated as optional enrichment here, same
as Phase 6 treats detection: neither has real weights/model access
guaranteed in every environment, so their absence degrades specific
checks with a warning rather than failing the whole request. Gemini is
never used for any of this - see the project-wide rule that Gemini
only reviews, never extracts/generates/validates on its own.
"""
import logging
import re
import time
from dataclasses import dataclass, field

from app.core.errors import AppError
from app.services.business_rules.connectivity_rules import (
    RuleViolation,
    check_impossible_connections,
    check_invalid_reducers,
    check_missing_fittings,
    check_unterminated_pipes,
)
from app.services.business_rules.duplicate_detection import DuplicateFittingViolation, find_duplicate_fittings
from app.services.business_rules.hardware_generator import HardwareLineItem, generate_hardware_for_flanges
from app.services.detection.pipeline import DetectionPipeline
from app.services.graph_construction.pipeline import GraphConstructionPipeline
from app.services.ocr.pipeline import OcrPipeline

logger = logging.getLogger(__name__)

_NPS_NUMBER_RE = re.compile(r"(\d+(?:\.\d+)?)")
_CLASS_NUMBER_RE = re.compile(r"(\d{2,4})")


def _parse_nps(nps_value: str | None) -> float | None:
    if not nps_value:
        return None
    match = _NPS_NUMBER_RE.search(nps_value)
    return float(match.group(1)) if match else None


def _parse_rating_class(material_class_value: str | None) -> int | None:
    if not material_class_value:
        return None
    match = _CLASS_NUMBER_RE.search(material_class_value)
    return int(match.group(1)) if match else None


@dataclass
class BusinessRulesResult:
    hardware: list[HardwareLineItem] = field(default_factory=list)
    violations: list[RuleViolation] = field(default_factory=list)
    duplicate_fittings: list[DuplicateFittingViolation] = field(default_factory=list)
    steps_applied: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    processing_time_ms: float = 0.0


class BusinessRulesPipeline:
    def __init__(
        self,
        graph_pipeline: GraphConstructionPipeline | None = None,
        detection_pipeline: DetectionPipeline | None = None,
        ocr_pipeline: OcrPipeline | None = None,
    ) -> None:
        self._graph_pipeline = graph_pipeline or GraphConstructionPipeline()
        self._detection_pipeline = detection_pipeline or DetectionPipeline()
        self._ocr_pipeline = ocr_pipeline or OcrPipeline()

    def run(self, contents: bytes, content_type: str) -> BusinessRulesResult:
        start = time.perf_counter()
        steps: list[str] = []
        warnings: list[str] = []

        graph_result = self._graph_pipeline.run(contents, content_type)
        steps.append("graph_construction")
        warnings.extend(graph_result.warnings)

        violations: list[RuleViolation] = []
        violations.extend(
            check_missing_fittings(graph_result.analysis.branch_node_ids, graph_result.fitting_by_node)
        )
        violations.extend(
            check_unterminated_pipes(graph_result.analysis.dead_end_node_ids, graph_result.fitting_by_node)
        )
        violations.extend(check_invalid_reducers(graph_result.fitting_by_node, graph_result.node_degrees))
        violations.extend(check_impossible_connections(graph_result.edges, graph_result.fitting_by_node))
        steps.append("connectivity_rules")

        duplicate_fittings: list[DuplicateFittingViolation] = []
        try:
            detection_result = self._detection_pipeline.run(contents, content_type)
            duplicate_fittings = find_duplicate_fittings(detection_result.detections)
            steps.append("duplicate_detection")
        except AppError as exc:
            warnings.append(f"Duplicate-fitting check skipped - symbol detection unavailable ({exc.code}).")

        nps_inches: float | None = None
        rating_class: int | None = None
        try:
            ocr_result = self._ocr_pipeline.run(contents, content_type)
            fields = ocr_result.extracted_fields
            if fields is not None:
                if fields.nps:
                    nps_inches = _parse_nps(fields.nps[0].value)
                rating_class = _parse_rating_class(fields.material_class.value)
            steps.append("ocr_field_lookup")
        except AppError:
            # No warning here yet - if there turn out to be no flanges
            # at all, OCR being unavailable never mattered. The warning
            # below only fires when hardware was actually generated
            # using a non-exact (default) bolt spec.
            pass

        flange_node_ids = [
            node_id
            for node_id, fitting in graph_result.fitting_by_node.items()
            if fitting.class_name == "flange"
        ]
        hardware = generate_hardware_for_flanges(flange_node_ids, nps_inches, rating_class)
        steps.append("hardware_generation")

        if any(item.is_estimated for item in hardware):
            warnings.append(
                "Hardware bolt count/size could not be matched exactly to an NPS/rating class "
                "from OCR - using a conservative default; verify against ASME B16.5/B16.47 "
                "(or your governing piping spec) before procurement."
            )

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "Business rules complete in %.1fms: %d violation(s), %d duplicate(s), %d hardware item(s)",
            elapsed_ms, len(violations), len(duplicate_fittings), len(hardware),
        )

        return BusinessRulesResult(
            hardware=hardware,
            violations=violations,
            duplicate_fittings=duplicate_fittings,
            steps_applied=steps,
            warnings=warnings,
            processing_time_ms=round(elapsed_ms, 1),
        )
