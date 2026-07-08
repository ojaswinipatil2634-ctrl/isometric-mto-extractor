from app.services.pipe_extraction.hough import RawLineSegment
from app.services.pipe_extraction.polyline import classify_orientation, merge_line_segments


def test_merges_two_collinear_segments_with_small_gap_into_one():
    segments = [
        RawLineSegment(100, 100, 300, 100),
        RawLineSegment(310, 100, 500, 100),  # 10px gap, well under default tolerance
    ]

    merged = merge_line_segments(segments, gap_tolerance_px=15.0)

    assert len(merged) == 1
    seg = merged[0]
    assert seg.source_segment_count == 2
    assert seg.orientation == "horizontal"
    # Should span from the leftmost to the rightmost endpoint.
    assert min(seg.start[0], seg.end[0]) == 100
    assert max(seg.start[0], seg.end[0]) == 500


def test_does_not_merge_segments_with_large_gap():
    segments = [
        RawLineSegment(100, 100, 200, 100),
        RawLineSegment(400, 100, 500, 100),  # 200px gap, far beyond tolerance
    ]

    merged = merge_line_segments(segments, gap_tolerance_px=15.0)

    assert len(merged) == 2


def test_does_not_merge_perpendicular_segments():
    segments = [
        RawLineSegment(100, 100, 300, 100),  # horizontal
        RawLineSegment(300, 100, 300, 300),  # vertical
    ]

    merged = merge_line_segments(segments)

    assert len(merged) == 2
    orientations = {seg.orientation for seg in merged}
    assert orientations == {"horizontal", "vertical"}


def test_does_not_merge_parallel_but_offset_segments():
    segments = [
        RawLineSegment(100, 100, 300, 100),
        RawLineSegment(100, 150, 300, 150),  # parallel, 50px away perpendicular to the line
    ]

    merged = merge_line_segments(segments, colinear_distance_tolerance_px=6.0)

    assert len(merged) == 2


def test_classify_orientation_horizontal_vertical_diagonal():
    assert classify_orientation(0.0) == "horizontal"
    assert classify_orientation(179.0) == "horizontal"
    assert classify_orientation(90.0) == "vertical"
    assert classify_orientation(88.0) == "vertical"
    assert classify_orientation(45.0) == "diagonal"
    assert classify_orientation(30.0) == "diagonal"


def test_empty_input_returns_empty_list():
    assert merge_line_segments([]) == []
