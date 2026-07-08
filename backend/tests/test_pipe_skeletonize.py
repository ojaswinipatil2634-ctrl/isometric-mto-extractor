import cv2
import numpy as np
import pytest

from app.services.pipe_extraction.skeletonize import binary_to_skeleton


def _binarize(img_bgr: np.ndarray) -> np.ndarray:
    """Mimic Phase 2's threshold polarity: ink=0 (black), background=255."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    return binary


def test_skeleton_of_thick_line_is_thin_and_continuous():
    img = np.full((200, 400, 3), 255, dtype=np.uint8)
    cv2.line(img, (50, 100), (350, 100), (0, 0, 0), thickness=9)
    binary = _binarize(img)

    skeleton = binary_to_skeleton(binary)

    assert skeleton.shape == binary.shape
    assert set(np.unique(skeleton)).issubset({0, 255})

    # The skeleton should be much thinner than the original 9px-wide line.
    original_fg_px = int((binary == 0).sum())
    skeleton_fg_px = int((skeleton == 255).sum())
    assert 0 < skeleton_fg_px < original_fg_px

    # It should still span roughly the full length of the original line
    # (continuity preserved, not shattered into disconnected fragments).
    ys, xs = np.where(skeleton == 255)
    assert xs.max() - xs.min() > 250


def test_skeleton_of_blank_image_is_blank():
    img = np.full((100, 100, 3), 255, dtype=np.uint8)
    binary = _binarize(img)

    skeleton = binary_to_skeleton(binary)

    assert int((skeleton == 255).sum()) == 0


def test_rejects_non_single_channel_input():
    color_image = np.zeros((10, 10, 3), dtype=np.uint8)

    with pytest.raises(ValueError):
        binary_to_skeleton(color_image)
