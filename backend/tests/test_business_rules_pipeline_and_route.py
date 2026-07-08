import io

from app.services.business_rules.pipeline import BusinessRulesPipeline
from app.services.graph_construction.analysis import GraphAnalysis
from app.services.graph_construction.fitting_association import FittingMatch
from app.services.graph_construction.pipeline import GraphConstructionResult
from tests.fixtures import encode_png_bytes, make_closed_loop_pipe_drawing, make_t_junction_pipe_drawing


class _StubGraphPipeline:
    """Stands in for GraphConstructionPipeline so hardware generation and
    connectivity rules can be tested against a fully controlled graph,
    without needing a real image processed through the whole CV stack."""

    def __init__(self, result: GraphConstructionResult):
        self._result = result

    def run(self, contents: bytes, content_type: str) -> GraphConstructionResult:
        return self._result


def _make_graph_result(**overrides) -> GraphConstructionResult:
    defaults = dict(
        node_positions={0: (0.0, 0.0), 1: (100.0, 0.0)},
        node_degrees={0: 1, 1: 1},
        fitting_by_node={},
        edges=[(0, 1, {"length_px": 100.0, "angle_degrees": 0.0, "orientation": "horizontal", "source_segment_count": 1})],
        analysis=GraphAnalysis(dead_end_node_ids=[0, 1], is_fully_connected=True),
        steps_applied=["pipe_extraction", "node_construction", "graph_construction", "graph_analysis"],
        warnings=[],
        processing_time_ms=1.0,
    )
    defaults.update(overrides)
    return GraphConstructionResult(**defaults)


def _fitting(name: str) -> FittingMatch:
    return FittingMatch(class_name=name, confidence=0.9, distance_px=3.0)


PNG_BYTES = encode_png_bytes(make_t_junction_pipe_drawing())


# --- hardware generation, via a controlled graph ---

def test_pipeline_generates_hardware_for_detected_flange_nodes():
    graph_result = _make_graph_result(
        node_positions={0: (0.0, 0.0), 1: (100.0, 0.0)},
        node_degrees={0: 1, 1: 1},
        fitting_by_node={0: _fitting("flange"), 1: _fitting("flange")},
        analysis=GraphAnalysis(dead_end_node_ids=[], is_fully_connected=True),
    )
    pipeline = BusinessRulesPipeline(graph_pipeline=_StubGraphPipeline(graph_result))

    result = pipeline.run(PNG_BYTES, "image/png")

    gaskets = [item for item in result.hardware if item.item_type == "gasket"]
    assert len(gaskets) == 2
    assert {g.node_id for g in gaskets} == {0, 1}


def test_pipeline_produces_no_hardware_without_flanges():
    graph_result = _make_graph_result(fitting_by_node={0: _fitting("elbow")})
    pipeline = BusinessRulesPipeline(graph_pipeline=_StubGraphPipeline(graph_result))

    result = pipeline.run(PNG_BYTES, "image/png")

    assert result.hardware == []


# --- connectivity rule wiring ---

def test_pipeline_flags_missing_fitting_for_unmatched_branch():
    graph_result = _make_graph_result(
        node_degrees={0: 1, 1: 3, 2: 1, 3: 1},
        fitting_by_node={},
        analysis=GraphAnalysis(branch_node_ids=[1], dead_end_node_ids=[0, 2, 3], is_fully_connected=True),
    )
    pipeline = BusinessRulesPipeline(graph_pipeline=_StubGraphPipeline(graph_result))

    result = pipeline.run(PNG_BYTES, "image/png")

    codes = {v.rule_code for v in result.violations}
    assert "MISSING_FITTING" in codes
    assert "UNTERMINATED_PIPE" in codes


def test_pipeline_flags_invalid_reducer():
    graph_result = _make_graph_result(
        node_degrees={0: 1, 1: 1},
        fitting_by_node={0: _fitting("reducer")},
        analysis=GraphAnalysis(dead_end_node_ids=[1], is_fully_connected=True),
    )
    pipeline = BusinessRulesPipeline(graph_pipeline=_StubGraphPipeline(graph_result))

    result = pipeline.run(PNG_BYTES, "image/png")

    reducer_violations = [v for v in result.violations if v.rule_code == "INVALID_REDUCER"]
    assert len(reducer_violations) == 1


def test_pipeline_flags_impossible_connection():
    graph_result = _make_graph_result(
        node_degrees={0: 1, 1: 1},
        fitting_by_node={0: _fitting("gate_valve"), 1: _fitting("globe_valve")},
        edges=[(0, 1, {"length_px": 1.0, "angle_degrees": 0.0, "orientation": "horizontal", "source_segment_count": 1})],
        analysis=GraphAnalysis(dead_end_node_ids=[], is_fully_connected=True),
    )
    pipeline = BusinessRulesPipeline(graph_pipeline=_StubGraphPipeline(graph_result))

    result = pipeline.run(PNG_BYTES, "image/png")

    codes = {v.rule_code for v in result.violations}
    assert "IMPOSSIBLE_CONNECTION" in codes


def test_pipeline_no_violations_for_clean_graph():
    graph_result = _make_graph_result(
        node_degrees={0: 1, 1: 1},
        fitting_by_node={0: _fitting("flange"), 1: _fitting("flange")},
        analysis=GraphAnalysis(dead_end_node_ids=[0, 1], is_fully_connected=True),
    )
    pipeline = BusinessRulesPipeline(graph_pipeline=_StubGraphPipeline(graph_result))

    result = pipeline.run(PNG_BYTES, "image/png")

    assert result.violations == []


# --- real end-to-end: T-junction and closed-loop drawings through the actual CV stack ---

def test_real_t_junction_drawing_flags_missing_fitting_and_unterminated_pipes():
    """
    No trained YOLO weights are configured in this environment, so
    every node in the real graph has no detected fitting - the T
    branch point should be flagged MISSING_FITTING and its three dead
    ends UNTERMINATED_PIPE, exercising the real graph construction path
    end to end (not a stub).
    """
    img = make_t_junction_pipe_drawing()
    result = BusinessRulesPipeline().run(encode_png_bytes(img), "image/png")

    codes = [v.rule_code for v in result.violations]
    assert codes.count("MISSING_FITTING") == 1
    assert codes.count("UNTERMINATED_PIPE") == 3
    assert result.hardware == []
    assert any("Duplicate-fitting check skipped" in w or "unavailable" in w for w in result.warnings)


def test_real_closed_loop_drawing_has_no_branch_or_dead_end_violations():
    img = make_closed_loop_pipe_drawing()
    result = BusinessRulesPipeline().run(encode_png_bytes(img), "image/png")

    codes = [v.rule_code for v in result.violations]
    assert "MISSING_FITTING" not in codes
    assert "UNTERMINATED_PIPE" not in codes


# --- route ---

def test_business_rules_endpoint_returns_expected_shape(client):
    files = {"file": ("tjunc.png", io.BytesIO(PNG_BYTES), "image/png")}

    response = client.post("/api/v1/business-rules", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "evaluated"
    assert "violations" in body
    assert "hardware" in body
    assert "duplicate_fittings" in body
    assert body["violation_count"] == len(body["violations"])


def test_business_rules_endpoint_rejects_unsupported_file_type(client):
    files = {"file": ("notes.txt", io.BytesIO(b"not a drawing"), "text/plain")}

    response = client.post("/api/v1/business-rules", files=files)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_FILE"
