from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import get_settings
from app.core.errors import AppError

ALGORITHM = "HS256"
GUEST_TOKEN_TTL = timedelta(days=30)  # 명세: 비회원 토큰 유효기간 초안 30일
USER_TOKEN_TTL = timedelta(days=30)


def create_access_token(user_id: str, kind: str) -> tuple[str, int]:
    """(토큰, 만료까지 남은 초) 를 돌려준다. kind: 'guest' | 'user'."""
    ttl = GUEST_TOKEN_TTL if kind == "guest" else USER_TOKEN_TTL
    now = datetime.now(UTC)
    payload = {"sub": user_id, "kind": kind, "iat": now, "exp": now + ttl}
    token = jwt.encode(payload, get_settings().jwt_secret, algorithm=ALGORITHM)
    return token, int(ttl.total_seconds())


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise AppError(401, "auth_invalid_token", "토큰이 유효하지 않습니다.") from None
