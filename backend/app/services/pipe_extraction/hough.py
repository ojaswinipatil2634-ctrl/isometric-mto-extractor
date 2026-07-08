"""
Hough transform stage.

Runs the probabilistic Hough transform (`cv2.HoughLinesP`) against the
skeletonized drawing (skeletonize.py) to extract raw straight line
segments. This is the layer that turns "which pixels are ink" into
"where are the straight runs" - pipe segments in an isometric drawing
are always straight lines between fittings, so this is the geometric
primitive the rest of pipe extraction (polyline.py) builds on.

OpenCV only - no learned model is involved in this stage.
"""
import logging
from dataclasses import dataclass

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RawLineSegment:
    """One straight line segment as returned directly by HoughLinesP,
    in image pixel coordinates."""

    x1: float
    y1: float
    x2: float
    y2: float


def detect_line_segments(
    skeleton: np.ndarray,
    rho: float = 1.0,
    theta_degrees: float = 1.0,
    threshold: int = 20,
    min_line_length: int = 15,
    max_line_gap: int = 8,
) -> list[RawLineSegment]:
    """
    Detect straight line segments in a skeletonized binary image.

    Parameters mirror `cv2.HoughLinesP` directly:
      - rho: distance resolution of the accumulator, in pixels.
      - theta_degrees: angle resolution of the accumulator, in degrees
        (converted to radians internally).
      - threshold: minimum accumulator votes for a line to be reported.
      - min_line_length: shorter segments are discarded - filters out
        noise from text characters and symbol edges that survived
        skeletonization but aren't pipe runs.
      - max_line_gap: maximum gap (px) between points on the same line
        to treat them as one segment rather than two.

    Returns an empty list (not an error) if no lines are found - a
    blank or symbol-only drawing with no pipe runs is a valid input,
    not a failure.
    """
    if skeleton.ndim != 2:
        raise ValueError(f"detect_line_segments expects a single-channel image, got shape {skeleton.shape}")

    lines = cv2.HoughLinesP(
        skeleton,
        rho,
        np.deg2rad(theta_degrees),
        threshold,
        minLineLength=min_line_length,
        maxLineGap=max_line_gap,
    )

    if lines is None:
        logger.info("Hough: no line segments detected")
        return []

    segments = [RawLineSegment(float(x1), float(y1), float(x2), float(y2)) for (x1, y1, x2, y2) in lines[:, 0, :]]
    logger.info("Hough: detected %d raw line segment(s)", len(segments))
    return segments
