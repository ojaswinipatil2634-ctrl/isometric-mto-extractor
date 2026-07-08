"""
Deskew stage.

Isometric drawings scanned or photographed rarely land perfectly level.
This stage estimates the dominant skew angle from the drawing's straight
lines (border, title block, dimension lines) and rotates the image to
correct it.

Approach: binarize -> detect line segments with the probabilistic Hough
transform -> take the median angle of near-horizontal/near-vertical lines
-> rotate. The median (not mean) makes this robust to a handful of
outlier lines like leader lines and dimension arrows that legitimately
aren't parallel to the page edge.
"""
import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)

MAX_CORRECTABLE_SKEW_DEGREES = 15.0


def estimate_skew_angle(gray: np.ndarray) -> float:
    """Estimate the skew angle in degrees. Returns 0.0 if it can't be determined."""
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold=100, minLineLength=gray.shape[1] // 4, maxLineGap=10
    )

    if lines is None or len(lines) == 0:
        logger.info("Deskew: no lines detected, assuming 0deg skew")
        return 0.0

    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        # Normalize near-horizontal lines into [-45, 45] so a line drawn
        # slightly downward and one slightly "upward from the other end"
        # aren't treated as opposite skews.
        if angle > 45:
            angle -= 90
        elif angle < -45:
            angle += 90
        if abs(angle) <= MAX_CORRECTABLE_SKEW_DEGREES:
            angles.append(angle)

    if not angles:
        return 0.0

    skew = float(np.median(angles))
    logger.info("Deskew: estimated skew angle %.2fdeg from %d lines", skew, len(angles))
    return skew


def deskew(image: np.ndarray) -> tuple[np.ndarray, float]:
    """
    Correct rotation in a BGR image.

    Returns (deskewed_image, original_tilt_degrees). `original_tilt_degrees`
    is reported in the intuitive sign convention (positive = the input
    drawing was rotated that many degrees and has now been leveled) -
    this is the negation of the angle actually fed into the rotation
    matrix, since image-coordinate line angles (y grows downward) are
    mirrored relative to the rotation matrix's convention.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    correction_angle = estimate_skew_angle(gray)

    if abs(correction_angle) < 0.1:
        return image, 0.0

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, correction_angle, 1.0)
    rotated = cv2.warpAffine(
        image, rotation_matrix, (w, h),
        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE,
    )
    original_tilt_degrees = -correction_angle
    return rotated, original_tilt_degrees
