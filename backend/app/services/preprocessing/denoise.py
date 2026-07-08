"""
Denoise stage.

Scanned/photographed drawings pick up sensor noise and JPEG artifacts
that hurt downstream OCR and line detection. Non-local means denoising
preserves edges (line work, text strokes) far better than a Gaussian
blur would, at the cost of being slower - acceptable here since this
runs once per uploaded drawing, not per video frame.
"""
import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def denoise(image: np.ndarray, strength: int = 7) -> np.ndarray:
    """
    Apply edge-preserving denoising to a BGR image.

    `strength` maps to OpenCV's `h`/`hColor` filter strength parameters -
    higher removes more noise but can soften fine text if pushed too far.
    """
    denoised = cv2.fastNlMeansDenoisingColored(
        image, None, h=strength, hColor=strength, templateWindowSize=7, searchWindowSize=21
    )
    logger.info("Denoise: applied fastNlMeansDenoisingColored (strength=%d)", strength)
    return denoised
