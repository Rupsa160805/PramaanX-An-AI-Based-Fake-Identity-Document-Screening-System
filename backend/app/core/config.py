"""
PramaanX — Application Configuration
--------------------------------------
All runtime settings are read from environment variables or a .env file.
No secrets or machine-specific absolute paths are hardcoded here.

Create a .env file at backend/.env (see .env.example) before running.
"""

import os
import tempfile
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application settings.
    Values are resolved from environment variables first,
    then from a .env file in the backend directory.
    """

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_name: str = "PramaanX"
    app_version: str = "1.0.0"
    pipeline_version: str = "1.0.0"
    environment: str = "development"  # development | production

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed frontend origins.
    # Example: "http://localhost:3000,http://localhost:5173"
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    # ── File Upload ───────────────────────────────────────────────────────────
    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB default
    allowed_extensions: List[str] = [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]
    tmp_dir: str = tempfile.gettempdir()

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = "INFO"

    # ── AI / Model ────────────────────────────────────────────────────────────
    # Override to point to a trained model file.
    # Leave empty to let the default path (ai/ml/tampering_model.pth) be used.
    tampering_model_path: str = ""

    # ── Mock / Demo ───────────────────────────────────────────────────────────
    # When True, the database check layer returns synthetic mock data
    # instead of calling any real government API (which does not exist for
    # this student prototype).
    mock_database: bool = True


settings = Settings()
