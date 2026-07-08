import pytest
from pydantic import ValidationError

from app.pipeline.business_logic import build_mto
from app.schemas.mto import ComponentType, DrawingMetadata, ExtractionRaw, Fitting, PipeSegment


def _base_metadata() -> DrawingMetadata:
    return DrawingMetadata(
        drawing_number="D-100",
        revision="A",
        line_number="6\"-CW-1",
        material_class="A106-B",
        service="Cooling Water",
        nps="6\"",
    )


def test_gasket_and_boltset_derivation_matches_flange_count():
    extraction = ExtractionRaw(
        metadata=_base_metadata(),
        pipe_segments=[PipeSegment(nps="6\"", length_m=10.0)],
        fittings=[
            Fitting(type=ComponentType.FLANGE, nps="6\"", quantity=4, rating="150#"),
            Fitting(type=ComponentType.VALVE, nps="6\"", quantity=1, rating="150#"),
        ],
    )
    result = build_mto(extraction, mock_mode=True)

    assert result.summary.total_flanged_joints == 4
    assert result.summary.total_gaskets == 4
    assert result.summary.total_bolt_sets == 4
    assert result.summary.total_valves == 1

    gasket_items = [li for li in result.line_items if li.component == "Gasket"]
    assert len(gasket_items) == 1
    assert gasket_items[0].quantity == 4


def test_pipe_lengths_are_grouped_by_nps():
    extraction = ExtractionRaw(
        metadata=_base_metadata(),
        pipe_segments=[
            PipeSegment(nps="6\"", length_m=5.0),
            PipeSegment(nps="6\"", length_m=3.0),
            PipeSegment(nps="4\"", length_m=2.0),
        ],
    )
    result = build_mto(extraction, mock_mode=True)
    pipe_items = {li.nps: li.quantity for li in result.line_items if li.component == "Pipe"}
    assert pipe_items["6\""] == 8.0
    assert pipe_items["4\""] == 2.0


def test_negative_quantity_rejected_by_schema():
    with pytest.raises(ValidationError):
        Fitting(type=ComponentType.VALVE, nps="6\"", quantity=-1)


def test_no_flanges_means_no_gasket_line_item():
    extraction = ExtractionRaw(
        metadata=_base_metadata(),
        pipe_segments=[PipeSegment(nps="6\"", length_m=1.0)],
        fittings=[],
    )
    result = build_mto(extraction, mock_mode=True)
    assert result.summary.total_gaskets == 0
    assert not any(li.component == "Gasket" for li in result.line_items)
