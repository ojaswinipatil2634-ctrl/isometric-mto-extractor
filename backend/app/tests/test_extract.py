import io

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

client = TestClient(app)


def _fake_png_bytes() -> bytes:
    img = Image.new("RGB", (100, 100), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


def test_extract_returns_mock_mto():
    files = {"file": ("drawing.png", _fake_png_bytes(), "image/png")}
    resp = client.post("/api/extract", files=files)
    assert resp.status_code == 200
    body = resp.json()

    assert body["mock_mode"] is True
    assert body["metadata"]["drawing_number"].startswith("MOCK-")
    assert len(body["line_items"]) > 0
    assert body["summary"]["total_gaskets"] == body["summary"]["total_flanged_joints"]
    assert body["summary"]["total_bolt_sets"] == body["summary"]["total_flanged_joints"]


def test_extract_rejects_bad_file_type():
    files = {"file": ("notes.txt", b"hello world", "text/plain")}
    resp = client.post("/api/extract", files=files)
    assert resp.status_code == 400


def test_extract_rejects_empty_file():
    files = {"file": ("drawing.png", b"", "image/png")}
    resp = client.post("/api/extract", files=files)
    assert resp.status_code == 400
