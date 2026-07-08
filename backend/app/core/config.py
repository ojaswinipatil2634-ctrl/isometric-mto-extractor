"""
Application configuration.

Centralizes all environment-driven settings so nothing is hard-coded
in routes or services. Uses pydantic-settings so values are validated
at startup and fail loudly if something required is missing/malformed.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- General ---
    APP_NAME: str = "Isometric MTO Extractor"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # --- API ---
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # --- Storage ---
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 25

    # --- Database (wired in a later phase, declared now so .env is stable) ---
    DATABASE_URL: str = "sqlite:///./data/app.db"

    # --- Gemini (used starting Phase 9; safe to leave blank for now) ---
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TIMEOUT_SECONDS: float = 60.0

    # --- OCR (Phase 3) ---
    OCR_LANG: str = "en"
    # CPU-only by default - this is the safe default on Windows dev
    # machines, which typically don't have a CUDA-enabled PaddlePaddle
    # build installed. Set to true only if paddlepaddle-gpu is installed.
    OCR_USE_GPU: bool = False
    OCR_USE_ANGLE_CLS: bool = True

    # --- Symbol detection (Phase 4) ---
    # Trained YOLOv11 weights are not shipped in this repo (they're a
    # project-specific training artifact, not something pip installs).
    # If this path doesn't exist, /detect returns a structured
    # 503 DETECTION_UNAVAILABLE error rather than crashing or fabricating
    # detections - see app/services/detection/engine.py.
    YOLO_WEIGHTS_PATH: str = "./data/weights/yolov11_piping.pt"
    YOLO_CONFIDENCE_THRESHOLD: float = 0.25
    # CPU-only by default, same rationale as OCR_USE_GPU above.
    YOLO_DEVICE: str = "cpu"

    # --- Logging ---
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor so the .env file is parsed only once."""
    return Settings()
