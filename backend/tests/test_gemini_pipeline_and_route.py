import io

from app.services.gemini_verification.client import GeminiReview, GeminiVerificationClient
from app.services.gemini_verification.pipeline import GeminiVerificationPipeline
from tests.fixtures import encode_png_bytes, make_l_shaped_pipe_drawing

PNG_BYTES = encode_png_bytes(make_l_shaped_pipe_drawing())


class _StubGeminiClient:
    def __init__(self, review: GeminiReview, is_configured: bool = True):
        self._review = review
        self.is_configured = is_configured
        self.last_context: dict | None = None

    def review(self, image_bytes: bytes, context: dict) -> GeminiReview:
        self.last_context = context
        return self._review


def test_pipeline_skips_cleanly_when_not_configured():
    """The real, unconfigured GeminiVerificationClient (no API key set in
    this test environment) - genuinely exercises the 'skip cleanly'
    requirement end to end, not just via a stub."""
    pipeline = GeminiVerificationPipeline(gemini_client=GeminiVerificationClient(api_key=None))

    result = pipeline.run(PNG_BYTES, "image/png")

    assert result.available is False
    assert result.corrections == []
    assert result.missing_items == []
    assert result.ocr_flags == []
    assert any("not configured" in w for w in result.warnings)


def test_pipeline_skips_upstream_pipelines_entirely_when_not_configured():
    """Skipping should happen before any of the (expensive) upstream
    pipelines run at all - verified by injecting stubs that would raise
    if called."""

    class _ExplodingPipeline:
        def run(self, contents, content_type):
            raise AssertionError("should not have been called")

    pipeline = GeminiVerificationPipeline(
        preprocessing_pipeline=_ExplodingPipeline(),
        ocr_pipeline=_ExplodingPipeline(),
        detection_pipeline=_ExplodingPipeline(),
        graph_pipeline=_ExplodingPipeline(),
        business_rules_pipeline=_ExplodingPipeline(),
        gemini_client=GeminiVerificationClient(api_key=None),
    )

    result = pipeline.run(PNG_BYTES, "image/png")

    assert result.available is False


def test_pipeline_builds_context_and_returns_review_when_configured():
    review = GeminiReview(
        available=True,
        corrections=["revision should be B"],
        missing_items=["a support near the elbow"],
        ocr_flags=[],
    )
    stub_client = _StubGeminiClient(review)

    pipeline = GeminiVerificationPipeline(gemini_client=stub_client)
    result = pipeline.run(PNG_BYTES, "image/png")

    assert result.available is True
    assert result.corrections == ["revision should be B"]
    assert result.missing_items == ["a support near the elbow"]

    # Context passed to Gemini includes graph/business-rules summaries -
    # this is what proves the pipeline is reviewing real prior-phase
    # output, not calling Gemini blind.
    assert "graph_summary" in stub_client.last_context
    assert "business_rules_summary" in stub_client.last_context
    assert stub_client.last_context["graph_summary"]["node_count"] == 3


def test_pipeline_reports_gemini_unavailable_with_warning():
    review = GeminiReview(available=False, corrections=[], missing_items=[], ocr_flags=[], error="boom")
    stub_client = _StubGeminiClient(review)

    pipeline = GeminiVerificationPipeline(gemini_client=stub_client)
    result = pipeline.run(PNG_BYTES, "image/png")

    assert result.available is False
    assert any("boom" in w for w in result.warnings)


# --- route ---

def test_verify_endpoint_returns_expected_shape(client):
    files = {"file": ("drawing.png", io.BytesIO(PNG_BYTES), "image/png")}

    response = client.post("/api/v1/verify", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "reviewed"
    # No GEMINI_API_KEY is configured in this test environment, so this
    # exercises the real "skip cleanly" path end to end.
    assert body["available"] is False
    assert body["corrections"] == []
    assert body["missing_items"] == []
    assert body["ocr_flags"] == []
    assert any("not configured" in w for w in body["warnings"])


def test_verify_endpoint_rejects_unsupported_file_type(client):
    files = {"file": ("notes.txt", io.BytesIO(b"not a drawing"), "text/plain")}

    response = client.post("/api/v1/verify", files=files)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_FILE"
