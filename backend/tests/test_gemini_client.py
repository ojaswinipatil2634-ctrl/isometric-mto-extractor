import httpx
import pytest

from app.services.gemini_verification.client import GeminiVerificationClient


def test_not_configured_returns_unavailable_without_any_network_call():
    client = GeminiVerificationClient(api_key=None)

    assert client.is_configured is False

    review = client.review(b"", {})

    assert review.available is False
    assert "not configured" in review.error


def test_real_invalid_api_key_fails_gracefully_against_the_real_endpoint():
    """
    Genuinely calls Google's real Generative Language API with a
    deliberately invalid key (no mocking) - Google correctly rejects it
    (a real HTTP error status), which must be caught and turned into a
    clean unavailable result rather than propagating an exception.
    """
    client = GeminiVerificationClient(api_key="definitely-not-a-real-api-key", timeout_seconds=10.0)

    review = client.review(b"\x89PNG\r\n", {"drawing_number": "TEST-001"})

    assert review.available is False
    assert review.corrections == []
    assert review.missing_items == []
    assert review.ocr_flags == []
    assert review.error is not None


def _mock_post(handler):
    mock_client = httpx.Client(transport=httpx.MockTransport(handler))

    def fake_post(*args, **kwargs):
        return mock_client.post(*args, **kwargs)

    return fake_post


def test_review_parses_a_successful_response(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        body = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": (
                                    '{"corrections": ["revision should be B not A"], '
                                    '"missing_items": ["a support symbol near the elbow"], '
                                    '"ocr_flags": ["line number looks misread"]}'
                                )
                            }
                        ]
                    }
                }
            ]
        }
        return httpx.Response(200, json=body)

    monkeypatch.setattr(httpx, "post", _mock_post(handler))

    client = GeminiVerificationClient(api_key="fake-key")
    review = client.review(b"fake-image-bytes", {"drawing_number": "TEST-001"})

    assert review.available is True
    assert review.corrections == ["revision should be B not A"]
    assert review.missing_items == ["a support symbol near the elbow"]
    assert review.ocr_flags == ["line number looks misread"]
    assert review.error is None


def test_review_handles_malformed_json_response_gracefully(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        body = {"candidates": [{"content": {"parts": [{"text": "not valid json"}]}}]}
        return httpx.Response(200, json=body)

    monkeypatch.setattr(httpx, "post", _mock_post(handler))

    client = GeminiVerificationClient(api_key="fake-key")
    review = client.review(b"fake-image-bytes", {})

    assert review.available is False
    assert review.error is not None


def test_review_handles_unexpected_response_shape_gracefully(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    monkeypatch.setattr(httpx, "post", _mock_post(handler))

    client = GeminiVerificationClient(api_key="fake-key")
    review = client.review(b"fake-image-bytes", {})

    assert review.available is False
    assert review.error is not None


def test_review_handles_non_200_status_gracefully(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "server error"})

    monkeypatch.setattr(httpx, "post", _mock_post(handler))

    client = GeminiVerificationClient(api_key="fake-key")
    review = client.review(b"fake-image-bytes", {})

    assert review.available is False
