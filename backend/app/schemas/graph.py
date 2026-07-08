"""Request/response schemas for the Phase 6 /graph endpoint."""
from pydantic import BaseModel, Field


class GraphNodeSchema(BaseModel):
    id: int
    x: float
    y: float
    degree: int
    is_dead_end: bool
    is_branch: bool
    fitting_type: str | None = Field(
        None, description="Nearest Phase 4 detected fitting class, if any was within range."
    )
    fitting_confidence: float | None = None


class GraphEdgeSchema(BaseModel):
    source_node_id: int
    target_node_id: int
    length_px: float
    angle_degrees: float
    orientation: str = Field(..., examples=["horizontal", "vertical", "diagonal"])
    source_segment_count: int


class GraphConstructionResponse(BaseModel):
    status: str = Field(..., examples=["constructed"])
    filename: str
    nodes: list[GraphNodeSchema]
    edges: list[GraphEdgeSchema]
    node_count: int
    edge_count: int
    branch_node_ids: list[int]
    dead_end_node_ids: list[int]
    loops: list[list[int]] = Field(..., description="Each inner list is the node ids forming one cycle.")
    loop_count: int
    connected_components: list[list[int]]
    connected_component_count: int
    is_fully_connected: bool
    steps_applied: list[str]
    warnings: list[str]
    processing_time_ms: float
