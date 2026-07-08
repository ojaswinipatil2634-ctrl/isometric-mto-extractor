"""
Gemini Vision integration.

Gemini is used ONLY at runtime to analyze an uploaded isometric drawing —
never for code generation. This module isolates all model-call and
prompt-engineering concerns so the rest of the pipeline never imports
`google.generativeai` directly.
"""
from __future__ import annotations

import json
import logging
import pprint

from app.config import Settings
from app.schemas.mto import ExtractionRaw

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are an expert piping engineer reading an ISOMETRIC DRAWING.

Analyze the attached image and extract structured data. Respond with
STRICT JSON ONLY — no markdown fences, no commentary, no prose before or
after the JSON object.

Return an object with EXACTLY this shape:

{
  "metadata": {
    "drawing_number": string,
    "revision": string,
    "line_number": string,
    "material_class": string,
    "service": string,
    "nps": string
  },
  "pipe_segments": [ { "nps": string, "length_m": number, "schedule": string } ],
  "fittings": [ { "type": "elbow"|"tee"|"reducer"|"flange"|"valve", "nps": string, "quantity": integer, "rating": string|null } ],
  "welds": [ { "weld_type": string, "quantity": integer } ],
  "supports": [ { "support_type": string, "quantity": integer } ],
  "confidence": number between 0 and 1
}

Rules:

- NEVER return null for any field.
- Every key in the JSON must always exist.
- If you cannot determine a value, use:
  - "UNKNOWN" for strings
  - 0 for numbers
  - [] for arrays
- Do not omit any keys.
- Do not invent additional keys.
- drawing_number, revision, line_number, material_class, service and nps must always be strings.
- rating may be null ONLY if the fitting is not a flange or valve and no pressure rating can be determined.
- Use your best engineering estimate whenever possible instead of UNKNOWN.
- Lengths must always be in meters.
- Do NOT include gaskets or bolt sets.
- Return ONLY valid JSON.
"""


class GeminiExtractionError(Exception):
    pass


def extract_from_image(png_bytes: bytes, settings: Settings) -> ExtractionRaw:
    """Call Gemini Vision on the given image and parse a validated result.

    Raises GeminiExtractionError on any failure (network, parsing, or
    schema validation) so the caller can decide whether to fall back.
    """
    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise GeminiExtractionError(
            "google-generativeai package not installed"
        ) from exc

    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.model_name)
        response = model.generate_content(
            [
                EXTRACTION_PROMPT,
                {"mime_type": "image/png", "data": png_bytes},
            ],
            generation_config={"response_mime_type": "application/json"},
        )
        raw_text = response.text
    except Exception as exc:
        logger.exception("Gemini API call failed")
        raise GeminiExtractionError(str(exc)) from exc

    try:
        payload = json.loads(raw_text)
        
        print("\n========== GEMINI RESPONSE ==========")
        pprint.pprint(payload)
        print("=====================================\n")
    except json.JSONDecodeError as exc:
        logger.error("Gemini returned non-JSON payload: %s", raw_text[:500])
        raise GeminiExtractionError(f"Invalid JSON from model: {exc}") from exc

    try:
                # Fill missing metadata values before validation
        metadata = payload.setdefault("metadata", {})

        metadata["drawing_number"] = metadata.get("drawing_number") or "UNKNOWN"
        metadata["revision"] = metadata.get("revision") or "A"
        metadata["line_number"] = metadata.get("line_number") or "UNKNOWN"
        metadata["material_class"] = metadata.get("material_class") or "UNKNOWN"
        metadata["service"] = metadata.get("service") or "UNKNOWN"
        metadata["nps"] = metadata.get("nps") or "UNKNOWN"

        return ExtractionRaw.model_validate(payload)
    except Exception as exc:
        logger.error("Gemini payload failed schema validation: %s", payload)
        raise GeminiExtractionError(f"Schema validation failed: {exc}") from exc
