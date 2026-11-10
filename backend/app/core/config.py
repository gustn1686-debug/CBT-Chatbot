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

    # 보관 기간(일). docs/db-schema.md §5
    guest_retention_days: int = 30
    member_retention_days: int = 60
    crisis_retention_days: int = 180
    crisis_log_secret: str = "change-me"

    llm_mode: str = "mock"  # mock | http
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    # --- 모델 서버 보호 (동시 호출 제한 · 타임아웃). 초 단위 ---
    llm_max_concurrent: int = 8  # 대화 응답을 동시에 생성할 수 있는 요청 수
    llm_max_queue: int = 8  # 빈 자리를 기다리는 요청 수 상한. 넘으면 바로 "이용자가 많아요"
    llm_queue_wait_seconds: float = 20  # 빈 자리를 기다리는 최대 시간
    llm_first_token_timeout: float = 60  # 첫 글자가 올 때까지 (앞부분 처리 시간 포함)
    llm_idle_timeout: float = 30  # 글자 사이가 이 시간 넘게 비면 중단
    llm_total_timeout: float = 180  # 응답 하나의 전체 시간 상한
    llm_summary_max_concurrent: int = 1  # 회기 요약 동시 실행 수 (대화 응답보다 적게)
    llm_summary_queue_wait_seconds: float = 300
    llm_summary_timeout: float = 120

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
