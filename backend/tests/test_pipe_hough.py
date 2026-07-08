import cv2
import numpy as np
import pytest

from app.services.pipe_extraction.hough import detect_line_segments


def _skeleton_with_line(p1, p2, size=(200, 400)) -> np.ndarray:
    img = np.zeros(size, dtype=np.uint8)
    cv2.line(img, p1, p2, 255, thickness=1)
    return img


def test_detects_a_single_horizontal_line():
    skeleton = _skeleton_with_line((50, 100), (350, 100))

    segments = detect_line_segments(skeleton)

    assert len(segments) >= 1
    seg = segments[0]
    assert abs(seg.y1 - 100) <= 1
    assert abs(seg.y2 - 100) <= 1
    # Detected segment should span most of the drawn line's length.
    assert abs(seg.x2 - seg.x1) > 250


def test_returns_empty_list_for_blank_image():
    skeleton = np.zeros((100, 100), dtype=np.uint8)

    segments = detect_line_segments(skeleton)

    assert segments == []


def test_short_noise_segments_are_filtered_by_min_line_length():
    skeleton = np.zeros((100, 100), dtype=np.uint8)
    cv2.line(skeleton, (10, 10), (14, 10), 255, thickness=1)  # 4px, well under default min length

    segments = detect_line_segments(skeleton, min_line_length=15)

    assert segments == []


def test_rejects_non_single_channel_input():
    color_image = np.zeros((10, 10, 3), dtype=np.uint8)

    with pytest.raises(ValueError):
        detect_line_segments(color_image)
