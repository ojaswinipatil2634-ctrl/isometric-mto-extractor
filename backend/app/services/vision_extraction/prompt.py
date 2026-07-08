"""
Extraction prompt for the Gemini vision MTO pipeline.

Kept in its own module because the take-home spec explicitly asks for
the prompt to be reviewable as part of the deliverable (section 3.3:
"Prompt & schema in the repo").
"""

EXTRACTION_PROMPT = """You are an expert piping engineer reading a PIPING ISOMETRIC DRAWING.

The drawing may be a clean CAD isometric OR a hand-marked/annotated
field copy (grid paper, hand-drawn circles, arrows, highlighter marks,
stamps). Read through that noise and focus on the actual pipe routing,
line number, dimensions, and component symbols.

Analyze the attached image and extract structured data. Respond with
STRICT JSON ONLY - no markdown fences, no commentary, no prose before
or after the JSON object.

Return an object with EXACTLY this shape:

{
  "metadata": {
    "drawing_number": string|null,
    "revision": string|null,
    "line_number": string|null,
    "nps": string|null,
    "material_class": string|null,
    "service": string|null
  },
  "pipe_segments": [
    { "nps": string, "length_m": number, "schedule": string|null, "material_spec": string|null }
  ],
  "fittings": [
    {
      "category": "FITTING"|"FLANGE"|"VALVE",
      "subtype": string,
      "size_nps": string,
      "schedule_rating": string|null,
      "material_spec": string|null,
      "end_type": string|null,
      "quantity": integer,
      "rating": string|null
    }
  ],
  "overall_confidence": number between 0 and 1
}

Rules:
- "subtype" examples: "elbow_90_lr", "elbow_45_lr", "tee_equal", "tee_reducing",
  "reducer_concentric", "cap", "coupling", "weldolet", "gate_valve", "globe_valve",
  "check_valve", "ball_valve", "butterfly_valve", "weld_neck_flange", "slip_on_flange",
  "blind_flange".
- "category" must be exactly one of FITTING, FLANGE, or VALVE. Do NOT put valves or
  flanges under FITTING.
- Do NOT include gaskets or bolt sets in "fittings" - those are derived downstream,
  one per flanged joint, from the FLANGE quantities you report.
- Lengths must be in meters. Convert from feet/inches or from a marked-up scale if the
  drawing uses imperial dimensions or hand-written dimensions.
- If a metadata field is not visible or legible, use null rather than guessing a
  specific value, but still make your best engineering estimate for pipe_segments and
  fittings (a routing always implies some fittings even if symbols are hard to read),
  and lower "overall_confidence" accordingly.
- Output valid JSON and nothing else.
"""
