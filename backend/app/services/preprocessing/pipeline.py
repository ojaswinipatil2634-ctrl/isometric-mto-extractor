"""
Preprocessing pipeline orchestrator.

Chains: load -> deskew -> denoise -> resize -> contrast -> adaptive threshold

Each stage is a pure function in its own module (deskew.py, denoise.py,
etc.) so it can be unit tested and reasoned about independently. This
module's only job is sequencing them and recording what happened at
each step, which the API surfaces back to the caller for transparency
and debugging.
"""
import base64
import hashlib
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field

import cv2
import numpy as np

from app.services.preprocessing import contrast, denoise, deskew, loader, resize, threshold

logger = logging.getLogger(__name__)


@dataclass
class PreprocessingResult:
    processed_image: np.ndarray          # final binarized output (grayscale, 0/255)
    preview_image: np.ndarray             # contrast-enhanced BGR image, pre-threshold (for display)
    original_width: int
    original_height: int
    processed_width: int
    processed_height: int
    skew_angle_corrected_degrees: float
    resize_scale_factor: float
    steps_applied: list[str] = field(default_factory=list)
    processing_time_ms: float = 0.0


# Every stage (vision extraction, OCR, graph construction, and business
# rules - which internally runs its own OCR *and* graph construction
# again) independently instantiates its own PreprocessingPipeline() and
# runs this same chain on the same uploaded bytes. On a large, dense
# scan that chain alone can take 30-40s, so one request can pay that
# cost five separate times (~150-200s wasted) before any Gemini/OCR
# work even starts. Rather than thread a shared PreprocessingResult
# through every pipeline's constructor - a much larger, riskier change
# this close to a deadline - this small process-wide cache, keyed by a
# hash of the actual bytes, lets every call site keep constructing its
# own PreprocessingPipeline() (no signature changes needed) while the
# expensive chain only really runs once per distinct upload. Bounded to
# a handful of entries so memory can't grow unbounded across requests.
_CACHE_MAX_ENTRIES = 4
_cache_lock = threading.Lock()
_cache: "OrderedDict[str, PreprocessingResult]" = OrderedDict()


def _cache_key(contents: bytes, content_type: str) -> str:
    return f"{content_type}:{hashlib.sha256(contents).hexdigest()}"


class PreprocessingPipeline:
    """Runs the full Phase 2 preprocessing pipeline on an uploaded drawing."""

    def run(self, contents: bytes, content_type: str) -> PreprocessingResult:
        key = _cache_key(contents, content_type)
        with _cache_lock:
            cached = _cache.get(key)
            if cached is not None:
                _cache.move_to_end(key)
                logger.info("Preprocessing cache hit (%s...)", key[:16])
                return cached

        start = time.perf_counter()
        steps: list[str] = []

        image = loader.load_as_bgr_image(contents, content_type)
        original_h, original_w = image.shape[:2]
        steps.append("load")

        deskewed, skew_angle = deskew.deskew(image)
        steps.append("deskew")

        denoised = denoise.denoise(deskewed)
        steps.append("denoise")

        resized, scale_factor = resize.resize(denoised)
        steps.append("resize")

        enhanced = contrast.enhance_contrast(resized)
        steps.append("contrast_enhancement")

        binarized = threshold.adaptive_threshold(enhanced)
        steps.append("adaptive_threshold")

        elapsed_ms = (time.perf_counter() - start) * 1000
        processed_h, processed_w = binarized.shape[:2]

        logger.info(
            "Preprocessing pipeline complete in %.1fms: %dx%d -> %dx%d, skew=%.2fdeg",
            elapsed_ms, original_w, original_h, processed_w, processed_h, skew_angle,
        )

        result = PreprocessingResult(
            processed_image=binarized,
            preview_image=enhanced,
            original_width=original_w,
            original_height=original_h,
            processed_width=processed_w,
            processed_height=processed_h,
            skew_angle_corrected_degrees=round(skew_angle, 2),
            resize_scale_factor=round(scale_factor, 4),
            steps_applied=steps,
            processing_time_ms=round(elapsed_ms, 1),
        )

        with _cache_lock:
            _cache[key] = result
            _cache.move_to_end(key)
            while len(_cache) > _CACHE_MAX_ENTRIES:
                _cache.popitem(last=False)

        return result


def encode_png_base64(image: np.ndarray) -> str:
    """Encode a numpy image (grayscale or BGR) as a base64 PNG data string."""
    success, buffer = cv2.imencode(".png", image)
    if not success:
        raise RuntimeError("Failed to encode processed image as PNG")
    return base64.b64encode(buffer.tobytes()).decode("ascii")
