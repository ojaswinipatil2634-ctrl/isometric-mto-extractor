"""
Adaptive threshold stage.

The final preprocessing step, producing a binary image ready for OCR
(Phase 3) and line/symbol detection (Phases 4-5). Adaptive (not global)
thresholding is used because isometric drawings frequently have uneven
lighting/scan exposure across the sheet - a single global threshold
would blow out one corner while leaving another too dark to read.
"""
import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def adaptive_threshold(image: np.ndarray, block_size: int = 35, c: int = 11) -> np.ndarray:
    """
    Binarize a BGR or grayscale image using adaptive Gaussian thresholding.

    `block_size` must be odd - the neighborhood size used to compute each
    pixel's local threshold. `c` is a constant subtracted from the mean,
    fine-tuning how aggressively mid-tones get pushed to black or white.
    """
    if block_size % 2 == 0:
        block_size += 1

    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,
        blockSize=block_size, C=c,
    )
    logger.info("Threshold: applied adaptive Gaussian threshold (block_size=%d, C=%d)", block_size, c)
    return binary
