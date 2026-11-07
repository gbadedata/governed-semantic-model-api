"""Runtime configuration, read from environment variables prefixed SEMANTIC_API_."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SAMPLE_DIR = Path(__file__).resolve().parents[2] / "data" / "sample"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SEMANTIC_API_", env_file=".env", extra="ignore")

    # "local" answers from the curated sample mart with DuckDB (development and tests);
    # "fabric" queries the Fabric / Power BI semantic model (production).
    backend: Literal["local", "fabric"] = "local"
    sample_data_dir: Path = DEFAULT_SAMPLE_DIR
    log_level: str = "INFO"
    max_range_days: int = 366
    max_top_products: int = 50

    fabric_workspace_id: str | None = None
    fabric_dataset_id: str | None = None
    fabric_timeout_seconds: float = 20.0
    # Credentials: either an AWS Secrets Manager secret (JSON with tenant_id, client_id,
    # client_secret) or the three values directly. Prefer the secret in any deployed environment.
    fabric_secret_arn: str | None = None
    fabric_tenant_id: str | None = None
    fabric_client_id: str | None = None
    fabric_client_secret: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
