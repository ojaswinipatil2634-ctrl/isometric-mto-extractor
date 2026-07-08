import math

from app.services.graph_construction.branch_splitting import split_segments_at_branch_points
from app.services.pipe_extraction.polyline import PipeSegment


def _seg(start, end, orientation="horizontal") -> PipeSegment:
    length = math.hypot(end[0] - start[0], end[1] - start[1])
    return PipeSegment(
        start=start, end=end, length_px=length, angle_degrees=0.0,
        orientation=orientation, source_segment_count=1,
    )


def test_splits_main_run_at_mid_span_branch_point():
    main_run = _seg((100, 300), (700, 300), orientation="horizontal")
    branch = _seg((400, 300), (400, 500), orientation="vertical")

    result = split_segments_at_branch_points([main_run, branch])

    # The main run should now be two pieces meeting exactly at (400, 300).
    assert len(result) == 3
    endpoints = {p for seg in result for p in (seg.start, seg.end)}
    assert (400.0, 300.0) in endpoints
    # Total length of the two main-run pieces should still sum to the original.
    main_pieces = [s for s in result if s.orientation == "horizontal"]
    assert len(main_pieces) == 2
    assert abs(sum(s.length_px for s in main_pieces) - main_run.length_px) < 0.5


def test_does_not_split_near_existing_endpoint_corner_case():
    # An L-corner: the second segment's endpoint lands right at (or
    # very near) the first segment's own endpoint - this is a normal
    # corner join, not a mid-span branch, and shouldn't trigger a split.
    corner_a = _seg((100, 100), (400, 100))
    corner_b = _seg((400, 100), (400, 400))

    result = split_segments_at_branch_points([corner_a, corner_b])

    assert len(result) == 2


def test_pure_crossing_without_shared_endpoint_is_not_split():
    """
    Two lines that merely cross, with neither's endpoint landing on the
    other, represent two unconnected pipes overlapping in the isometric
    2D projection - NOT a real tee/cross fitting. A genuine branch is
    always drawn with one run's endpoint touching the other run (the
    mid-span case above); a bare crossing must not be treated as a
    junction, or unrelated pipes would get spuriously merged into one
    connected run.
    """
    horizontal = _seg((100, 300), (700, 300))
    vertical = _seg((400, 50), (400, 550))

    result = split_segments_at_branch_points([horizontal, vertical])

    assert result == [horizontal, vertical]


def test_empty_input_returns_empty():
    assert split_segments_at_branch_points([]) == []


def test_unrelated_segments_are_left_alone():
    a = _seg((0, 0), (100, 0))
    b = _seg((500, 500), (600, 500))

    result = split_segments_at_branch_points([a, b])

    assert result == [a, b]
