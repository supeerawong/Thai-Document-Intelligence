from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="THAIDOC_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./data/thaidoc.db"
    artifact_dir: Path = Path("./artifacts")
    redis_url: str = "redis://localhost:6379/0"
    retention_hours: int = Field(default=24, ge=1)
    max_upload_bytes: int = 50 * 1024 * 1024
    max_pages: int = 200
    sync_max_bytes: int = 10 * 1024 * 1024
    sync_max_pages: int = 5
    api_key: str | None = None
    ai_base_url: str | None = None
    ai_model: str | None = None
    ai_api_key: str | None = None
    ai_timeout_seconds: float = Field(default=60, gt=0)


settings = Settings()
