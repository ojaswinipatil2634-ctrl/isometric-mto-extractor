import io

import pytest


def _png_bytes() -> bytes:
    # Minimal valid 1x1 PNG.
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d494844520000000100000001080600000"
        "01f15c4890000000a49444154789c6360000002000105a557e5000000"
        "0049454e44ae426082"
    )


def test_extract_accepts_valid_png(client):
    files = {"file": ("test.png", io.BytesIO(_png_bytes()), "image/png")}

    response = client.post("/api/v1/extract", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "received"
    assert body["filename"] == "test.png"
    assert body["content_type"] == "image/png"
    assert body["size_bytes"] > 0


def test_extract_rejects_unsupported_type(client):
    files = {"file": ("test.txt", io.BytesIO(b"not a drawing"), "text/plain")}

    response = client.post("/api/v1/extract", files=files)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "INVALID_FILE"


def test_extract_rejects_empty_file(client):
    files = {"file": ("empty.png", io.BytesIO(b""), "image/png")}

    response = client.post("/api/v1/extract", files=files)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "INVALID_FILE"


def test_extract_rejects_oversized_file(client, monkeypatch):
    from app.core import config

    config.get_settings.cache_clear()
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "0")
    config.get_settings.cache_clear()

    files = {"file": ("test.png", io.BytesIO(_png_bytes()), "image/png")}
    response = client.post("/api/v1/extract", files=files)

    assert response.status_code == 413
    body = response.json()
    assert body["error"]["code"] == "FILE_TOO_LARGE"

    config.get_settings.cache_clear()


def test_extract_requires_file_field(client):
    response = client.post("/api/v1/extract")

    assert response.status_code == 422
