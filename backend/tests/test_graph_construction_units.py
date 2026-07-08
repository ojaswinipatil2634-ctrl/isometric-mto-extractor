from app.services.graph_construction.analysis import analyze
from app.services.graph_construction.graph_builder import build_graph
from app.services.graph_construction.node_builder import build_nodes
from app.services.pipe_extraction.polyline import PipeSegment


def _seg(start, end, orientation="horizontal") -> PipeSegment:
    import math
    length = math.hypot(end[0] - start[0], end[1] - start[1])
    return PipeSegment(
        start=start, end=end, length_px=length, angle_degrees=0.0,
        orientation=orientation, source_segment_count=1,
    )


# --- node_builder ---

def test_build_nodes_snaps_close_endpoints_together():
    # Two segments meeting near (400, 300), off by a few px of noise.
    segments = [
        _seg((100, 300), (399, 301)),
        _seg((401, 299), (400, 500)),
    ]

    positions, edges = build_nodes(segments, snap_tolerance_px=12.0)

    # 4 raw endpoints, but the two near (400,300) should merge -> 3 nodes.
    assert len(positions) == 3
    assert len(edges) == 2


def test_build_nodes_keeps_far_endpoints_separate():
    segments = [
        _seg((0, 0), (100, 0)),
        _seg((300, 300), (400, 300)),
    ]

    positions, edges = build_nodes(segments, snap_tolerance_px=12.0)

    assert len(positions) == 4
    assert len(edges) == 2


def test_build_nodes_handles_empty_input():
    positions, edges = build_nodes([])

    assert positions == {}
    assert edges == []


# --- graph_builder ---

def test_build_graph_creates_nodes_and_edges():
    segments = [_seg((0, 0), (100, 0)), _seg((100, 0), (100, 100))]
    positions, edges = build_nodes(segments)

    graph = build_graph(positions, edges)

    assert graph.number_of_nodes() == 3
    assert graph.number_of_edges() == 2


def test_build_graph_skips_degenerate_self_loop_segments():
    # A segment whose two endpoints snap to the same node shouldn't
    # become a self-loop edge.
    segments = [_seg((100, 100), (105, 102))]
    positions, edges = build_nodes(segments, snap_tolerance_px=12.0)

    graph = build_graph(positions, edges)

    assert graph.number_of_edges() == 0


# --- analysis ---

def test_analyze_straight_line_has_two_dead_ends_no_branches_no_loops():
    segments = [_seg((0, 0), (100, 0))]
    positions, edges = build_nodes(segments)
    graph = build_graph(positions, edges)

    result = analyze(graph)

    assert len(result.dead_end_node_ids) == 2
    assert result.branch_node_ids == []
    assert result.loops == []
    assert result.is_fully_connected is True
    assert len(result.connected_components) == 1


def test_analyze_t_junction_has_one_branch_and_three_dead_ends():
    # Three arms meeting at (400, 300).
    segments = [
        _seg((100, 300), (400, 300)),
        _seg((400, 300), (700, 300)),
        _seg((400, 300), (400, 500)),
    ]
    positions, edges = build_nodes(segments)
    graph = build_graph(positions, edges)

    result = analyze(graph)

    assert len(result.branch_node_ids) == 1
    assert len(result.dead_end_node_ids) == 3
    assert result.loops == []


def test_analyze_closed_square_loop_has_one_cycle_and_no_dead_ends():
    segments = [
        _seg((150, 150), (650, 150)),
        _seg((650, 150), (650, 450)),
        _seg((650, 450), (150, 450)),
        _seg((150, 450), (150, 150)),
    ]
    positions, edges = build_nodes(segments)
    graph = build_graph(positions, edges)

    result = analyze(graph)

    assert result.dead_end_node_ids == []
    assert result.branch_node_ids == []
    assert len(result.loops) == 1
    assert len(result.loops[0]) == 4


def test_analyze_disconnected_runs_reports_multiple_components():
    segments = [
        _seg((0, 0), (100, 0)),
        _seg((500, 500), (600, 500)),
    ]
    positions, edges = build_nodes(segments)
    graph = build_graph(positions, edges)

    result = analyze(graph)

    assert result.is_fully_connected is False
    assert len(result.connected_components) == 2


def test_analyze_empty_graph_is_trivially_connected():
    positions, edges = build_nodes([])
    graph = build_graph(positions, edges)

    result = analyze(graph)

    assert result.is_fully_connected is True
    assert result.branch_node_ids == []
    assert result.dead_end_node_ids == []
    assert result.loops == []


def test_analyze_parallel_segments_between_same_nodes_is_a_loop():
    # Two distinct runs both connecting the same two junctions - a real
    # loop even though a simple-graph cycle_basis alone wouldn't see it.
    segments = [
        _seg((0, 0), (100, 0)),
        _seg((0, 0), (100, 0)),
    ]
    positions, edges = build_nodes(segments)
    graph = build_graph(positions, edges)

    result = analyze(graph)

    assert graph.number_of_edges() == 2
    assert len(result.loops) == 1
