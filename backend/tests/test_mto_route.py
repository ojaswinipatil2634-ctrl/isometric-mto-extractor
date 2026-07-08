import io

import openpyxl

from tests.fixtures import encode_png_bytes, make_l_shaped_pipe_drawing

PNG_BYTES = encode_png_bytes(make_l_shaped_pipe_drawing())


def _upload(client, filename="drawing.png"):
    files = {"file": (filename, io.BytesIO(PNG_BYTES), "image/png")}
    return client.post("/api/v1/mto", files=files)


def test_post_mto_persists_and_returns_full_result(mto_client):
    response = _upload(mto_client)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "extracted"
    assert body["id"] == 1
    assert body["filename"] == "drawing.png"
    assert body["node_count"] == 3
    assert body["edge_count"] == 2
    assert "hardware" in body
    assert "violations" in body
    assert "items" in body
    assert len(body["items"]) > 0
    assert body["extraction_source"] in ("gemini", "mock")


def test_post_mto_rejects_unsupported_file_type(mto_client):
    files = {"file": ("notes.txt", io.BytesIO(b"not a drawing"), "text/plain")}

    response = mto_client.post("/api/v1/mto", files=files)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_FILE"


def test_history_lists_persisted_runs(mto_client):
    _upload(mto_client, "first.png")
    _upload(mto_client, "second.png")

    response = mto_client.get("/api/v1/mto/history")

    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 2
    assert len(body["items"]) == 2
    # newest first
    assert body["items"][0]["filename"] == "second.png"


def test_history_respects_limit(mto_client):
    for i in range(3):
        _upload(mto_client, f"file{i}.png")

    response = mto_client.get("/api/v1/mto/history?limit=1")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["total_count"] == 3


def test_get_run_by_id_returns_full_detail(mto_client):
    created = _upload(mto_client).json()

    response = mto_client.get(f"/api/v1/mto/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_run_by_id_404_for_missing_run(mto_client):
    response = mto_client.get("/api/v1/mto/999999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RUN_NOT_FOUND"


def test_export_json(mto_client):
    created = _upload(mto_client).json()

    response = mto_client.get(f"/api/v1/mto/{created['id']}/export?format=json")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert body["id"] == created["id"]


def test_export_csv(mto_client):
    created = _upload(mto_client).json()

    response = mto_client.get(f"/api/v1/mto/{created['id']}/export?format=csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    text = response.content.decode("utf-8")
    assert "# Summary" in text
    assert "# Material Take-Off" in text
    assert "# Hardware" in text
    assert "# Violations" in text


def test_export_xlsx(mto_client):
    created = _upload(mto_client).json()

    response = mto_client.get(f"/api/v1/mto/{created['id']}/export?format=xlsx")

    assert response.status_code == 200
    workbook = openpyxl.load_workbook(io.BytesIO(response.content))
    assert workbook.sheetnames == ["Summary", "MTO Items", "Hardware", "Violations"]


def test_export_404_for_missing_run(mto_client):
    response = mto_client.get("/api/v1/mto/999999/export?format=json")

    assert response.status_code == 404


def test_export_rejects_invalid_format(mto_client):
    created = _upload(mto_client).json()

    response = mto_client.get(f"/api/v1/mto/{created['id']}/export?format=pdf")

    assert response.status_code == 422
