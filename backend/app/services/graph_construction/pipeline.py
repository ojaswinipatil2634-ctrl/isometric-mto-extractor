"""
Graph construction pipeline orchestrator.

Chains: Phase 5 pipe extraction -> node snapping -> NetworkX graph
build -> (best-effort) Phase 4 fitting association -> structural
analysis (branches, dead ends, loops, connectivity).

Symbol detection is treated as optional enrichment, not a hard
dependency: Phase 4 requires a trained YOLOv11 weights file that isn't
shipped in this repo, so DetectionUnavailableError is expected in a
fresh checkout. When that happens, the graph is still built from pipe
geometry alone and a warning is attached - this phase never fails just
because Phase 4 isn't configured yet.
"""
import logging
import time
from dataclasses import dataclass, field

from app.core.errors import AppError
from app.services.detection.pipeline import DetectionItemResult, DetectionPipeline
from app.services.graph_construction.analysis import GraphAnalysis, analyze
from app.services.graph_construction.branch_splitting import split_segments_at_branch_points
from app.services.graph_construction.fitting_association import FittingMatch, associate_fittings
from app.services.graph_construction.graph_builder import build_graph
from app.services.graph_construction.node_builder import Point, build_nodes
from app.services.pipe_extraction.pipeline import PipeExtractionPipeline

logger = logging.getLogger(__name__)


@dataclass
class GraphConstructionResult:
    node_positions: dict[int, Point] = field(default_factory=dict)
    node_degrees: dict[int, int] = field(default_factory=dict)
    fitting_by_node: dict[int, FittingMatch] = field(default_factory=dict)
    edges: list[tuple[int, int, dict]] = field(default_factory=list)
    analysis: GraphAnalysis = field(default_factory=GraphAnalysis)
    steps_applied: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    processing_time_ms: float = 0.0


class GraphConstructionPipeline:
    def __init__(
        self,
        pipe_extraction_pipeline: PipeExtractionPipeline | None = None,
        detection_pipeline: DetectionPipeline | None = None,
    ) -> None:
        self._pipe_extraction_pipeline = pipe_extraction_pipeline or PipeExtractionPipeline()
        self._detection_pipeline = detection_pipeline or DetectionPipeline()

    def run(self, contents: bytes, content_type: str) -> GraphConstructionResult:
        start = time.perf_counter()
        steps: list[str] = []
        warnings: list[str] = []

        pipe_result = self._pipe_extraction_pipeline.run(contents, content_type)
        steps.append("pipe_extraction")
        warnings.extend(pipe_result.warnings)

        split_segments = split_segments_at_branch_points(pipe_result.segments)
        steps.append("branch_point_splitting")

        node_positions, edge_endpoints = build_nodes(split_segments)
        steps.append("node_construction")

        graph = build_graph(node_positions, edge_endpoints)
        steps.append("graph_construction")

        fitting_by_node: dict[int, FittingMatch] = {}
        try:
            detection_result = self._detection_pipeline.run(contents, content_type)
            detections: list[DetectionItemResult] = detection_result.detections
            if detections:
                fitting_by_node = associate_fittings(node_positions, detections)
            steps.append("fitting_association")
        except AppError as exc:
            warnings.append(
                f"Symbol detection unavailable - graph built from pipe geometry alone ({exc.code})."
            )
            logger.info("Fitting association skipped: %s", exc.message)

        analysis = analyze(graph)
        steps.append("graph_analysis")

        if graph.number_of_nodes() == 0:
            warnings.append("No pipe geometry was available to build a graph from.")

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "Graph construction complete in %.1fms: %d node(s), %d edge(s), %d branch(es), "
            "%d dead end(s), %d loop(s), %d connected component(s)",
            elapsed_ms, graph.number_of_nodes(), graph.number_of_edges(),
            len(analysis.branch_node_ids), len(analysis.dead_end_node_ids),
            len(analysis.loops), len(analysis.connected_components),
        )

        return GraphConstructionResult(
            node_positions=node_positions,
            node_degrees=dict(graph.degree()),
            fitting_by_node=fitting_by_node,
            edges=[(u, v, data) for u, v, data in graph.edges(data=True)],
            analysis=analysis,
            steps_applied=steps,
            warnings=warnings,
            processing_time_ms=round(elapsed_ms, 1),
        )
