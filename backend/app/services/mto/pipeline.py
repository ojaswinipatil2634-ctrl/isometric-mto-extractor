"""
Full MTO extraction pipeline orchestrator - Phase 8.

Combines Phase 3 OCR (title-block fields), Phase 6 graph construction
(topology summary), and Phase 7 business rules (hardware + violations)
into one result shaped for persistence. Nothing new is extracted here -
this phase is composition + persistence + export over what earlier
phases already produce. Gemini is never used - see the project-wide
rule that Gemini only reviews, never extracts.

Each sub-pipeline still runs its own preprocessing internally (the same
tradeoff already accepted in Phase 6/7 - independently composable
pipelines over re-running a shared cache), so this endpoint is the
heaviest one in the API, but it produces the single persisted record
`/mto/history` and `/mto/{id}` serve back without re-running anything.
"""
import logging
import time
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field
from typing import Callable, TypeVar

from app.core.errors import AppError
from app.schemas.vision_extraction import VisionMTOItem
from app.services.business_rules.pipeline import BusinessRulesPipeline, BusinessRulesResult
from app.services.detection.engine import get_detection_engine
from app.services.graph_construction.pipeline import GraphConstructionPipeline, GraphConstructionResult
from app.services.ocr.pipeline import OcrPipeline
from app.services.preprocessing.pipeline import PreprocessingPipeline
from app.services.vision_extraction.pipeline import VisionExtractionPipeline

logger = logging.getLogger(__name__)

T = TypeVar("T")

# The OCR/graph/business-rules layers are classical-CV, best-effort,
# supplementary structural analysis (see MTOExtractionResult docstring
# below) - the take-home spec's primary deliverable, the MTO item list,
# comes entirely from vision_extraction and never touches these. On a
# dense hand-marked drawing (heavy grid background, hundreds of
# annotation circles), Hough transform/skeletonize can pathologically
# hang for minutes rather than erroring out - which is worse than a
# clean failure, since it blocks the whole request. A dedicated
# executor with a hard wall-clock timeout ensures a slow/pathological
# image degrades this bonus layer instead of hanging the endpoint.
# Threads that exceed the timeout are abandoned (Python can't kill a
# running thread) but no longer block the response.
_BONUS_STAGE_TIMEOUT_SECONDS = 8.0
# OCR, graph construction, and business rules (which internally runs
# its own OCR *and* graph construction) all depend on the same
# preprocessing chain, and app/services/preprocessing/pipeline.py now
# caches it by content hash - but only *after* some call runs it to
# completion. If the first stage to touch it (OCR) gets cut off by its
# own 8s budget before that ~20-30s chain finishes on a large/dense
# scan, the cache is never warmed, and every later stage independently
# repeats the same doomed cold attempt. Pre-warming once upfront, with
# its own more realistic budget, avoids that: either every downstream
# stage gets a cache hit and can focus its own 8s budget on its actual
# work, or preprocessing itself is genuinely too slow for this input,
# in which case there is no point even trying OCR/graph/business rules
# and we say so once instead of three separate times.
_PREPROCESS_TIMEOUT_SECONDS = 30.0
_bonus_stage_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="mto-bonus-stage")


def _run_with_timeout(
    fn: Callable[[], T], stage_name: str, timeout_seconds: float = _BONUS_STAGE_TIMEOUT_SECONDS
) -> tuple[T | None, str | None]:
    """Runs `fn` with a hard wall-clock timeout.

    Returns (result, error). `result` is None and `error` describes what
    went wrong if `fn` raised, or if it didn't finish within
    `timeout_seconds`. Never raises.
    """
    future: Future = _bonus_stage_executor.submit(fn)
    try:
        return future.result(timeout=timeout_seconds), None
    except FutureTimeoutError:
        reason = (
            f"{stage_name} did not finish within {timeout_seconds:.0f}s "
            "(likely a dense/hand-marked drawing) - skipped for this run."
        )
        logger.warning(reason)
        return None, reason
    except AppError as exc:
        reason = exc.details.get("reason") if exc.details else None
        reason = reason or exc.message
        return None, f"{stage_name} unavailable ({exc.code}): {reason}"
    except Exception as exc:  # pragma: no cover - defensive catch-all
        return None, f"{stage_name} failed unexpectedly: {exc}"


def _summarize_items(items: list[VisionMTOItem]) -> dict:
    """Spec section 3.4 summary block, computed from the actual MTO items."""
    summary = {
        "total_pipe_length_m": 0.0,
        "fittings": 0,
        "flanges": 0,
        "valves": 0,
        "gaskets": 0,
        "bolt_sets": 0,
    }
    for item in items:
        if item.category == "PIPE":
            summary["total_pipe_length_m"] += item.length_m or 0.0
        elif item.category == "FITTING":
            summary["fittings"] += int(item.quantity)
        elif item.category == "FLANGE":
            summary["flanges"] += int(item.quantity)
        elif item.category == "VALVE":
            summary["valves"] += int(item.quantity)
        elif item.category == "GASKET":
            summary["gaskets"] += int(item.quantity)
        elif item.category == "BOLT":
            summary["bolt_sets"] += int(item.quantity)
    summary["total_pipe_length_m"] = round(summary["total_pipe_length_m"], 2)
    return summary


@dataclass
class MTOExtractionResult:
    drawing_number: str | None = None
    revision: str | None = None
    line_number: str | None = None
    service: str | None = None
    material_class: str | None = None
    nps_values: list[str] = field(default_factory=list)

    # The actual MTO line items (PIPE/FITTING/FLANGE/VALVE/GASKET/BOLT) -
    # see app/services/vision_extraction/. This is the primary deliverable;
    # everything below is supplementary structural analysis from the
    # Phase 6/7 CV/graph stack (bonus signal, not required for a usable MTO).
    items: list[VisionMTOItem] = field(default_factory=list)
    mto_summary: dict = field(default_factory=dict)
    extraction_source: str = "mock"  # "gemini" | "mock"
    used_mock: bool = True

    node_count: int = 0
    edge_count: int = 0
    branch_count: int = 0
    dead_end_count: int = 0
    loop_count: int = 0
    is_fully_connected: bool = True

    business_rules: BusinessRulesResult = field(default_factory=BusinessRulesResult)

    # Informational only - see _check_symbol_detection_availability(). The
    # rest of the pipeline never branches on this; graph/business-rules
    # already degrade internally (see their own AppError handling) whether
    # or not this flag is true.
    symbol_detection_enabled: bool = False
    symbol_detection_reason: str | None = None

    warnings: list[str] = field(default_factory=list)
    processing_time_ms: float = 0.0


class MTOExtractionPipeline:
    def __init__(
        self,
        ocr_pipeline: OcrPipeline | None = None,
        graph_pipeline: GraphConstructionPipeline | None = None,
        business_rules_pipeline: BusinessRulesPipeline | None = None,
        vision_pipeline: VisionExtractionPipeline | None = None,
    ) -> None:
        self._ocr_pipeline = ocr_pipeline or OcrPipeline()
        self._graph_pipeline = graph_pipeline or GraphConstructionPipeline()
        self._business_rules_pipeline = business_rules_pipeline or BusinessRulesPipeline()
        self._vision_pipeline = vision_pipeline or VisionExtractionPipeline()

    @staticmethod
    def _check_symbol_detection_availability() -> tuple[bool, str | None]:
        """
        Reports whether the YOLO symbol detector is available, purely as
        informational metadata for the response - never as a gate on the
        rest of the pipeline. `graph_construction` and `business_rules`
        already call the detection pipeline themselves and each already
        catches `AppError` internally to degrade gracefully (built from
        pipe geometry / OCR alone) when it isn't, so this check doesn't
        change what runs; it only surfaces *why* detection didn't
        contribute, for the UI and for anyone auditing a run later.

        `get_detection_engine()` is cheap to call here even when the
        engine is already loaded (or already known to be unavailable):
        both outcomes are cached at the module level in
        app.services.detection.engine, so this never re-triggers model
        loading work that graph/business-rules didn't already trigger.
        """
        try:
            get_detection_engine()
            return True, None
        except AppError as exc:
            reason = exc.details.get("reason") if exc.details else None
            reason = reason or exc.message
            logger.warning(
                "YOLO weights not found or symbol detector unavailable (%s). "
                "Continuing with OCR/graph-based extraction only - symbol detection skipped.",
                reason,
            )
            return False, reason

    def run(self, contents: bytes, content_type: str, filename: str = "unknown") -> MTOExtractionResult:
        start = time.perf_counter()
        warnings: list[str] = []

        symbol_detection_enabled, symbol_detection_reason = self._check_symbol_detection_availability()

        # Pre-warm the shared preprocessing cache (see the comment on
        # _PREPROCESS_TIMEOUT_SECONDS above) so OCR/graph/business-rules
        # below each get a cache hit instead of independently repeating
        # the same doomed cold computation.
        _, preprocess_error = _run_with_timeout(
            lambda: PreprocessingPipeline().run(contents, content_type),
            "Preprocessing",
            timeout_seconds=_PREPROCESS_TIMEOUT_SECONDS,
        )
        bonus_stages_available = preprocess_error is None
        if not bonus_stages_available:
            warnings.append(
                f"{preprocess_error} Title-block OCR, pipe-topology, and business-rule "
                "checks were all skipped for this run as a result; the primary MTO items "
                "below (from Gemini) are unaffected."
            )

        drawing_number = revision = line_number = service = material_class = None
        nps_values: list[str] = []
        ocr_result = ocr_error = None
        if bonus_stages_available:
            ocr_result, ocr_error = _run_with_timeout(
                lambda: self._ocr_pipeline.run(contents, content_type), "OCR"
            )
        if ocr_result is not None:
            fields = ocr_result.extracted_fields
            if fields is not None:
                drawing_number = fields.drawing_number.value
                revision = fields.revision.value
                line_number = fields.line_number.value
                service = fields.service.value
                material_class = fields.material_class.value
                nps_values = [f.value for f in fields.nps if f.value]
            warnings.extend(ocr_result.warnings)
        elif ocr_error:
            warnings.append(f"Title-block fields unavailable - {ocr_error}")

        # Primary MTO item extraction (pipe/fitting/flange/valve/gasket/bolt).
        # See app/services/vision_extraction/ - this is what actually
        # populates the exported CSV/JSON/Excel now. OCR fields above are
        # kept as the preferred metadata source when available (real
        # title-block reading); vision metadata only fills in gaps.
        vision_result = self._vision_pipeline.run(contents, content_type, filename)
        warnings.extend(w for w in vision_result.warnings if w not in warnings)
        drawing_number = drawing_number or vision_result.metadata.drawing_number
        revision = revision or vision_result.metadata.revision
        line_number = line_number or vision_result.metadata.line_number
        service = service or vision_result.metadata.service
        material_class = material_class or vision_result.metadata.material_class
        if not nps_values and vision_result.metadata.nps:
            nps_values = [vision_result.metadata.nps]

        graph_result = graph_error = None
        if bonus_stages_available:
            graph_result, graph_error = _run_with_timeout(
                lambda: self._graph_pipeline.run(contents, content_type), "Graph construction"
            )
        if graph_result is None:
            graph_result = GraphConstructionResult()
            if graph_error:
                warnings.append(graph_error)
        warnings.extend(w for w in graph_result.warnings if w not in warnings)

        business_rules_result = business_rules_error = None
        if bonus_stages_available:
            business_rules_result, business_rules_error = _run_with_timeout(
                lambda: self._business_rules_pipeline.run(contents, content_type), "Business rules"
            )
        if business_rules_result is None:
            business_rules_result = BusinessRulesResult()
            if business_rules_error:
                warnings.append(business_rules_error)
        warnings.extend(w for w in business_rules_result.warnings if w not in warnings)

        elapsed_ms = (time.perf_counter() - start) * 1000

        result = MTOExtractionResult(
            drawing_number=drawing_number,
            revision=revision,
            line_number=line_number,
            service=service,
            material_class=material_class,
            nps_values=nps_values,
            items=vision_result.items,
            mto_summary=_summarize_items(vision_result.items),
            extraction_source=vision_result.extraction_source,
            used_mock=vision_result.used_mock,
            node_count=len(graph_result.node_positions),
            edge_count=len(graph_result.edges),
            branch_count=len(graph_result.analysis.branch_node_ids),
            dead_end_count=len(graph_result.analysis.dead_end_node_ids),
            loop_count=len(graph_result.analysis.loops),
            is_fully_connected=graph_result.analysis.is_fully_connected,
            business_rules=business_rules_result,
            symbol_detection_enabled=symbol_detection_enabled,
            symbol_detection_reason=symbol_detection_reason,
            warnings=warnings,
            processing_time_ms=round(elapsed_ms, 1),
        )

        logger.info(
            "MTO extraction complete in %.1fms: drawing_number=%s, source=%s, %d item(s), "
            "%d hardware item(s), %d violation(s)",
            result.processing_time_ms, drawing_number, vision_result.extraction_source,
            len(vision_result.items), len(business_rules_result.hardware), len(business_rules_result.violations),
        )
        return result
