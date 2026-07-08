"""
Resize stage.

Downstream OCR (Phase 3) and symbol detection (Phase 4) both expect a
predictable resolution range - too small and small dimension text
becomes unreadable, too large and inference gets slow with no accuracy
benefit. This stage caps the longest edge at MAX_DIMENSION while
preserving aspect ratio, and never upscales (upscaling fabricates detail
that isn't in the source drawing).
"""
import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)

MAX_DIMENSION_PX = 2200


def resize(image: np.ndarray, max_dimension: int = MAX_DIMENSION_PX) -> tuple[np.ndarray, float]:
    """
    Scale `image` so its longest edge is at most `max_dimension` pixels.

    Returns (resized_image, scale_factor). scale_factor is 1.0 if no
    resizing was needed (image already within bounds).
    """
    h, w = image.shape[:2]
    longest_edge = max(h, w)

    if longest_edge <= max_dimension:
        return image, 1.0

    scale = max_dimension / longest_edge
    new_size = (int(w * scale), int(h * scale))
    resized = cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)
    logger.info("Resize: %dx%d -> %dx%d (scale=%.4f)", w, h, new_size[0], new_size[1], scale)
    return resized, scale
