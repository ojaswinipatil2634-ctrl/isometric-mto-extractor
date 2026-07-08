"""
Rule-based extraction of MTO title-block fields from raw OCR text.

Per the project's Gemini rule, extraction must never come from an LLM -
this is pure regex/heuristics over whatever PaddleOCR actually detected.
Gemini (Phase 9) only reviews the result afterward; it never produces it.

Two matching strategies are used, in order:

1. Single-block match: the label and value appear together in one OCR
   text line, e.g. "DWG NO. MTO-1234-01" or "LINE NO. 6"-P-1001-A1A".
   This is the common case for isometric drawings where the title block
   is laid out as free text rather than a ruled table.

2. Adjacent-block fallback: the label and value were detected as two
   separate OCR text regions (common when a title block is a ruled
   table and each cell becomes its own region), e.g. one box containing
   just "DWG NO." and the next box (in reading order) containing just
   "MTO-1234-01". If strategy 1 finds nothing, we look for a label-only
   block and take the very next block as its value.

Every returned field carries the OCR confidence and bounding box of the
block(s) it came from, so the frontend can show provenance and the
confidence engine (a later phase) has something concrete to work with.
"""
import re
from dataclasses import dataclass
from typing import Protocol


class TextBlockLike(Protocol):
    """Structural type - anything with .text/.confidence/.bbox works.
    Keeps this module independent of the OCR pipeline's concrete types
    so it can be unit tested with plain test doubles."""

    text: str
    confidence: float
    bbox: list[list[float]]


@dataclass
class FieldValue:
    value: str | None
    confidence: float | None
    source_text: str | None
    bbox: list[list[float]] | None


@dataclass
class ExtractedFields:
    drawing_number: FieldValue
    revision: FieldValue
    line_number: FieldValue
    service: FieldValue
    material_class: FieldValue
    nps: list[FieldValue]
    dimensions: list[FieldValue]


def _empty_field() -> FieldValue:
    return FieldValue(value=None, confidence=None, source_text=None, bbox=None)


# --- Single-block "LABEL ... VALUE" patterns ----------------------------
# Each pattern has exactly one capturing group holding the value (or two
# alternates or'd together, handled by `_first_group`).

_DRAWING_NUMBER_RE = re.compile(
    r"DRAWING\s*(?:NO|NUMBER)?\.?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/]{2,})"
    r"|DWG\.?\s*(?:NO|NUMBER)?\.?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/]{2,})",
    re.IGNORECASE,
)
_REVISION_RE = re.compile(r"\bREV(?:ISION)?\.?\s*[:\-]?\s*([A-Z0-9]{1,3})\b", re.IGNORECASE)
_LINE_NUMBER_RE = re.compile(
    r"LINE\s*(?:NO\.?|NUMBER)?\s*[:\-]?\s*(\d{1,3}\s*[\"']?\s*-\s*[A-Z0-9\-]+)",
    re.IGNORECASE,
)
_SERVICE_RE = re.compile(r"\bSERVICE\s*[:\-]?\s*([A-Z][A-Z0-9 /]{2,40}?)(?:\s{2,}|$)", re.IGNORECASE)
_MATERIAL_CLASS_RE = re.compile(
    r"(?:MATERIAL\s*)?CLASS\s*[:\-]?\s*([A-Z0-9]{1,10})"
    r"|\bMOC\s*[:\-]?\s*([A-Z0-9]{1,10})",
    re.IGNORECASE,
)
_NPS_RE = re.compile(
    r"\bNPS\s*[:\-]?\s*(\d{1,3}(?:\.\d+)?)"
    r"|\bDN\s*(\d{2,4})\b"
    r"|\b(\d{1,2}(?:\s?\d/\d)?)\s*(?:\"|IN\b|INCH\b)",
    re.IGNORECASE,
)
_DIMENSION_RE = re.compile(
    r"\b(\d+(?:\.\d+)?\s?(?:MM|CM|FT))\b"
    r"|\b(\d+'\s?-?\s?\d+(?:\.\d+)?\"?)"
    r"|\bR\s?=\s?(\d+(?:\.\d+)?)\s?(?:MM|IN)?\b",
    re.IGNORECASE,
)

# --- Label-only patterns for the adjacent-block fallback ----------------

_LABEL_ONLY_PATTERNS: dict[str, re.Pattern] = {
    "drawing_number": re.compile(r"^\s*(?:DRAWING|DWG)\.?\s*(?:NO|NUMBER)?\.?\s*[:\-]?\s*$", re.IGNORECASE),
    "revision": re.compile(r"^\s*REV(?:ISION)?\.?\s*[:\-]?\s*$", re.IGNORECASE),
    "line_number": re.compile(r"^\s*LINE\s*(?:NO\.?|NUMBER)?\.?\s*[:\-]?\s*$", re.IGNORECASE),
    "service": re.compile(r"^\s*SERVICE\s*[:\-]?\s*$", re.IGNORECASE),
    "material_class": re.compile(
        r"^\s*(?:MATERIAL\s*)?CLASS\s*[:\-]?\s*$|^\s*MOC\s*[:\-]?\s*$", re.IGNORECASE
    ),
}


def extract_fields(blocks: list[TextBlockLike]) -> ExtractedFields:
    """Run every field rule against the full set of OCR text blocks."""
    drawing_number = _match_single(blocks, _DRAWING_NUMBER_RE)
    revision = _match_single(blocks, _REVISION_RE)
    line_number = _match_single(blocks, _LINE_NUMBER_RE)
    service = _match_single(blocks, _SERVICE_RE)
    material_class = _match_single(blocks, _MATERIAL_CLASS_RE)
    nps = _match_all(blocks, _NPS_RE)
    dimensions = _match_all(blocks, _DIMENSION_RE)

    if drawing_number.value is None:
        drawing_number = _match_adjacent(blocks, _LABEL_ONLY_PATTERNS["drawing_number"])
    if revision.value is None:
        revision = _match_adjacent(blocks, _LABEL_ONLY_PATTERNS["revision"])
    if line_number.value is None:
        line_number = _match_adjacent(blocks, _LABEL_ONLY_PATTERNS["line_number"])
    if service.value is None:
        service = _match_adjacent(blocks, _LABEL_ONLY_PATTERNS["service"])
    if material_class.value is None:
        material_class = _match_adjacent(blocks, _LABEL_ONLY_PATTERNS["material_class"])

    return ExtractedFields(
        drawing_number=drawing_number,
        revision=revision,
        line_number=line_number,
        service=service,
        material_class=material_class,
        nps=nps,
        dimensions=dimensions,
    )


def _first_group(match: re.Match) -> str:
    return next(g for g in match.groups() if g is not None).strip()


def _match_single(blocks: list[TextBlockLike], pattern: re.Pattern) -> FieldValue:
    for b in blocks:
        m = pattern.search(b.text)
        if m:
            return FieldValue(value=_first_group(m), confidence=b.confidence, source_text=b.text, bbox=b.bbox)
    return _empty_field()


def _match_all(blocks: list[TextBlockLike], pattern: re.Pattern) -> list[FieldValue]:
    results: list[FieldValue] = []
    seen: set[str] = set()
    for b in blocks:
        for m in pattern.finditer(b.text):
            value = _first_group(m)
            key = value.upper()
            if key in seen:
                continue
            seen.add(key)
            results.append(FieldValue(value=value, confidence=b.confidence, source_text=b.text, bbox=b.bbox))
    return results


def _match_adjacent(blocks: list[TextBlockLike], label_pattern: re.Pattern) -> FieldValue:
    for i, b in enumerate(blocks):
        if label_pattern.match(b.text.strip()) and i + 1 < len(blocks):
            nxt = blocks[i + 1]
            return FieldValue(
                value=nxt.text.strip(),
                confidence=nxt.confidence,
                source_text=f"{b.text} | {nxt.text}",
                bbox=nxt.bbox,
            )
    return _empty_field()
