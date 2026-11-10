import hashlib
import hmac
import secrets
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


# --- 비밀번호 해시 (표준 라이브러리 scrypt, 추가 의존성 없음) ---
_SCRYPT = {"n": 2**14, "r": 8, "p": 1}


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, dklen=32, **_SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    try:
        scheme, salt_hex, digest_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt_hex), dklen=32, **_SCRYPT
        )
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)
