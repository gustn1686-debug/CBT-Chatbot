"""상담 계획 API. docs/api-spec.md §6

- 계획은 회원만 만든다 (비회원 기록은 보관 기간이 짧고 기기를 바꾸면 사라진다).
- 진행 중인 계획은 한 번에 하나다.
- 회기는 대화에서 "상담 마치기"(POST /conversations/{id}/complete)를 누를 때 하나씩 채워진다.
"""

import re
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.db import get_db
from app.models import Conversation, CounselingPlan, Message, User
from app.services import plans as plan_service
from app.services import summary as memory_summary

router = APIRouter(tags=["plans"])

MIN_SESSIONS, MAX_SESSIONS = 1, 12
_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return (
        plan_service.aware(dt).astimezone(UTC).replace(tzinfo=None).isoformat(timespec="seconds")
        + "Z"
    )


def require_member(user: User = Depends(get_current_user)) -> User:
    if user.is_guest:
        raise AppError(403, "member_required", "상담 계획은 가입한 뒤에 만들 수 있어요.")
    return user


class Schedule(BaseModel):
    weekdays: list[int] = Field(min_length=1, max_length=7)
    time: str
    timezone: str = "Asia/Seoul"

    @field_validator("weekdays")
    @classmethod
    def _weekdays(cls, v: list[int]) -> list[int]:
        if any(d < 0 or d > 6 for d in v):
            raise ValueError("요일은 0(월)~6(일) 이어야 합니다.")
        return sorted(set(v))

    @field_validator("time")
    @classmethod
    def _time(cls, v: str) -> str:
        if not _TIME.match(v):
            raise ValueError("시각은 HH:MM 형식이어야 합니다.")
        return v

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("알 수 없는 시간대입니다.") from None
        return v


class CreatePlan(Schedule):
    total_sessions: int = Field(ge=MIN_SESSIONS, le=MAX_SESSIONS)


def _sessions(db: Session, plan_id: str) -> list[Conversation]:
    return list(
        db.scalars(
            select(Conversation)
            .where(Conversation.plan_id == plan_id)
            .order_by(Conversation.plan_session_no)
        ).all()
    )


def session_out(c: Conversation, total: int) -> dict:
    status = plan_service.effective_status(c.session_summary_status, c.session_summary_requested_at)
    return {
        "number": c.plan_session_no,
        "total": total,
        "conversation_id": c.id,
        "title": c.title,
        "completed_at": _iso(c.completed_at),
        "summary_status": status,
        "summary": c.session_summary if status == "done" else None,
    }


def plan_out(db: Session, plan: CounselingPlan) -> dict:
    sessions = _sessions(db, plan.id)
    summary_status = plan_service.effective_status(plan.summary_status, plan.summary_requested_at)
    return {
        "id": plan.id,
        "status": plan.status,
        "total_sessions": plan.total_sessions,
        "completed_sessions": len(sessions),
        "weekdays": plan.weekdays,
        "time": plan.remind_time,
        "timezone": plan.timezone,
        "schedule_label": plan_service.schedule_label(plan),
        "next_reminder_at": _iso(plan_service.next_reminder(plan)),
        "created_at": _iso(plan.created_at),
        "completed_at": _iso(plan.completed_at),
        "sessions": [session_out(c, plan.total_sessions) for c in sessions],
        "summary_status": summary_status,
        "summary": plan.summary if summary_status == "done" else None,
    }


def _owned_plan(db: Session, user: User, plan_id: str) -> CounselingPlan:
    plan = db.get(CounselingPlan, plan_id)
    if plan is None or plan.user_id != user.id:
        raise AppError(404, "not_found", "상담 계획을 찾을 수 없습니다.")
    return plan


def _active_plan(db: Session, user_id: str) -> CounselingPlan | None:
    return db.scalars(
        select(CounselingPlan).where(
            CounselingPlan.user_id == user_id, CounselingPlan.status == "active"
        )
    ).first()


@router.get("/plans/current")
def current_plan(user: User = Depends(require_member), db: Session = Depends(get_db)) -> dict:
    """진행 중인 계획. 없으면 가장 최근에 마친 계획(전체 요약을 다시 볼 수 있게). 둘 다 없으면 null."""
    plan = (
        _active_plan(db, user.id)
        or db.scalars(
            select(CounselingPlan)
            .where(CounselingPlan.user_id == user.id, CounselingPlan.status == "completed")
            .order_by(CounselingPlan.completed_at.desc())
        ).first()
    )
    return {"plan": plan_out(db, plan) if plan else None}


@router.post("/plans", status_code=201)
def create_plan(
    body: CreatePlan, user: User = Depends(require_member), db: Session = Depends(get_db)
) -> dict:
    if _active_plan(db, user.id) is not None:
        raise AppError(409, "plan_exists", "이미 진행 중인 상담 계획이 있어요.")
    plan = CounselingPlan(
        user_id=user.id,
        total_sessions=body.total_sessions,
        weekdays=body.weekdays,
        remind_time=body.time,
        timezone=body.timezone,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return {"plan": plan_out(db, plan)}


@router.patch("/plans/{plan_id}")
def update_schedule(
    plan_id: str,
    body: Schedule,
    user: User = Depends(require_member),
    db: Session = Depends(get_db),
) -> dict:
    plan = _owned_plan(db, user, plan_id)
    if plan.status != "active":
        raise AppError(409, "plan_not_active", "진행 중인 계획만 일정을 바꿀 수 있어요.")
    plan.weekdays = body.weekdays
    plan.remind_time = body.time
    plan.timezone = body.timezone
    db.commit()
    return {"plan": plan_out(db, plan)}


@router.post("/plans/{plan_id}/cancel")
def cancel_plan(
    plan_id: str, user: User = Depends(require_member), db: Session = Depends(get_db)
) -> dict:
    """계획 그만두기. 마친 회기와 요약은 대화에 그대로 남는다. 알림은 더 가지 않는다."""
    plan = _owned_plan(db, user, plan_id)
    if plan.status == "active":
        plan.status = "cancelled"
        db.commit()
    return {"plan": None}


@router.post("/plans/{plan_id}/summary/retry")
def retry_plan_summary(
    plan_id: str,
    background: BackgroundTasks,
    user: User = Depends(require_member),
    db: Session = Depends(get_db),
) -> dict:
    """전체 요약이 실패했을 때 다시 만든다. 실패한 회기 요약이 있으면 그것부터 다시 만든다."""
    plan = _owned_plan(db, user, plan_id)
    if plan.status != "completed":
        raise AppError(
            409, "plan_not_completed", "모든 회기를 마친 뒤에 전체 요약을 만들 수 있어요."
        )
    now = datetime.now(UTC)
    retried = False
    for c in _sessions(db, plan.id):
        status = plan_service.effective_status(
            c.session_summary_status, c.session_summary_requested_at
        )
        if status == "failed":
            c.session_summary_status, c.session_summary_requested_at = "pending", now
            background.add_task(plan_service.summarize_session, c.id)
            retried = True
    if not retried and plan_service.effective_status(
        plan.summary_status, plan.summary_requested_at
    ) in (None, "failed"):
        plan.summary_status = None
        background.add_task(plan_service.summarize_plan_if_ready, plan.id)
    db.commit()
    return {"plan": plan_out(db, plan)}


# --- 회기 마치기 ---------------------------------------------------------------


def _owned_conversation(db: Session, user: User, conversation_id: str) -> Conversation:
    c = db.get(Conversation, conversation_id)
    if c is None or c.user_id != user.id:
        raise AppError(404, "not_found", "대화를 찾을 수 없습니다.")
    return c


def _complete_response(db: Session, c: Conversation) -> dict:
    plan = db.get(CounselingPlan, c.plan_id)
    return {"session": session_out(c, plan.total_sessions), "plan": plan_out(db, plan)}


@router.post("/conversations/{conversation_id}/complete")
def complete_session(
    conversation_id: str,
    background: BackgroundTasks,
    user: User = Depends(require_member),
    db: Session = Depends(get_db),
) -> dict:
    """이 대화를 진행 중인 계획의 다음 회기로 마친다. 두 번 눌러도 같은 결과를 돌려준다."""
    c = _owned_conversation(db, user, conversation_id)
    if c.plan_id is not None:
        return _complete_response(db, c)

    plan = _active_plan(db, user.id)
    if plan is None:
        raise AppError(409, "no_active_plan", "진행 중인 상담 계획이 없어요.")
    has_user_message = db.scalar(
        select(func.count())
        .select_from(Message)
        .where(Message.conversation_id == c.id, Message.role == "user")
    )
    if not has_user_message:
        raise AppError(409, "empty_session", "이야기를 나눈 뒤에 상담을 마칠 수 있어요.")

    now = datetime.now(UTC)
    done = len(_sessions(db, plan.id))
    c.plan_id = plan.id
    c.plan_session_no = done + 1
    c.completed_at = now
    c.status = "closed"
    c.session_summary_status = "pending"
    c.session_summary_requested_at = now
    if done + 1 >= plan.total_sessions:
        plan.status = "completed"
        plan.completed_at = now
    try:
        db.commit()
    except IntegrityError:  # 두 대화를 동시에 마쳐 회기 번호가 겹친 경우
        db.rollback()
        raise AppError(409, "conflict", "잠시 후 다시 시도해 주세요.") from None

    background.add_task(plan_service.summarize_session, c.id)
    # 다음 대화가 이 회기를 기억하도록 (기존 '대화 종료'와 같은 기억용 요약)
    background.add_task(memory_summary.summarize_conversation, c.id)
    return _complete_response(db, c)


@router.get("/conversations/{conversation_id}/session")
def get_session(
    conversation_id: str, user: User = Depends(require_member), db: Session = Depends(get_db)
) -> dict:
    """마친 회기의 요약 화면. 요약이 만들어지는 동안 앱이 이 주소를 다시 불러 상태를 확인한다."""
    c = _owned_conversation(db, user, conversation_id)
    if c.plan_id is None:
        raise AppError(404, "not_found", "상담 계획으로 마친 대화가 아니에요.")
    return _complete_response(db, c)


@router.post("/conversations/{conversation_id}/session/summary/retry")
def retry_session_summary(
    conversation_id: str,
    background: BackgroundTasks,
    user: User = Depends(require_member),
    db: Session = Depends(get_db),
) -> dict:
    c = _owned_conversation(db, user, conversation_id)
    if c.plan_id is None:
        raise AppError(404, "not_found", "상담 계획으로 마친 대화가 아니에요.")
    status = plan_service.effective_status(c.session_summary_status, c.session_summary_requested_at)
    if status == "failed":
        c.session_summary_status = "pending"
        c.session_summary_requested_at = datetime.now(UTC)
        db.commit()
        background.add_task(plan_service.summarize_session, c.id)
    return _complete_response(db, c)
