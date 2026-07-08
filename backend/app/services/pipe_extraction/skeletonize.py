"""
Skeletonization stage.

Reduces the thick, variable-width pipe lines in the Phase 2 binarized
output down to a 1px-wide topological skeleton. Hough line detection
(hough.py) is far more accurate and produces far fewer duplicate/
overlapping segments when it runs against a skeleton than against the
original variable-width ink - a 6px-wide pipe line would otherwise be
picked up as two or three near-parallel Hough lines along its edges.

Uses `skimage.morphology.skeletonize` (medial-axis style thinning).
This is the one place scikit-image is used in the project so far - the
dependency was declared back in Phase 2's requirements.txt for exactly
this purpose.
"""
import logging

import numpy as np
from skimage.morphology import skeletonize

logger = logging.getLogger(__name__)


def binary_to_skeleton(binary_image: np.ndarray) -> np.ndarray:
    """
    Skeletonize a binarized drawing.

    `binary_image` is expected to be the Phase 2 adaptive-threshold
    output: a single-channel image where ink (pipe lines, symbols,
    text) is 0 (black) and background is 255 (white) - i.e.
    `cv2.THRESH_BINARY` polarity, not inverted.

    Returns a uint8 image of the same shape, values in {0, 255}, where
    255 marks the 1px-wide skeleton of the foreground ink.
    """
    if binary_image.ndim != 2:
        raise ValueError(f"binary_to_skeleton expects a single-channel image, got shape {binary_image.shape}")

    foreground_mask = binary_image == 0
    skeleton_mask = skeletonize(foreground_mask)
    skeleton = (skeleton_mask.astype(np.uint8)) * 255

    foreground_px = int(foreground_mask.sum())
    skeleton_px = int(skeleton_mask.sum())
    logger.info(
        "Skeletonize: %d foreground px -> %d skeleton px (%.1f%% retained)",
        foreground_px, skeleton_px, (100.0 * skeleton_px / foreground_px) if foreground_px else 0.0,
    )
    return skeleton
