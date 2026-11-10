from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
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
