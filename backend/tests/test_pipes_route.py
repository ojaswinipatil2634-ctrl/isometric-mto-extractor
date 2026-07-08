import io

from tests.fixtures import encode_png_bytes, make_l_shaped_pipe_drawing


def test_pipes_endpoint_returns_segments_for_a_valid_upload(client):
    img = make_l_shaped_pipe_drawing()
    png_bytes = encode_png_bytes(img)

    response = client.post(
        "/api/v1/pipes",
        files={"file": ("drawing.png", io.BytesIO(png_bytes), "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "extracted"
    assert body["segment_count"] == 2
    assert len(body["segments"]) == 2
    for seg in body["segments"]:
        assert set(seg.keys()) == {
            "start", "end", "length_px", "angle_degrees", "orientation", "source_segment_count",
        }
    assert body["skeleton_width"] > 0
    assert body["skeleton_height"] > 0
    assert body["steps_applied"] == ["preprocess", "skeletonize", "hough_transform", "polyline_extraction"]


def test_pipes_endpoint_rejects_unsupported_file_type(client):
    response = client.post(
        "/api/v1/pipes",
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "INVALID_FILE"


def test_pipes_endpoint_rejects_empty_file(client):
    response = client.post(
        "/api/v1/pipes",
        files={"file": ("drawing.png", io.BytesIO(b""), "image/png")},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "INVALID_FILE"
