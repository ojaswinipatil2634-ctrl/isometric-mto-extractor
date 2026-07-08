"""
Unit tests for app.services.ocr.field_extractor.

These are pure regex/heuristic tests - no PaddleOCR involved at all -
using plain test-double text blocks that mimic what PaddleOCR's `.ocr()`
call would hand back (text + confidence + a 4-point bbox).
"""
from dataclasses import dataclass

from app.services.ocr import field_extractor


@dataclass
class FakeBlock:
    text: str
    confidence: float
    bbox: list


def _bbox(x=0, y=0):
    return [[x, y], [x + 100, y], [x + 100, y + 20], [x, y + 20]]


def test_extracts_drawing_number_and_revision_from_single_line():
    blocks = [
        FakeBlock("DWG NO. MTO-1234-01  REV. B", 0.97, _bbox()),
    ]

    result = field_extractor.extract_fields(blocks)

    assert result.drawing_number.value == "MTO-1234-01"
    assert result.drawing_number.confidence == 0.97
    assert result.revision.value == "B"


def test_extracts_line_number():
    blocks = [FakeBlock('LINE NO. 6"-P-1001-A1A', 0.9, _bbox())]

    result = field_extractor.extract_fields(blocks)

    assert result.line_number.value == '6"-P-1001-A1A'


def test_extracts_service_and_material_class():
    blocks = [
        FakeBlock("SERVICE: COOLING WATER", 0.88, _bbox()),
        FakeBlock("MATERIAL CLASS: A1A", 0.91, _bbox(y=30)),
    ]

    result = field_extractor.extract_fields(blocks)

    assert result.service.value.strip() == "COOLING WATER"
    assert result.material_class.value == "A1A"


def test_extracts_multiple_nps_and_dimension_values():
    blocks = [
        FakeBlock('PIPE SIZE 6" REDUCED TO 4"', 0.85, _bbox()),
        FakeBlock("OVERALL LENGTH 1500MM", 0.8, _bbox(y=30)),
        FakeBlock("R=250MM", 0.8, _bbox(y=60)),
    ]

    result = field_extractor.extract_fields(blocks)

    nps_values = {f.value for f in result.nps}
    assert "6" in nps_values
    assert "4" in nps_values

    dim_values = {f.value for f in result.dimensions}
    assert "1500MM" in dim_values


def test_adjacent_block_fallback_when_label_and_value_are_split():
    blocks = [
        FakeBlock("DWG NO.", 0.9, _bbox()),
        FakeBlock("MTO-9999-02", 0.93, _bbox(y=25)),
        FakeBlock("REV.", 0.9, _bbox(y=50)),
        FakeBlock("C", 0.95, _bbox(y=75)),
    ]

    result = field_extractor.extract_fields(blocks)

    assert result.drawing_number.value == "MTO-9999-02"
    assert result.drawing_number.source_text == "DWG NO. | MTO-9999-02"
    assert result.revision.value == "C"


def test_missing_fields_return_none_without_fabrication():
    blocks = [FakeBlock("SOME UNRELATED TEXT", 0.5, _bbox())]

    result = field_extractor.extract_fields(blocks)

    assert result.drawing_number.value is None
    assert result.drawing_number.confidence is None
    assert result.revision.value is None
    assert result.nps == []
    assert result.dimensions == []


def test_empty_input_returns_all_empty_fields():
    result = field_extractor.extract_fields([])

    assert result.drawing_number.value is None
    assert result.line_number.value is None
    assert result.service.value is None
    assert result.material_class.value is None
    assert result.nps == []
    assert result.dimensions == []
