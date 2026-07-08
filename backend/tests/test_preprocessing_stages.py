import numpy as np
import cv2

from app.services.preprocessing import contrast, denoise, deskew, loader, resize, threshold
from tests.fixtures import encode_png_bytes, make_line_drawing, make_pdf_bytes, rotate_image


def test_loader_decodes_png():
    img = make_line_drawing()
    png_bytes = encode_png_bytes(img)

    loaded = loader.load_as_bgr_image(png_bytes, "image/png")

    assert loaded.shape == img.shape


def test_loader_decodes_jpeg():
    img = make_line_drawing()
    import cv2

    success, buffer = cv2.imencode(".jpg", img)
    assert success

    loaded = loader.load_as_bgr_image(buffer.tobytes(), "image/jpeg")

    assert loaded.ndim == 3
    assert loaded.shape[0] == img.shape[0]
    assert loaded.shape[1] == img.shape[1]


def test_loader_decodes_pdf_first_page():
    img = make_line_drawing(width=400, height=300)
    pdf_bytes = make_pdf_bytes(img)

    loaded = loader.load_as_bgr_image(pdf_bytes, "application/pdf")

    assert loaded.ndim == 3
    # Rendered at 300 DPI from a 400x300 "point" page -> larger raster.
    assert loaded.shape[1] > 400
    assert loaded.shape[0] > 300


def test_deskew_corrects_known_rotation():
    img = make_line_drawing()
    rotated = rotate_image(img, 7.0)

    corrected, detected_angle = deskew.deskew(rotated)

    # Hough-based estimation on synthetic art won't be pixel-perfect,
    # but should land close to the true 7-degree rotation.
    assert abs(detected_angle - 7.0) < 2.0

    # The real correctness criterion: the corrected image should measure
    # as level (near-zero residual skew), regardless of sign convention.
    corrected_gray = cv2.cvtColor(corrected, cv2.COLOR_BGR2GRAY)
    residual_skew = deskew.estimate_skew_angle(corrected_gray)
    assert abs(residual_skew) < 1.0


def test_deskew_leaves_level_image_alone():
    img = make_line_drawing()

    _, detected_angle = deskew.deskew(img)

    assert abs(detected_angle) < 1.0


def test_denoise_preserves_shape():
    img = make_line_drawing()

    result = denoise.denoise(img)

    assert result.shape == img.shape
    assert result.dtype == img.dtype


def test_resize_caps_longest_edge():
    img = make_line_drawing(width=4000, height=1000)

    resized, scale = resize.resize(img, max_dimension=2200)

    assert max(resized.shape[:2]) <= 2200
    assert scale < 1.0


def test_resize_does_not_upscale_small_images():
    img = make_line_drawing(width=400, height=300)

    resized, scale = resize.resize(img, max_dimension=2200)

    assert scale == 1.0
    assert resized.shape == img.shape


def test_contrast_enhancement_preserves_shape_and_type():
    img = make_line_drawing()

    enhanced = contrast.enhance_contrast(img)

    assert enhanced.shape == img.shape
    assert enhanced.dtype == np.uint8


def test_adaptive_threshold_produces_binary_image():
    img = make_line_drawing()

    binary = threshold.adaptive_threshold(img)

    assert binary.ndim == 2
    unique_values = set(np.unique(binary).tolist())
    assert unique_values.issubset({0, 255})
