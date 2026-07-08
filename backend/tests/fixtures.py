"""
Synthetic fixtures for preprocessing tests.

We don't have real isometric drawings to test against, so these
generate simple synthetic images/PDFs with known, checkable properties
(a known rotation angle, a known size, known content) so the pipeline's
behavior can be asserted precisely instead of eyeballed.
"""
import io

import cv2
import numpy as np


def make_line_drawing(width: int = 800, height: int = 600) -> np.ndarray:
    """A white canvas with black rectangle borders and cross-hatching,
    similar in spirit to a simple piping drawing's border + title block
    lines. Has enough straight edges for Hough-based skew detection."""
    img = np.full((height, width, 3), 255, dtype=np.uint8)
    cv2.rectangle(img, (20, 20), (width - 20, height - 20), (0, 0, 0), 3)
    cv2.rectangle(img, (20, height - 120), (width - 20, height - 20), (0, 0, 0), 2)
    for x in range(60, width - 60, 80):
        cv2.line(img, (x, 20), (x, height - 20), (0, 0, 0), 1)
    cv2.putText(img, "DWG NO. MTO-001 REV A", (40, height - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    return img


def rotate_image(img: np.ndarray, angle_degrees: float) -> np.ndarray:
    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle_degrees, 1.0)
    return cv2.warpAffine(img, matrix, (w, h), borderValue=(255, 255, 255))


def encode_png_bytes(img: np.ndarray) -> bytes:
    success, buffer = cv2.imencode(".png", img)
    assert success
    return buffer.tobytes()


def make_l_shaped_pipe_drawing(width: int = 800, height: int = 600, thickness: int = 5) -> np.ndarray:
    """A white canvas with one horizontal and one vertical black line
    meeting at a corner, like a simple two-segment pipe run with a
    90-degree elbow. Known geometry so segment count/orientation/
    length can be asserted precisely."""
    img = np.full((height, width, 3), 255, dtype=np.uint8)
    cv2.line(img, (100, 150), (600, 150), (0, 0, 0), thickness)
    cv2.line(img, (600, 150), (600, 450), (0, 0, 0), thickness)
    return img


def make_broken_horizontal_pipe_drawing(
    width: int = 800, height: int = 200, gap_start: int = 380, gap_end: int = 420
) -> np.ndarray:
    """A single horizontal pipe run interrupted by a small gap (e.g.
    where a dimension label or symbol would sit), used to verify that
    polyline merging bridges small gaps into one continuous segment."""
    img = np.full((height, width, 3), 255, dtype=np.uint8)
    cv2.line(img, (100, 100), (gap_start, 100), (0, 0, 0), 4)
    cv2.line(img, (gap_end, 100), (700, 100), (0, 0, 0), 4)
    return img


def make_pdf_bytes(img: np.ndarray) -> bytes:
    """Wrap a synthetic image into a minimal single-page PDF via PyMuPDF."""
    import fitz

    png_bytes = encode_png_bytes(img)
    doc = fitz.open()
    h, w = img.shape[:2]
    page = doc.new_page(width=w, height=h)
    page.insert_image(fitz.Rect(0, 0, w, h), stream=png_bytes)
    buffer = io.BytesIO()
    doc.save(buffer)
    doc.close()
    return buffer.getvalue()


def make_t_junction_pipe_drawing(width: int = 800, height: int = 600, thickness: int = 5) -> np.ndarray:
    """A horizontal run with a vertical branch meeting it mid-span - a
    T-junction, i.e. one node of degree 3 with three dead-end arms."""
    img = np.full((height, width, 3), 255, dtype=np.uint8)
    cv2.line(img, (100, 300), (700, 300), (0, 0, 0), thickness)
    cv2.line(img, (400, 300), (400, 500), (0, 0, 0), thickness)
    return img


def make_closed_loop_pipe_drawing(width: int = 800, height: int = 600, thickness: int = 5) -> np.ndarray:
    """A rectangle of four straight pipe runs forming one closed loop -
    every node has degree 2, there are no dead ends, and there is
    exactly one cycle."""
    img = np.full((height, width, 3), 255, dtype=np.uint8)
    cv2.line(img, (150, 150), (650, 150), (0, 0, 0), thickness)  # top
    cv2.line(img, (650, 150), (650, 450), (0, 0, 0), thickness)  # right
    cv2.line(img, (650, 450), (150, 450), (0, 0, 0), thickness)  # bottom
    cv2.line(img, (150, 450), (150, 150), (0, 0, 0), thickness)  # left
    return img
