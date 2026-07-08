"""
Contrast enhancement stage.

Uses CLAHE (Contrast Limited Adaptive Histogram Equalization) rather
than global histogram equalization. Isometric drawings often have
faded regions (photocopies, aged blueprints) alongside crisp regions in
the same sheet - CLAHE adapts locally instead of over- or under-
correcting the whole page from one global histogram.

Applied in LAB color space, only to the L (lightness) channel, so line
and text color information isn't distorted.
"""
import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def enhance_contrast(image: np.ndarray, clip_limit: float = 2.5, tile_size: int = 8) -> np.ndarray:
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
    l_enhanced = clahe.apply(l_channel)

    merged = cv2.merge((l_enhanced, a_channel, b_channel))
    result = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
    logger.info("Contrast: applied CLAHE (clip_limit=%.1f, tile=%dx%d)", clip_limit, tile_size, tile_size)
    return result
