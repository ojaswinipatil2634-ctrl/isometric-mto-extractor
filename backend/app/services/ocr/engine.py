"""
PaddleOCR engine wrapper.

`paddleocr`/`paddlepaddle` are heavy, platform-sensitive dependencies
(large binary wheels, first-run model download, occasional missing
system libraries on some Windows installs). Per project rules, if OCR
is unavailable for any reason we must return a structured error and
never fabricate an OCR result.

To make that possible, this module is the *only* place in the app that
ever imports `paddleocr`, and it does so lazily (inside a function, not
at module import time). That means:

    - the rest of the app can import this module freely without paying
      the cost of loading PaddleOCR until it's actually used
    - if paddleocr/paddlepaddle aren't installed, or the engine fails to
      initialize (no internet to fetch model weights on first run,
      unsupported platform, missing system libraries, etc.), the
      failure is caught here and turned into a single well-known
      `OcrUnavailableError` instead of crashing the process
    - the failure is cached, so repeated requests don't keep retrying a
      slow, doomed initialization on every call
"""
import logging
import threading
from typing import Protocol

from app.core.config import get_settings
from app.core.errors import OcrUnavailableError

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_engine_instance: "PaddleOcrEngine | None" = None
_engine_init_failed_reason: str | None = None


class RawOcrLine:
    """One recognized text line, in the engine's raw reading order."""

    __slots__ = ("text", "confidence", "bbox")

    def __init__(self, text: str, confidence: float, bbox: list[list[float]]) -> None:
        self.text = text
        self.confidence = confidence
        self.bbox = bbox

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"RawOcrLine(text={self.text!r}, confidence={self.confidence:.3f})"


class OcrEngineProtocol(Protocol):
    """Interface the rest of the app depends on, so tests can substitute
    a fake engine without touching real PaddleOCR."""

    def recognize(self, image) -> list[RawOcrLine]: ...


class PaddleOcrEngine:
    """Thin adapter around PaddleOCR's `.ocr()` call."""

    def __init__(self, ocr_instance) -> None:
        self._ocr = ocr_instance

    def recognize(self, image) -> list[RawOcrLine]:
        """
        image: BGR numpy array (as produced by the preprocessing pipeline).
        Returns one RawOcrLine per detected text line.

        Raises:
            OcrUnavailableError: if the underlying engine raises while
                processing this specific image (corrupt state, out of
                memory, etc). This is deliberately a *different* error
                path than initialization failure, but the same error
                type, since both mean "no result is available" and
                neither should be papered over with a fabricated one.
        """
        try:
            raw_result = self._ocr.ocr(image, cls=True)
        except Exception as exc:
            raise OcrUnavailableError(
                "PaddleOCR failed while processing the image.",
                details={"reason": str(exc)},
            ) from exc

        lines: list[RawOcrLine] = []

        # PaddleOCR 2.x's `.ocr()` returns a list with one entry per input
        # image: [[ [bbox, (text, confidence)], ... ]]. We only ever pass
        # a single image, so we only look at raw_result[0]. It can be
        # None if no text was detected at all - that's a valid, non-error
        # outcome (an empty drawing region), not something to raise on.
        if not raw_result or raw_result[0] is None:
            return lines

        for bbox, (text, confidence) in raw_result[0]:
            lines.append(RawOcrLine(text=text, confidence=float(confidence), bbox=bbox))
        return lines


def get_ocr_engine() -> "PaddleOcrEngine":
    """
    Lazily builds and caches a single PaddleOCR instance for the process.

    Raises:
        OcrUnavailableError: if paddleocr/paddlepaddle are not installed,
            or the engine fails to initialize. Never fabricates a result;
            the caller is expected to surface this as a clean 503.
    """
    global _engine_instance, _engine_init_failed_reason

    if _engine_instance is not None:
        return _engine_instance

    if _engine_init_failed_reason is not None:
        raise OcrUnavailableError("OCR engine is unavailable.", details={"reason": _engine_init_failed_reason})

    with _lock:
        # Re-check inside the lock - another thread may have already
        # initialized (or failed to initialize) the engine while we
        # were waiting for it.
        if _engine_instance is not None:
            return _engine_instance
        if _engine_init_failed_reason is not None:
            raise OcrUnavailableError(
                "OCR engine is unavailable.", details={"reason": _engine_init_failed_reason}
            )

        settings = get_settings()

        try:
            from paddleocr import PaddleOCR  # deferred import - see module docstring
        except Exception as exc:
            _engine_init_failed_reason = (
                "paddleocr/paddlepaddle is not installed or failed to import "
                f"({type(exc).__name__}: {exc})"
            )
            logger.error("OCR engine unavailable: %s", _engine_init_failed_reason)
            raise OcrUnavailableError(
                "OCR engine is unavailable.", details={"reason": _engine_init_failed_reason}
            ) from exc

        try:
            ocr_instance = PaddleOCR(
                use_angle_cls=settings.OCR_USE_ANGLE_CLS,
                lang=settings.OCR_LANG,
                use_gpu=settings.OCR_USE_GPU,
                show_log=False,
            )
        except Exception as exc:
            _engine_init_failed_reason = f"PaddleOCR failed to initialize ({type(exc).__name__}: {exc})"
            logger.error("OCR engine unavailable: %s", _engine_init_failed_reason)
            raise OcrUnavailableError(
                "OCR engine is unavailable.", details={"reason": _engine_init_failed_reason}
            ) from exc

        _engine_instance = PaddleOcrEngine(ocr_instance)
        logger.info(
            "PaddleOCR engine initialized (lang=%s, use_gpu=%s, use_angle_cls=%s)",
            settings.OCR_LANG, settings.OCR_USE_GPU, settings.OCR_USE_ANGLE_CLS,
        )
        return _engine_instance


def reset_engine_cache_for_tests() -> None:
    """Test-only helper: clears the cached engine/failure so each test
    can exercise initialization behavior independently."""
    global _engine_instance, _engine_init_failed_reason
    with _lock:
        _engine_instance = None
        _engine_init_failed_reason = None
