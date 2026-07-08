from app.services.business_rules.duplicate_detection import DuplicateFittingViolation
from app.services.business_rules.hardware_generator import HardwareLineItem
from app.services.business_rules.connectivity_rules import RuleViolation
from app.services.business_rules.pipeline import BusinessRulesResult
from app.services.mto.persistence_service import build_run_record
from app.services.mto.pipeline import MTOExtractionResult


def test_build_run_record_maps_all_fields():
    business_rules = BusinessRulesResult(
        hardware=[HardwareLineItem("gasket", 1, 1, '6" NPS', False)],
        violations=[RuleViolation("MISSING_FITTING", "warning", "some message", [2])],
        duplicate_fittings=[DuplicateFittingViolation("flange", (0, 1), 0.9, (0, 0, 10, 10), (1, 1, 11, 11))],
        steps_applied=["graph_construction"],
        warnings=["some warning"],
        processing_time_ms=12.3,
    )
    result = MTOExtractionResult(
        drawing_number="MTO-001",
        revision="A",
        line_number='6"-CS-1001-A1A',
        service="COOLING WATER",
        material_class="150",
        nps_values=["6"],
        node_count=4,
        edge_count=3,
        branch_count=1,
        dead_end_count=3,
        loop_count=0,
        is_fully_connected=True,
        business_rules=business_rules,
        warnings=["overall warning"],
        processing_time_ms=99.9,
    )

    record = build_run_record("drawing.png", result)

    assert record.filename == "drawing.png"
    assert record.drawing_number == "MTO-001"
    assert record.revision == "A"
    assert record.nps_values == ["6"]
    assert record.node_count == 4
    assert record.branch_count == 1
    assert record.is_fully_connected is True
    assert record.hardware == [
        {"item_type": "gasket", "node_id": 1, "quantity": 1, "size": '6" NPS', "is_estimated": False}
    ]
    assert record.violations == [
        {"rule_code": "MISSING_FITTING", "severity": "warning", "message": "some message", "node_ids": [2]}
    ]
    assert record.duplicate_fitting_count == 1
    assert record.warnings == ["overall warning"]
    assert record.processing_time_ms == 99.9


def test_build_run_record_handles_empty_business_rules():
    result = MTOExtractionResult()

    record = build_run_record("blank.png", result)

    assert record.hardware == []
    assert record.violations == []
    assert record.duplicate_fitting_count == 0
