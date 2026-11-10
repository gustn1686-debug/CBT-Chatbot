from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 레포 루트의 .env 를 읽는다 (backend/app/core/config.py -> 루트)
ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    database_url: str = "sqlite:///./synap.db"
    jwt_secret: str = "change-me"
    guest_session_limit: int = 3
    cors_origins: str = "http://localhost:5173"

    llm_mode: str = "mock"  # mock | http
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
