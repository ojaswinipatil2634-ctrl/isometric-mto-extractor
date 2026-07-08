import base64
import io

import cv2
import numpy as np

from app.services.preprocessing.pipeline import PreprocessingPipeline
from tests.fixtures import encode_png_bytes, make_line_drawing, make_pdf_bytes, rotate_image


def test_pipeline_runs_all_steps_on_png():
    img = make_line_drawing()
    png_bytes = encode_png_bytes(img)

    result = PreprocessingPipeline().run(png_bytes, "image/png")

    assert result.steps_applied == [
        "load", "deskew", "denoise", "resize", "contrast_enhancement", "adaptive_threshold",
    ]
    assert result.original_width == img.shape[1]
    assert result.original_height == img.shape[0]
    assert result.processed_image.ndim == 2
    assert result.processing_time_ms > 0


def test_pipeline_runs_on_pdf():
    img = make_line_drawing(width=500, height=400)
    pdf_bytes = make_pdf_bytes(img)

    result = PreprocessingPipeline().run(pdf_bytes, "application/pdf")

    assert "load" in result.steps_applied
    assert result.processed_width > 0
    assert result.processed_height > 0


def test_pipeline_corrects_rotated_input():
    img = make_line_drawing()
    rotated = rotate_image(img, -5.0)
    png_bytes = encode_png_bytes(rotated)

    result = PreprocessingPipeline().run(png_bytes, "image/png")

    assert abs(result.skew_angle_corrected_degrees - (-5.0)) < 2.0


def test_preprocess_endpoint_accepts_png(client):
    img = make_line_drawing()
    png_bytes = encode_png_bytes(img)
    files = {"file": ("drawing.png", io.BytesIO(png_bytes), "image/png")}

    response = client.post("/api/v1/preprocess", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "processed"
    assert body["filename"] == "drawing.png"
    assert "adaptive_threshold" in body["steps_applied"]
    assert body["processed_width"] > 0

    # The processed image should be valid, decodable PNG bytes.
    decoded = base64.b64decode(body["processed_image_base64"])
    array = np.frombuffer(decoded, dtype=np.uint8)
    processed_img = cv2.imdecode(array, cv2.IMREAD_GRAYSCALE)
    assert processed_img is not None
    assert processed_img.shape[0] == body["processed_height"]
    assert processed_img.shape[1] == body["processed_width"]


def test_preprocess_endpoint_rejects_unsupported_type(client):
    files = {"file": ("notes.txt", io.BytesIO(b"not a drawing"), "text/plain")}

    response = client.post("/api/v1/preprocess", files=files)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_FILE"


def test_preprocess_endpoint_accepts_pdf(client):
    img = make_line_drawing(width=500, height=400)
    pdf_bytes = make_pdf_bytes(img)
    files = {"file": ("drawing.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    response = client.post("/api/v1/preprocess", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "processed"
