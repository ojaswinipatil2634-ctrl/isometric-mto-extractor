import io

from app.services.graph_construction.pipeline import GraphConstructionPipeline
from tests.fixtures import (
    encode_png_bytes,
    make_closed_loop_pipe_drawing,
    make_l_shaped_pipe_drawing,
    make_t_junction_pipe_drawing,
)


def test_pipeline_builds_graph_from_l_shaped_drawing():
    img = make_l_shaped_pipe_drawing()
    png_bytes = encode_png_bytes(img)

    result = GraphConstructionPipeline().run(png_bytes, "image/png")

    assert "pipe_extraction" in result.steps_applied
    assert "node_construction" in result.steps_applied
    assert "graph_construction" in result.steps_applied
    assert "graph_analysis" in result.steps_applied

    # An L-shape is one elbow joining two straight runs: 3 nodes, 2
    # edges, 2 dead ends, 1 branch-free corner, no loops.
    assert len(result.node_positions) == 3
    assert len(result.edges) == 2
    assert len(result.analysis.dead_end_node_ids) == 2
    assert result.analysis.branch_node_ids == []
    assert result.analysis.loops == []
    assert result.analysis.is_fully_connected is True

    # Detection has no weights configured in this environment, so
    # fitting association should degrade gracefully with a warning
    # rather than failing the whole request.
    assert any("Symbol detection unavailable" in w for w in result.warnings)
    assert result.fitting_by_node == {}


def test_pipeline_builds_graph_from_t_junction_drawing():
    img = make_t_junction_pipe_drawing()
    png_bytes = encode_png_bytes(img)

    result = GraphConstructionPipeline().run(png_bytes, "image/png")

    assert len(result.analysis.branch_node_ids) == 1
    assert len(result.analysis.dead_end_node_ids) == 3
    assert result.analysis.loops == []


def test_pipeline_builds_graph_from_closed_loop_drawing():
    img = make_closed_loop_pipe_drawing()
    png_bytes = encode_png_bytes(img)

    result = GraphConstructionPipeline().run(png_bytes, "image/png")

    assert result.analysis.dead_end_node_ids == []
    assert result.analysis.branch_node_ids == []
    assert len(result.analysis.loops) == 1
    assert result.analysis.is_fully_connected is True


def test_pipeline_handles_blank_drawing_without_crashing():
    import numpy as np

    blank = np.full((400, 400, 3), 255, dtype=np.uint8)
    png_bytes = encode_png_bytes(blank)

    result = GraphConstructionPipeline().run(png_bytes, "image/png")

    assert result.node_positions == {}
    assert result.edges == []
    assert result.analysis.is_fully_connected is True
    assert any("No pipe geometry" in w or "No straight pipe" in w for w in result.warnings)


def test_graph_endpoint_returns_expected_shape_for_l_shaped_drawing(client):
    img = make_l_shaped_pipe_drawing()
    files = {"file": ("drawing.png", io.BytesIO(encode_png_bytes(img)), "image/png")}

    response = client.post("/api/v1/graph", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "constructed"
    assert body["node_count"] == 3
    assert body["edge_count"] == 2
    assert len(body["dead_end_node_ids"]) == 2
    assert body["branch_node_ids"] == []
    assert body["loop_count"] == 0
    assert body["is_fully_connected"] is True

    for node in body["nodes"]:
        assert node["degree"] in (1, 2)


def test_graph_endpoint_rejects_unsupported_file_type(client):
    files = {"file": ("notes.txt", io.BytesIO(b"not a drawing"), "text/plain")}

    response = client.post("/api/v1/graph", files=files)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_FILE"


def test_graph_endpoint_handles_closed_loop_drawing(client):
    img = make_closed_loop_pipe_drawing()
    files = {"file": ("loop.png", io.BytesIO(encode_png_bytes(img)), "image/png")}

    response = client.post("/api/v1/graph", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["loop_count"] == 1
    assert len(body["loops"][0]) == 4
    assert body["dead_end_node_ids"] == []
