"""
Gemini vision extraction client.

Talks to Google's Generative Language API directly over HTTPS via
httpx, same approach already used by `gemini_verification/client.py`
(no extra SDK dependency needed). If the API key is missing, or the
request fails for any reason (network, timeout, bad response,
malformed/invalid JSON), this returns `available=False` rather than
raising - the caller (pipeline.py) falls back to the deterministic
mock extraction in that case, per the spec's graceful-degradation
requirement.

Note: this is a *different* Gemini usage than
`gemini_verification/client.py`. That module deliberately never lets
Gemini extract anything - it only reviews output already produced by
the OCR/detection/graph/business-rules stack. This client is the
actual extraction path the take-home spec asks for (section 3.3), used
because that stack's own item-producing code depends on a YOLO model
whose weights are never shipped (see schemas/vision_extraction.py for
the full explanation). Both clients are independent and can be used
together: this one produces the MTO items, the other one still
reviews the final combined result.
"""
import base64
import json
import logging

import httpx
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.vision_extraction import VisionExtractionRaw
from app.services.vision_extraction.prompt import EXTRACTION_PROMPT

logger = logging.getLogger(__name__)

_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiExtractionClient:
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

    def extract(self, png_bytes: bytes) -> tuple[VisionExtractionRaw | None, str | None]:
        """Call Gemini Vision on the given PNG image.

        Returns (result, error). `result` is None if the key is missing,
        the HTTP call failed, or the response couldn't be parsed/validated
        against `VisionExtractionRaw` - in every one of those cases `error`
        describes why, and the caller should fall back to the mock
        extraction. This method never raises.
        """
        if not self.is_configured:
            return None, "GEMINI_API_KEY is not configured."

        image_b64 = base64.b64encode(png_bytes).decode("ascii")
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": EXTRACTION_PROMPT},
                        {"inline_data": {"mime_type": "image/png", "data": image_b64}},
                    ],
                }
            ],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        url = f"{_API_BASE}/{self._model}:generateContent"

        # A single retry specifically for timeouts: free-tier Gemini
        # latency is variable on dense/hand-marked drawings, and a
        # transient slow response shouldn't immediately fall back to the
        # mock MTO when trying once more often succeeds. Non-timeout
        # errors (auth, bad request, malformed response) are not
        # retried - retrying those would just reproduce the same
        # failure and cost more time for no benefit.
        last_timeout_reason: str | None = None
        for attempt in range(2):
            try:
                response = httpx.post(
                    url, params={"key": self._api_key}, json=payload, timeout=self._timeout_seconds
                )
                response.raise_for_status()

                body = response.json()
                text = body["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text)
                return VisionExtractionRaw.model_validate(parsed), None
            except httpx.TimeoutException as exc:
                last_timeout_reason = str(exc) or exc.__class__.__name__
                logger.warning(
                    "Gemini extraction call timed out (attempt %d/2): %s", attempt + 1, last_timeout_reason
                )
                continue
            except httpx.HTTPError as exc:
                reason = str(exc) or exc.__class__.__name__
                logger.warning("Gemini extraction call failed: %s", reason)
                return None, reason
            except (KeyError, IndexError) as exc:
                reason = str(exc) or exc.__class__.__name__
                logger.warning("Gemini extraction call failed: %s", reason)
                return None, reason
            except (json.JSONDecodeError, ValidationError) as exc:
                reason = str(exc) or exc.__class__.__name__
                logger.warning("Gemini extraction returned an unparseable/invalid payload: %s", reason)
                return None, reason
            except Exception as exc:  # pragma: no cover - defensive catch-all
                reason = str(exc) or exc.__class__.__name__
                logger.warning("Gemini extraction unavailable: %s", reason)
                return None, reason

        return None, f"Gemini extraction timed out after 2 attempts: {last_timeout_reason}"
