"""
/graph endpoint.

PHASE 6 SCOPE ONLY:
    Take Phase 5's straight pipe-run segments, snap their endpoints into
    shared junction nodes, and build a NetworkX graph. Report nodes,
    edges, branch points (degree >= 3), dead ends (degree == 1), loops
    (cycles), and connectivity (connected components). No business
    rules (Phase 7), no persistence (Phase 8), no AI - Gemini is never
    used here or anywhere in the extraction path.

Phase 4 symbol detection is used as best-effort enrichment only (to tag
junction nodes with a fitting type) - if no trained YOLO weights are
configured, the graph is still built from pipe geometry alone and a
warning is included, rather than failing the whole request.

Reuses UploadValidationService from Phase 1 so file-type/size rules
stay defined in exactly one place.
"""
import logging

from fastapi import APIRouter, Depends, UploadFile, File

from app.schemas.graph import GraphConstructionResponse, GraphEdgeSchema, GraphNodeSchema
from app.services.graph_construction.pipeline import GraphConstructionPipeline
from app.services.upload_validation_service import UploadValidationService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["graph-construction"])


def get_upload_validation_service() -> UploadValidationService:
    return UploadValidationService()


def get_graph_construction_pipeline() -> GraphConstructionPipeline:
    return GraphConstructionPipeline()


@router.post("/graph", response_model=GraphConstructionResponse)
async def construct_graph(
    file: UploadFile = File(...),
    validation_service: UploadValidationService = Depends(get_upload_validation_service),
    pipeline: GraphConstructionPipeline = Depends(get_graph_construction_pipeline),
) -> GraphConstructionResponse:
    contents = await validation_service.validate(file)

    result = pipeline.run(contents, file.content_type or "")

    logger.info(
        "Graph construction '%s': %d node(s), %d edge(s)",
        file.filename, len(result.node_positions), len(result.edges),
    )

    analysis = result.analysis
    branch_set = set(analysis.branch_node_ids)
    dead_end_set = set(analysis.dead_end_node_ids)

    nodes_schema = []
    for node_id, (x, y) in sorted(result.node_positions.items()):
        fitting = result.fitting_by_node.get(node_id)
        nodes_schema.append(
            GraphNodeSchema(
                id=node_id,
                x=round(x, 2),
                y=round(y, 2),
                degree=result.node_degrees.get(node_id, 0),
                is_dead_end=node_id in dead_end_set,
                is_branch=node_id in branch_set,
                fitting_type=fitting.class_name if fitting else None,
                fitting_confidence=fitting.confidence if fitting else None,
            )
        )

    edges_schema = [
        GraphEdgeSchema(
            source_node_id=u,
            target_node_id=v,
            length_px=data["length_px"],
            angle_degrees=data["angle_degrees"],
            orientation=data["orientation"],
            source_segment_count=data["source_segment_count"],
        )
        for u, v, data in result.edges
    ]

    return GraphConstructionResponse(
        status="constructed",
        filename=file.filename or "unknown",
        nodes=nodes_schema,
        edges=edges_schema,
        node_count=len(nodes_schema),
        edge_count=len(edges_schema),
        branch_node_ids=analysis.branch_node_ids,
        dead_end_node_ids=analysis.dead_end_node_ids,
        loops=analysis.loops,
        loop_count=len(analysis.loops),
        connected_components=analysis.connected_components,
        connected_component_count=len(analysis.connected_components),
        is_fully_connected=analysis.is_fully_connected,
        steps_applied=result.steps_applied,
        warnings=result.warnings,
        processing_time_ms=result.processing_time_ms,
    )
