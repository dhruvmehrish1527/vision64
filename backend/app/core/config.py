"""Application configuration.

All configuration is 12-factor: values come from the environment (or a local
`.env` file in development). Nothing secret is hard-coded. `get_settings()` is
cached so the environment is read once per process.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, validated application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- Core ----
    environment: str = Field(default="development", alias="ENVIRONMENT")
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")

    # ---- Database ----
    database_url: str = Field(default="sqlite:///./vision64.db", alias="DATABASE_URL")

    # ---- Engine ----
    stockfish_path: str = Field(default="stockfish", alias="STOCKFISH_PATH")
    engine_default_depth: int = Field(default=18, alias="ENGINE_DEFAULT_DEPTH")
    engine_multipv: int = Field(default=5, alias="ENGINE_MULTIPV")
    engine_threads: int = Field(default=2, alias="ENGINE_THREADS")
    engine_hash_mb: int = Field(default=128, alias="ENGINE_HASH_MB")
    engine_pool_size: int = Field(default=3, alias="ENGINE_POOL_SIZE")

    # ---- Coach ----
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    coach_model: str = Field(default="claude-opus-5", alias="COACH_MODEL")

    # ---- Auth ----
    clerk_jwks_url: str | None = Field(default=None, alias="CLERK_JWKS_URL")
    clerk_issuer: str | None = Field(default=None, alias="CLERK_ISSUER")
    auth_dev_bypass: bool = Field(default=True, alias="AUTH_DEV_BYPASS")

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins as a clean list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings singleton."""
    return Settings()
