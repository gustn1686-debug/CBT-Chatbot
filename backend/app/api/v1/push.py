"""웹 푸시 구독 API. docs/api-spec.md §7"""

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.plans import require_member
from app.core.config import get_settings
from app.core.errors import AppError
from app.db import get_db
from app.models import PushSubscription, User
from app.services import push

router = APIRouter(prefix="/push", tags=["push"])


class Keys(BaseModel):
    p256dh: str = Field(min_length=1, max_length=255)
    auth: str = Field(min_length=1, max_length=255)


class Subscribe(BaseModel):
    endpoint: str = Field(min_length=1, max_length=2048)
    keys: Keys


class Unsubscribe(BaseModel):
    endpoint: str = Field(min_length=1, max_length=2048)


@router.get("/public-key")
def public_key() -> dict:
    """브라우저가 구독할 때 쓰는 공개키. 서버에 키가 없으면 null (알림 기능 꺼짐)."""
    settings = get_settings()
    return {"public_key": settings.vapid_public_key if settings.push_enabled else None}


@router.post("/subscriptions", status_code=204)
def subscribe(
    body: Subscribe, user: User = Depends(require_member), db: Session = Depends(get_db)
) -> Response:
    if not body.endpoint.startswith("https://"):
        raise AppError(422, "validation_error", "알림 주소가 올바르지 않습니다.")
    # 같은 기기에서 다른 계정으로 로그인했다면 그 기기의 알림은 지금 계정으로 옮긴다.
    sub = db.scalars(
        select(PushSubscription).where(PushSubscription.endpoint == body.endpoint)
    ).first()
    if sub is None:
        sub = PushSubscription(endpoint=body.endpoint)
        db.add(sub)
    sub.user_id = user.id
    sub.p256dh = body.keys.p256dh
    sub.auth = body.keys.auth
    db.commit()
    return Response(status_code=204)


@router.delete("/subscriptions", status_code=204)
def unsubscribe(
    body: Unsubscribe, user: User = Depends(require_member), db: Session = Depends(get_db)
) -> Response:
    sub = db.scalars(
        select(PushSubscription).where(
            PushSubscription.endpoint == body.endpoint, PushSubscription.user_id == user.id
        )
    ).first()
    if sub is not None:
        db.delete(sub)
        db.commit()
    return Response(status_code=204)


@router.post("/test")
async def send_test(user: User = Depends(require_member)) -> dict:
    """알림이 오는지 바로 확인하는 테스트 알림 (시연·점검용)."""
    if not get_settings().push_enabled:
        raise AppError(503, "push_disabled", "서버에 알림 키가 설정되지 않았어요.")
    sent = await push.send_to_user(
        user.id,
        {
            "title": "Synap 알림 테스트",
            "body": "상담 시간이 되면 이렇게 알려드릴게요.",
            "url": "/plan",
            "tag": "test",
        },
    )
    return {"sent": sent}
