from app.services.pipe_extraction.pipeline import PipeExtractionPipeline
from tests.fixtures import (
    encode_png_bytes,
    make_broken_horizontal_pipe_drawing,
    make_l_shaped_pipe_drawing,
)


def test_pipeline_extracts_two_segments_from_l_shaped_drawing():
    img = make_l_shaped_pipe_drawing()
    pipeline = PipeExtractionPipeline()

    result = pipeline.run(encode_png_bytes(img), "image/png")

    assert result.steps_applied == ["preprocess", "skeletonize", "hough_transform", "polyline_extraction"]
    assert result.raw_segment_count >= 2
    assert len(result.segments) == 2
    orientations = {seg.orientation for seg in result.segments}
    assert orientations == {"horizontal", "vertical"}
    assert result.warnings == []
    assert result.skeleton_image_shape[0] > 0
    assert result.skeleton_image_shape[1] > 0


def test_pipeline_bridges_small_gap_in_a_single_pipe_run():
    img = make_broken_horizontal_pipe_drawing()
    pipeline = PipeExtractionPipeline()

    result = pipeline.run(encode_png_bytes(img), "image/png")

    assert len(result.segments) == 1
    assert result.segments[0].orientation == "horizontal"
    assert result.segments[0].source_segment_count >= 2


def test_pipeline_warns_when_no_pipe_runs_found():
    import numpy as np

    blank = np.full((200, 200, 3), 255, dtype=np.uint8)
    pipeline = PipeExtractionPipeline()

    result = pipeline.run(encode_png_bytes(blank), "image/png")

    assert result.segments == []
    assert any("no straight pipe runs" in w.lower() for w in result.warnings)
