"""상담 계획: 회기 마치기 → 회기 요약 → (마지막 회기면) 전체 요약, 그리고 예약 시각 계산.

요약은 사용자 응답을 기다리게 하지 않도록 백그라운드에서 만든다. 상태는 pending → done | failed 이고,
서버가 요약 도중 재시작되면 pending 이 영원히 남으므로 오래된 pending 은 failed 로 보고 다시 시도하게 한다.
"""

import logging
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Conversation, CounselingPlan
from app.services import llm

log = logging.getLogger(__name__)

PENDING_STALE_AFTER = timedelta(minutes=10)
WEEKDAY_LABELS = ("월", "화", "수", "목", "금", "토", "일")


def aware(dt: datetime | None) -> datetime | None:
    """SQLite 는 tz 를 잃으므로 UTC 로 간주한다."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def effective_status(status: str | None, requested_at: datetime | None) -> str | None:
    if status == "pending":
        requested = aware(requested_at)
        if requested is None or datetime.now(UTC) - requested > PENDING_STALE_AFTER:
            return "failed"
    return status


# --- 예약 시각 ---------------------------------------------------------------


def _hm(remind_time: str) -> tuple[int, int]:
    hour, minute = remind_time.split(":")
    return int(hour), int(minute)


def next_reminder(plan: CounselingPlan, now: datetime | None = None) -> datetime | None:
    """다음 알림 시각(UTC). 진행 중인 계획이 아니면 None."""
    if plan.status != "active" or not plan.weekdays:
        return None
    tz = ZoneInfo(plan.timezone)
    local_now = (now or datetime.now(UTC)).astimezone(tz)
    hour, minute = _hm(plan.remind_time)
    for days in range(8):
        day = local_now.date() + timedelta(days=days)
        if day.weekday() not in plan.weekdays:
            continue
        at = datetime(day.year, day.month, day.day, hour, minute, tzinfo=tz)
        if at > local_now:
            return at.astimezone(UTC)
    return None


def due_slot(plan: CounselingPlan, now: datetime, window_minutes: int) -> str | None:
    """지금이 알림을 보낼 예약 시각(부터 window 분 안)이면 그 예약을 나타내는 문자열, 아니면 None."""
    if plan.status != "active":
        return None
    tz = ZoneInfo(plan.timezone)
    local_now = now.astimezone(tz)
    if local_now.weekday() not in plan.weekdays:
        return None
    hour, minute = _hm(plan.remind_time)
    at = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if not (at <= local_now < at + timedelta(minutes=window_minutes)):
        return None
    return at.strftime("%Y-%m-%d %H:%M")


def completed_today(plan_sessions: list[Conversation], plan: CounselingPlan, now: datetime) -> bool:
    """오늘(사용자 시간대) 이미 회기를 마쳤다면 알림을 보내지 않는다."""
    tz = ZoneInfo(plan.timezone)
    today = now.astimezone(tz).date()
    return any(
        c.completed_at is not None and aware(c.completed_at).astimezone(tz).date() == today
        for c in plan_sessions
    )


def schedule_label(plan: CounselingPlan) -> str:
    days = sorted(plan.weekdays)
    when = "매일" if len(days) == 7 else "매주 " + "·".join(WEEKDAY_LABELS[d] for d in days)
    return f"{when} {plan.remind_time}"


# --- 요약 ------------------------------------------------------------------


def _session_messages(c: Conversation) -> list[dict[str, str]]:
    """모델 요약 입력: user 로 시작하고 user/assistant 가 번갈아 와야 한다 (model/README.md §4)."""
    merged: list[dict[str, str]] = []
    for m in c.messages:
        if not m.content:
            continue
        if not merged and m.role != "user":
            continue
        if merged and merged[-1]["role"] == m.role:
            merged[-1] = {"role": m.role, "content": f"{merged[-1]['content']}\n{m.content}"}
        else:
            merged.append({"role": m.role, "content": m.content})
    return merged


async def summarize_session(conversation_id: str) -> None:
    """회기 요약을 만들고, 그 회기가 계획의 마지막이면 이어서 전체 요약을 만든다."""
    with SessionLocal() as db:
        c = db.get(Conversation, conversation_id)
        if c is None or c.plan_id is None:
            return
        messages = _session_messages(c)
        plan_id = c.plan_id

    try:
        if not messages:
            raise llm.LLMError("요약할 대화가 없습니다.")
        text = await llm.summarize_session(messages)
        status = "done"
    except llm.LLMError:
        log.warning("회기 요약 실패 (conversation=%s)", conversation_id)
        text, status = None, "failed"

    with SessionLocal() as db:
        c = db.get(Conversation, conversation_id)
        if c is None:
            return
        c.session_summary = text
        c.session_summary_status = status
        db.commit()

    if status == "done":
        await summarize_plan_if_ready(plan_id)


async def summarize_plan_if_ready(plan_id: str) -> None:
    """계획의 모든 회기를 마쳤고 회기 요약이 다 준비됐을 때만 전체 요약을 한 번 만든다."""
    with SessionLocal() as db:
        plan = db.get(CounselingPlan, plan_id)
        if plan is None or plan.status != "completed":
            return
        if effective_status(plan.summary_status, plan.summary_requested_at) in ("done", "pending"):
            return
        sessions = db.scalars(
            select(Conversation)
            .where(Conversation.plan_id == plan_id)
            .order_by(Conversation.plan_session_no)
        ).all()
        if len(sessions) < plan.total_sessions or any(
            s.session_summary_status != "done" or not s.session_summary for s in sessions
        ):
            return
        payload = [
            {"session_number": s.plan_session_no, "summary": s.session_summary} for s in sessions
        ]
        if len(sessions) == 1:
            plan.summary = sessions[0].session_summary
            plan.summary_status = "done"
            db.commit()
            return
        plan.summary_status = "pending"
        plan.summary_requested_at = datetime.now(UTC)
        db.commit()

    try:
        text = await llm.summarize_plan(payload)
        status = "done"
    except llm.LLMError:
        log.warning("전체 요약 실패 (plan=%s)", plan_id)
        text, status = None, "failed"

    with SessionLocal() as db:
        plan = db.get(CounselingPlan, plan_id)
        if plan is None:
            return
        plan.summary = text
        plan.summary_status = status
        db.commit()
