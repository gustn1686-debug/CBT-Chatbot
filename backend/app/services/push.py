"""웹 푸시 발송과 상담 시간 알림 예약.

서버 안에서 주기적으로(REMINDER_CHECK_SECONDS) 진행 중인 계획을 보고, 예약 시각이 된 계획의 사용자 기기로
알림을 보낸다. 같은 예약을 두 번 보내지 않도록 보낼 권리를 DB 에서 먼저 차지(last_reminded_slot)한다.
서버를 여러 개 띄워도 한 곳에서만 보낸다.
"""

import asyncio
import json
import logging
from contextlib import suppress
from datetime import UTC, datetime

from pywebpush import WebPushException, webpush
from sqlalchemy import or_, select, update

from app.core.config import get_settings
from app.db import SessionLocal
from app.models import Conversation, CounselingPlan, PushSubscription
from app.services import plans as plan_service

log = logging.getLogger(__name__)


def _send_one(sub: PushSubscription, payload: dict) -> bool:
    """한 기기로 보낸다. 브라우저가 버린 구독이면 False (지워야 한다)."""
    settings = get_settings()
    try:
        webpush(
            subscription_info={
                "endpoint": sub.endpoint,
                "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
            },
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_subject},
            ttl=60 * 60,
            timeout=10,
        )
    except WebPushException as exc:
        status = getattr(exc.response, "status_code", None)
        if status in (404, 410):
            return False
        log.warning("푸시 발송 실패 (status=%s)", status)
    except Exception:
        log.exception("푸시 발송 중 오류")
    return True


async def send_to_user(user_id: str, payload: dict) -> int:
    """사용자의 모든 기기로 보내고 보낸 기기 수를 돌려준다. 버려진 구독은 지운다."""
    if not get_settings().push_enabled:
        return 0
    with SessionLocal() as db:
        subs = db.scalars(select(PushSubscription).where(PushSubscription.user_id == user_id)).all()
        db.expunge_all()
    sent, gone = 0, []
    for sub in subs:
        if await asyncio.to_thread(_send_one, sub, payload):
            sent += 1
        else:
            gone.append(sub.id)
    if gone:
        with SessionLocal() as db:
            for sid in gone:
                row = db.get(PushSubscription, sid)
                if row is not None:
                    db.delete(row)
            db.commit()
    return sent


def reminder_payload(plan: CounselingPlan, next_no: int) -> dict:
    return {
        "title": "Synap 상담 시간이에요",
        "body": f"{next_no}회기 상담을 시작해 볼까요? 오늘 하루는 어땠는지 들려주세요.",
        "url": "/",
        "tag": f"plan-{plan.id}",
    }


async def send_due_reminders(now: datetime | None = None) -> int:
    """예약 시각이 된 계획마다 알림을 보낸다. 알림을 보낸 계획 수를 돌려준다."""
    settings = get_settings()
    now = now or datetime.now(UTC)
    targets: list[tuple[str, dict]] = []
    with SessionLocal() as db:
        active = db.scalars(select(CounselingPlan).where(CounselingPlan.status == "active")).all()
        for plan in active:
            slot = plan_service.due_slot(plan, now, settings.reminder_window_minutes)
            if slot is None or plan.last_reminded_slot == slot:
                continue
            sessions = db.scalars(select(Conversation).where(Conversation.plan_id == plan.id)).all()
            if plan_service.completed_today(list(sessions), plan, now):
                continue
            # 보낼 권리를 먼저 차지한다. 다른 서버가 이미 차지했으면 rowcount 가 0 이다.
            claimed = db.execute(
                update(CounselingPlan)
                .where(
                    CounselingPlan.id == plan.id,
                    or_(
                        CounselingPlan.last_reminded_slot.is_(None),
                        CounselingPlan.last_reminded_slot != slot,
                    ),
                )
                .values(last_reminded_slot=slot)
            ).rowcount
            db.commit()
            if claimed:
                targets.append((plan.user_id, reminder_payload(plan, len(sessions) + 1)))
    for user_id, payload in targets:
        await send_to_user(user_id, payload)
    return len(targets)


async def reminder_loop() -> None:
    interval = get_settings().reminder_check_seconds
    while True:
        try:
            await send_due_reminders()
        except Exception:
            log.exception("상담 알림 확인 중 오류")
        await asyncio.sleep(interval)


def start_reminders() -> asyncio.Task | None:
    if not get_settings().push_enabled:
        log.info("VAPID 키가 없어 상담 시간 알림을 보내지 않습니다.")
        return None
    return asyncio.create_task(reminder_loop())


async def stop_reminders(task: asyncio.Task | None) -> None:
    if task is None:
        return
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
