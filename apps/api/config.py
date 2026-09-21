"""DataGuard application settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── Application ──
    app_name: str = "DataGuard"
    app_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    # ── Database ──
    database_url: str = "postgresql+asyncpg://dataguard:dataguard@localhost:5432/dataguard"
    database_url_sync: str = "postgresql://dataguard:dataguard@localhost:5432/dataguard"

    # ── Redis ──
    redis_url: str = "redis://localhost:6379/0"

    # ── OpenAI ──
    openai_api_key: str = ""
    openai_model_primary: str = "gpt-4o-mini"
    openai_model_secondary: str = "gpt-4o"
    openai_max_budget_usd: float = 5.0

    # ── File Storage ──
    upload_dir: str = "storage/uploads"
    version_dir: str = "storage/versions"
    max_file_size_mb: int = 100

    # ── Security ──
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    api_key: str = ""

    # ── LLM Config ──
    llm_cache_enabled: bool = True
    llm_max_retries: int = 3
    llm_timeout_seconds: int = 60
    llm_max_tokens_per_call: int = 2048

    # ── Autonomy Gate Thresholds ──
    threshold_max_conflict: float = 0.3
    threshold_max_ignorance: float = 0.4
    threshold_belief_error: float = 0.5
    threshold_belief_clean: float = 0.5

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def version_path(self) -> Path:
        p = Path(self.version_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


# Singleton
settings = Settings()
