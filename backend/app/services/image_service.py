"""
Image preprocessing: PDF -> image conversion, resizing, and light
enhancement before the image is sent to Gemini Vision.
"""
from __future__ import annotations

import io
import logging

from PIL import Image, ImageOps
from pdf2image import convert_from_bytes

logger = logging.getLogger(__name__)

MAX_DIMENSION = 2048  # keep well under Gemini's practical vision limits
POPPLER_PATH = r"C:\poppler\poppler-26.02.0\Library\bin"

class UnsupportedFileError(Exception):
    pass


def bytes_to_image(raw: bytes, filename: str) -> Image.Image:
    """Convert uploaded bytes (PNG/JPG/PDF) into a single PIL Image.

    For multi-page PDFs we take the first page as the primary drawing
    (multi-page support is listed as a bonus enhancement point).
    """
    lower = filename.lower()
    if lower.endswith(".pdf"):
        try:
            pages = convert_from_bytes(
    raw,
    dpi=200,
    first_page=1,
    last_page=1,
    poppler_path=POPPLER_PATH,
)
        except Exception as exc:  # poppler missing, corrupt pdf, etc.
            logger.exception("PDF conversion failed")
            raise UnsupportedFileError(f"Could not convert PDF: {exc}") from exc
        if not pages:
            raise UnsupportedFileError("PDF contains no pages")
        image = pages[0]
    elif lower.endswith((".png", ".jpg", ".jpeg")):
        try:
            image = Image.open(io.BytesIO(raw))
            image.load()
        except Exception as exc:
            raise UnsupportedFileError(f"Could not read image: {exc}") from exc
    else:
        raise UnsupportedFileError(f"Unsupported file type for '{filename}'")

    return image.convert("RGB")


def preprocess(image: Image.Image) -> Image.Image:
    """Resize to a bounded dimension and apply light contrast normalization.

    Keeping the image within MAX_DIMENSION reduces token/latency cost on
    the vision call while preserving enough detail for line/symbol reading.
    """
    image = ImageOps.exif_transpose(image)
    w, h = image.size
    scale = min(1.0, MAX_DIMENSION / max(w, h))
    if scale < 1.0:
        image = image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    image = ImageOps.autocontrast(image, cutoff=1)
    return image


def image_to_png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
