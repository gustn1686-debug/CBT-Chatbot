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
    return user
