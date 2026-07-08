from fastapi.testclient import TestClient
import io

from PIL import Image

from app.main import app

client = TestClient(app)


def _fake_png_bytes() -> bytes:
    img = Image.new("RGB", (50, 50), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


def test_csv_export_after_extract():
    files = {"file": ("drawing.png", _fake_png_bytes(), "image/png")}
    client.post("/api/extract", files=files)

    resp = client.get("/api/export/csv")
    assert resp.status_code == 200
    text = resp.text
    assert "Drawing Number" in text
    assert "Component,NPS,Unit,Quantity" in text


def test_csv_export_without_prior_extract_returns_404():
    # Use a fresh app instance so no prior extraction has been cached.
    from app.main import app as fresh_app
    from app.api import routes

    routes._LAST_RESULT.clear()
    fresh_client = TestClient(fresh_app)
    resp = fresh_client.get("/api/export/csv")
    assert resp.status_code == 404
