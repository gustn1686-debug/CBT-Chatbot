"""보관 기간이 지난 데이터 삭제. docs/db-schema.md §5.

하루 1회 실행한다 (Vercel Cron / pg_cron / 서버 cron):
    python -m app.services.retention
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import SessionLocal
from app.models import Conversation, CrisisEvent, User


@dataclass
class PurgeResult:
    guests: int = 0
    conversations: int = 0
    crisis_events: int = 0


def purge_expired(db: Session, now: datetime | None = None) -> PurgeResult:
    settings = get_settings()
    now = now or datetime.now(UTC)
    result = PurgeResult()

    # 비회원 계정과 그 대화 전체: 마지막 활동 후 N일
    guests = db.scalars(
        select(User).where(
            User.is_guest.is_(True),
            User.last_active_at < now - timedelta(days=settings.guest_retention_days),
        )
    ).all()
    for user in guests:
        db.delete(user)  # 대화·메시지는 cascade
    result.guests = len(guests)

    # 회원의 대화: 대화가 마지막으로 갱신된 후 N일 (계정은 유지)
    conversations = db.scalars(
        select(Conversation)
        .join(User, User.id == Conversation.user_id)
        .where(
            User.is_guest.is_(False),
            Conversation.updated_at < now - timedelta(days=settings.member_retention_days),
        )
    ).all()
    for conversation in conversations:
        db.delete(conversation)
    result.conversations = len(conversations)

    events = db.scalars(
        select(CrisisEvent).where(
            CrisisEvent.created_at < now - timedelta(days=settings.crisis_retention_days)
        )
    ).all()
    for event in events:
        db.delete(event)
    result.crisis_events = len(events)

    db.commit()
    return result


if __name__ == "__main__":
    with SessionLocal() as session:
        print(purge_expired(session))
