"""
Centralized application configuration.

All environment-driven settings live here so the rest of the codebase
never touches `os.environ` directly. This keeps configuration testable
and makes "mock mode" a first-class, explicit concept rather than an
implicit side effect of a missing key.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", protected_namespaces=("settings_",)
    )

    # --- Gemini ---
    gemini_api_key: str | None = None
    model_name: str = "gemini-2.5-flash"

    # --- App ---
    app_name: str = "Isometric MTO Extractor"
    max_upload_mb: int = 20
    allowed_extensions: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".pdf")
    cors_origins: list[str] = ["http://localhost:3000"]

    @property
    def mock_mode(self) -> bool:
        """Mock mode is active whenever no Gemini API key is configured.

        This is the single source of truth for mock-mode decisions across
        the pipeline, so the app can never crash for lack of a key.
        """
        return not bool(self.gemini_api_key and self.gemini_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor — avoids re-parsing env on every request."""
    return Settings()
