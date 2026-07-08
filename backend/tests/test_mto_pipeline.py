from app.core.errors import OcrUnavailableError
from app.services.business_rules.hardware_generator import HardwareLineItem
from app.services.business_rules.pipeline import BusinessRulesResult
from app.services.graph_construction.analysis import GraphAnalysis
from app.services.graph_construction.pipeline import GraphConstructionResult
from app.services.mto.pipeline import MTOExtractionPipeline
from app.services.ocr.field_extractor import ExtractedFields, FieldValue
from app.services.ocr.pipeline import OcrResult
from app.services.vision_extraction.pipeline import VisionExtractionResult
from tests.fixtures import encode_png_bytes, make_l_shaped_pipe_drawing


class _StubOcrPipeline:
    def __init__(self, result=None, raises=None):
        self._result = result
        self._raises = raises

    def run(self, contents, content_type):
        if self._raises:
            raise self._raises
        return self._result


class _StubVisionPipeline:
    """Returns empty metadata/items so OCR-focused tests aren't coupled to
    the (mock or live) vision extraction path's own drawing metadata."""

    def __init__(self, result: VisionExtractionResult | None = None):
        self._result = result or VisionExtractionResult()

    def run(self, contents, content_type, filename="unknown"):
        return self._result


class _StubGraphPipeline:
    def __init__(self, result: GraphConstructionResult):
        self._result = result

    def run(self, contents, content_type):
        return self._result


class _StubBusinessRulesPipeline:
    def __init__(self, result: BusinessRulesResult):
        self._result = result

    def run(self, contents, content_type):
        return self._result


def _field(value: str | None) -> FieldValue:
    return FieldValue(value=value, confidence=0.9 if value else None, source_text=value, bbox=None)


PNG_BYTES = encode_png_bytes(make_l_shaped_pipe_drawing())


def test_pipeline_maps_ocr_fields_and_graph_summary():
    ocr_result = OcrResult(
        engine_available=True,
        extracted_fields=ExtractedFields(
            drawing_number=_field("MTO-001"),
            revision=_field("A"),
            line_number=_field('6"-CS-1001-A1A'),
            service=_field("COOLING WATER"),
            material_class=_field("150"),
            nps=[_field("6")],
            dimensions=[],
        ),
        warnings=[],
    )
    graph_result = GraphConstructionResult(
        node_positions={0: (0.0, 0.0), 1: (1.0, 1.0), 2: (2.0, 2.0), 3: (3.0, 3.0)},
        analysis=GraphAnalysis(branch_node_ids=[1], dead_end_node_ids=[0, 2, 3], loops=[], is_fully_connected=True),
        edges=[(0, 1, {}), (1, 2, {}), (1, 3, {})],
    )
    business_rules_result = BusinessRulesResult(
        hardware=[HardwareLineItem("gasket", 0, 1, '6" NPS', False)],
    )

    pipeline = MTOExtractionPipeline(
        ocr_pipeline=_StubOcrPipeline(ocr_result),
        graph_pipeline=_StubGraphPipeline(graph_result),
        business_rules_pipeline=_StubBusinessRulesPipeline(business_rules_result),
        vision_pipeline=_StubVisionPipeline(),
    )

    result = pipeline.run(PNG_BYTES, "image/png")

    assert result.drawing_number == "MTO-001"
    assert result.revision == "A"
    assert result.service == "COOLING WATER"
    assert result.nps_values == ["6"]
    assert result.node_count == 4
    assert result.edge_count == 3
    assert result.branch_count == 1
    assert result.dead_end_count == 3
    assert result.business_rules.hardware[0].item_type == "gasket"


def test_pipeline_degrades_gracefully_when_ocr_unavailable():
    graph_result = GraphConstructionResult()
    business_rules_result = BusinessRulesResult()

    pipeline = MTOExtractionPipeline(
        ocr_pipeline=_StubOcrPipeline(raises=OcrUnavailableError("unavailable")),
        graph_pipeline=_StubGraphPipeline(graph_result),
        business_rules_pipeline=_StubBusinessRulesPipeline(business_rules_result),
        vision_pipeline=_StubVisionPipeline(),
    )

    result = pipeline.run(PNG_BYTES, "image/png")

    # With OCR unavailable and the (stubbed) vision pipeline returning no
    # metadata either, drawing_number has no source left to fall back to.
    assert result.drawing_number is None
    assert any("OCR unavailable" in w for w in result.warnings)


def test_pipeline_does_not_duplicate_identical_warnings():
    graph_result = GraphConstructionResult(warnings=["shared warning"])
    business_rules_result = BusinessRulesResult(warnings=["shared warning", "unique warning"])

    pipeline = MTOExtractionPipeline(
        ocr_pipeline=_StubOcrPipeline(OcrResult(engine_available=True, warnings=[])),
        graph_pipeline=_StubGraphPipeline(graph_result),
        business_rules_pipeline=_StubBusinessRulesPipeline(business_rules_result),
    )

    result = pipeline.run(PNG_BYTES, "image/png")

    assert result.warnings.count("shared warning") == 1
    assert "unique warning" in result.warnings


def test_real_l_shaped_drawing_end_to_end():
    """Runs the actual OCR/graph/business-rules pipelines (not stubs)
    against a real synthetic drawing to confirm the full composition
    works, not just the field-mapping logic in isolation."""
    result = MTOExtractionPipeline().run(PNG_BYTES, "image/png")

    assert result.node_count == 3
    assert result.edge_count == 2
    assert result.processing_time_ms > 0
