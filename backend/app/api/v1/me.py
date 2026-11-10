from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import verify_password
from app.db import get_db
from app.models import Conversation, User

router = APIRouter(tags=["me"])


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    limit = get_settings().guest_session_limit
    count = db.scalar(
        select(func.count()).select_from(Conversation).where(Conversation.user_id == user.id)
    )
    return {
        "kind": "guest" if user.is_guest else "user",
        "user": None
        if user.is_guest
        else {"id": user.id, "email": user.email, "nickname": user.nickname},
        "usage": {
            "session_count": count,
            "guest_session_limit": limit,
            "signup_required": user.is_guest and count >= limit,
        },
    }


class DeleteAccount(BaseModel):
    password: str = Field(max_length=128)


@router.delete("/me", status_code=204)
def delete_me(
    body: DeleteAccount | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """탈퇴. 계정과 모든 대화·메시지를 즉시 삭제한다 (docs/db-schema.md §5).

    되돌릴 수 없는 작업이라 회원은 비밀번호를 한 번 더 확인한다. 비회원은 확인 없이 삭제한다.
    위기 감지 통계(crisis_events)는 사용자와 연결돼 있지 않아 그대로 남는다.
    """
    if not user.is_guest and not (body and verify_password(body.password, user.password_hash)):
        raise AppError(403, "auth_invalid_credentials", "비밀번호가 맞지 않아요.")
    db.delete(user)  # 대화·메시지는 cascade
    db.commit()
    return Response(status_code=204)
