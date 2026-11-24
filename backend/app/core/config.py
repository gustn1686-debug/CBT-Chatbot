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

    llm_mode: str = "mock"  # mock | http | runpod
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    # --- RunPod 서버리스 (LLM_MODE=runpod). 작업을 제출(/run)하고 결과를 조회(/status/{id})하는 비동기 방식 ---
    runpod_endpoint_url: str = ""  # 예: https://api.runpod.ai/v2/<엔드포인트 ID>
    runpod_api_key: str = ""  # 비밀. .env 에만 둔다 (저장소·채팅에 붙여넣지 않는다)
    runpod_poll_interval: float = 1.0  # 결과 조회 간격(초)
    runpod_job_timeout: float = (
        120  # 작업 하나를 기다리는 최대 시간. 서버가 꺼져 있다 켜지는 시간 포함
    )
    runpod_stream_chunk_chars: int = 3  # 완성된 답변을 화면에 흘려 보낼 때 한 번에 보내는 글자 수
    runpod_stream_chunk_delay: float = 0.02  # 조각 사이 간격(초). 0 이면 지연 없음
    # 모델 서버에 시스템 프롬프트(+이전 대화 요약)를 보낼지. 팀 모델 API 가 system 메시지를 받는지
    # 확인되기 전까지는 끈다. 켜면 messages 맨 앞에 role=system 메시지를 붙인다.
    runpod_send_system_prompt: bool = False
    # 회기 요약을 같은 모델 API 로 만들지. 상담 응답 전용 API 라면 요약이 동작하지 않으므로 기본은 끈다.
    runpod_summary_enabled: bool = False

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

    # --- 상담 계획: 회기 요약 · 전체 요약 (model/README.md 의 session_summary / plan_summary 모드) ---
    # 비워 두면 모델의 기본 요약 지시를 쓴다. 바꾸고 싶을 때만 문장을 넣는다.
    session_summary_prompt: str = ""
    plan_summary_prompt: str = ""

    # --- 웹 푸시 알림 (상담 시간 알림) ---
    # 키는 scripts/generate_vapid_keys.py 로 만든다. 개인키는 비밀이라 .env 에만 둔다.
    # 둘 중 하나라도 비어 있으면 알림을 보내지 않는다 (나머지 기능은 그대로 동작).
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:synap@example.com"  # 푸시 서비스가 문제 시 연락할 주소
    reminder_check_seconds: float = 30  # 알림 보낼 시각이 됐는지 확인하는 간격
    reminder_window_minutes: int = (
        15  # 예약 시각에서 이만큼 지나도록 못 보냈으면 그 회차는 건너뛴다
    )

    @property
    def push_enabled(self) -> bool:
        return bool(self.vapid_public_key and self.vapid_private_key)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
