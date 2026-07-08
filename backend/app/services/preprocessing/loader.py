"""
Loads raw upload bytes (PDF, PNG, JPG) into a single OpenCV BGR image.

This is the only place in the preprocessing pipeline that needs to know
about the *source format* of the drawing. Every stage after this one
works purely in terms of numpy arrays, so PDF vs. image handling never
leaks into deskew/denoise/resize/contrast/threshold logic.
"""
import io
import logging

import cv2
import fitz  # PyMuPDF
import numpy as np
from PIL import Image

from app.core.errors import InvalidFileError

logger = logging.getLogger(__name__)

# Render PDFs at this DPI before rasterizing to a bitmap. 300 DPI is a
# reasonable default for isometric drawings with small dimension text.
PDF_RENDER_DPI = 300


def load_as_bgr_image(contents: bytes, content_type: str) -> np.ndarray:
    """
    Convert uploaded file bytes into a BGR numpy array (OpenCV's native
    color order), regardless of whether the source was a PDF, PNG, or JPG.

    Raises:
        InvalidFileError: if the bytes can't be decoded as the claimed type.
    """
    if content_type == "application/pdf":
        return _load_pdf_first_page(contents)
    return _load_raster_image(contents)


def _load_pdf_first_page(contents: bytes) -> np.ndarray:
    try:
        doc = fitz.open(stream=contents, filetype="pdf")
    except Exception as exc:  # PyMuPDF raises its own exception types
        raise InvalidFileError("Could not open PDF - the file may be corrupted.") from exc

    if doc.page_count == 0:
        doc.close()
        raise InvalidFileError("PDF contains no pages.")

    try:
        page = doc.load_page(0)
        zoom = PDF_RENDER_DPI / 72.0  # PDF points are 72 DPI
        matrix = fitz.Matrix(zoom, zoom)
        pixmap = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB)

        image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
            pixmap.height, pixmap.width, pixmap.n
        )
        # PyMuPDF gives RGB; OpenCV expects BGR.
        bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        logger.info("Rasterized PDF page 1/%d at %d DPI -> %dx%d", doc.page_count, PDF_RENDER_DPI, pixmap.width, pixmap.height)
        return bgr
    finally:
        doc.close()


def _load_raster_image(contents: bytes) -> np.ndarray:
    try:
        pil_image = Image.open(io.BytesIO(contents))
        pil_image.load()
    except Exception as exc:
        raise InvalidFileError("Could not decode image - the file may be corrupted.") from exc

    rgb_image = pil_image.convert("RGB")
    array = np.array(rgb_image)
    bgr = cv2.cvtColor(array, cv2.COLOR_RGB2BGR)
    return bgr
