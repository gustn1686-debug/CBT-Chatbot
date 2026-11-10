from datetime import UTC, datetime, timedelta

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db import get_db
from app.models import User

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise AppError(401, "auth_invalid_token", "토큰이 없습니다.")
    payload = decode_access_token(creds.credentials)
    user = db.get(User, payload.get("sub"))
    if user is None:
        raise AppError(401, "auth_invalid_token", "토큰이 유효하지 않습니다.")
    _touch(db, user)
    return user


def _touch(db: Session, user: User) -> None:
    """보관 기간 계산 기준(last_active_at). 요청마다 쓰지 않도록 1시간에 한 번만 갱신한다."""
    now = datetime.now(UTC)
    last = user.last_active_at
    if last is not None and last.tzinfo is None:
        last = last.replace(tzinfo=UTC)  # SQLite 는 tz 를 잃는다
    if last is None or now - last > timedelta(hours=1):
        user.last_active_at = now
        db.commit()
