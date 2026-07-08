"""
Converts an in-memory `MTOExtractionResult` (pipeline output) into an
(unsaved) `MTOExtractionRun` ORM row, ready for the repository to
persist. Kept separate from the pipeline and the repository so neither
has to know about the other's shape.
"""
from app.models.mto_run import MTOExtractionRun
from app.services.mto.pipeline import MTOExtractionResult


def _hardware_to_dicts(hardware) -> list[dict]:
    return [
        {
            "item_type": item.item_type,
            "node_id": item.node_id,
            "quantity": item.quantity,
            "size": item.size,
            "is_estimated": item.is_estimated,
        }
        for item in hardware
    ]


def _items_to_dicts(items) -> list[dict]:
    return [item.model_dump() for item in items]


def _violations_to_dicts(violations) -> list[dict]:
    return [
        {
            "rule_code": v.rule_code,
            "severity": v.severity,
            "message": v.message,
            "node_ids": v.node_ids,
        }
        for v in violations
    ]


def build_run_record(filename: str, result: MTOExtractionResult) -> MTOExtractionRun:
    br = result.business_rules
    return MTOExtractionRun(
        filename=filename,
        drawing_number=result.drawing_number,
        revision=result.revision,
        line_number=result.line_number,
        service=result.service,
        material_class=result.material_class,
        nps_values=result.nps_values,
        node_count=result.node_count,
        edge_count=result.edge_count,
        branch_count=result.branch_count,
        dead_end_count=result.dead_end_count,
        loop_count=result.loop_count,
        is_fully_connected=result.is_fully_connected,
        hardware=_hardware_to_dicts(br.hardware),
        violations=_violations_to_dicts(br.violations),
        duplicate_fitting_count=len(br.duplicate_fittings),
        items=_items_to_dicts(result.items),
        mto_summary=result.mto_summary,
        extraction_source=result.extraction_source,
        used_mock=result.used_mock,
        symbol_detection_enabled=result.symbol_detection_enabled,
        symbol_detection_reason=result.symbol_detection_reason,
        warnings=result.warnings,
        processing_time_ms=result.processing_time_ms,
    )
