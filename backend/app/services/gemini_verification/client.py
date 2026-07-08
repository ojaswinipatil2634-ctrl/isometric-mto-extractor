"""
Gemini verification client - Phase 9.

Talks to Google's Generative Language API (Gemini) directly over HTTPS
via httpx - no SDK dependency, so the install footprint doesn't grow at
all (httpx is already a dependency for testing). If the API key is
missing, or the request fails for any reason (network, timeout, bad
response, malformed JSON), this returns a clean "unavailable" result
rather than raising - per project rules, verification must never crash
the request and must never be presented as if it ran when it didn't.

Per the project-wide Gemini rule: Gemini NEVER performs extraction - it
only reviews what OCR/detection/graph/business-rules already produced.
The system instruction below is deliberately written to make review the
only thing the model is asked to do, and the response schema only
allows reviewer-shaped output (corrections, missing items, OCR flags) -
never raw extracted fields, never a regenerated extraction.
"""
import base64
import json
import logging
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

_SYSTEM_INSTRUCTION = (
    "You are reviewing an already-completed piping isometric drawing extraction. "
    "You are NOT extracting anything yourself - OCR, symbol detection, pipe/graph "
    "construction, and business rules have already run, and their output is given "
    "to you below alongside the original drawing image.\n\n"
    "Your ONLY job is to review that output against the image and respond with a "
    "JSON object with exactly these three keys:\n"
    '{"corrections": [string, ...], "missing_items": [string, ...], "ocr_flags": [string, ...]}\n\n'
    "- \"corrections\": specific inaccuracies you see in the extracted data compared to "
    "what the image actually shows.\n"
    "- \"missing_items\": fittings, symbols, or text visible in the image that don't appear "
    "anywhere in the extracted data.\n"
    "- \"ocr_flags\": specific OCR text values that look wrong given what's visible in the "
    "image.\n\n"
    "Do not invent a full new extraction, do not restate data that already looks correct, "
    "and use an empty list for any category with nothing to report. "
    "Respond with ONLY the JSON object and nothing else."
)


@dataclass
class GeminiReview:
    available: bool
    corrections: list[str]
    missing_items: list[str]
    ocr_flags: list[str]
    error: str | None = None


class GeminiVerificationClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self._model = model or settings.GEMINI_MODEL
        self._timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.GEMINI_TIMEOUT_SECONDS

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def review(self, image_bytes: bytes, context: dict) -> GeminiReview:
        """Review the drawing + already-extracted context. Never raises."""
        if not self.is_configured:
            return GeminiReview(
                available=False, corrections=[], missing_items=[], ocr_flags=[],
                error="GEMINI_API_KEY is not configured.",
            )

        try:
            image_b64 = base64.b64encode(image_bytes).decode("ascii")
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {"text": _SYSTEM_INSTRUCTION},
                            {"text": "Already-extracted data summary:\n" + json.dumps(context, indent=2)},
                            {"inline_data": {"mime_type": "image/png", "data": image_b64}},
                        ],
                    }
                ],
                "generationConfig": {"responseMimeType": "application/json"},
            }
            url = f"{_API_BASE}/{self._model}:generateContent"

            response = httpx.post(url, params={"key": self._api_key}, json=payload, timeout=self._timeout_seconds)
            response.raise_for_status()

            body = response.json()
            text = body["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(text)

            return GeminiReview(
                available=True,
                corrections=[str(c) for c in parsed.get("corrections", [])],
                missing_items=[str(m) for m in parsed.get("missing_items", [])],
                ocr_flags=[str(f) for f in parsed.get("ocr_flags", [])],
            )
        except Exception as exc:
            reason = str(exc) or exc.__class__.__name__
            logger.warning("Gemini verification unavailable: %s", reason)
            return GeminiReview(
                available=False, corrections=[], missing_items=[], ocr_flags=[], error=reason
            )
