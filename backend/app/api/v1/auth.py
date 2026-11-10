import re

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import bearer, get_current_user
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.db import get_db
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_email(value: str) -> str:
    email = value.strip().lower()
    if len(email) > 255 or not _EMAIL_RE.match(email):
        raise ValueError("이메일 형식이 올바르지 않습니다.")
    return email


class LoginBody(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _normalize_email(v)


class RegisterBody(LoginBody):
    password: str = Field(min_length=8, max_length=128)
    nickname: str = Field(min_length=1, max_length=50)

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        # 프론트 안내: 영문, 숫자 포함 8자 이상
        if not (re.search(r"[A-Za-z]", v) and re.search(r"\d", v)):
            raise ValueError("비밀번호는 영문과 숫자를 포함해야 합니다.")
        return v

    @field_validator("nickname")
    @classmethod
    def _nickname(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("닉네임을 입력해 주세요.")
        return v


def _user_payload(user: User) -> dict:
    return {"id": user.id, "email": user.email, "nickname": user.nickname}


def _auth_response(user: User) -> dict:
    token, _ = create_access_token(user.id, "user")
    return {"access_token": token, "kind": "user", "user": _user_payload(user)}


def _email_taken(db: Session, email: str) -> bool:
    return db.scalar(select(User.id).where(User.email == email)) is not None


def _commit_or_conflict(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "email_taken", "이미 가입된 이메일이에요.") from None


@router.post("/guest")
def create_guest(db: Session = Depends(get_db)) -> dict:
    """비회원 토큰 발급. 비회원도 users 행을 하나 가진다 (is_guest=True)."""
    user = User(is_guest=True)
    db.add(user)
    db.commit()
    token, expires_in = create_access_token(user.id, "guest")
    return {"access_token": token, "kind": "guest", "expires_in": expires_in}


def _upgrade_guest(db: Session, guest: User, body: RegisterBody) -> dict:
    if not guest.is_guest:
        raise AppError(400, "bad_request", "이미 회원 계정입니다.")
    if _email_taken(db, body.email):
        raise AppError(409, "email_taken", "이미 가입된 이메일이에요.")
    # 같은 행을 회원으로 바꾸므로 비회원 때의 대화가 그대로 이어진다.
    guest.is_guest = False
    guest.email = body.email
    guest.password_hash = hash_password(body.password)
    guest.nickname = body.nickname
    _commit_or_conflict(db)
    return _auth_response(guest)


@router.post("/register", status_code=201)
def register(
    body: RegisterBody,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> dict:
    """회원가입. 유효한 비회원 토큰과 함께 호출하면 그 비회원의 대화를 새 계정으로 이어받는다."""
    if creds is not None:
        payload = decode_access_token(creds.credentials)
        guest = db.get(User, payload.get("sub"))
        if guest is not None and guest.is_guest:
            return _upgrade_guest(db, guest, body)

    if _email_taken(db, body.email):
        raise AppError(409, "email_taken", "이미 가입된 이메일이에요.")
    user = User(
        is_guest=False,
        email=body.email,
        password_hash=hash_password(body.password),
        nickname=body.nickname,
    )
    db.add(user)
    _commit_or_conflict(db)
    return _auth_response(user)


@router.post("/upgrade", status_code=201)
def upgrade(
    body: RegisterBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """비회원 → 회원 이관. 비회원 토큰이 필요하다."""
    return _upgrade_guest(db, user, body)


@router.post("/login")
def login(body: LoginBody, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.email == body.email))
    if user is None or user.is_guest or not verify_password(body.password, user.password_hash):
        raise AppError(401, "auth_invalid_credentials", "이메일 또는 비밀번호가 맞지 않아요.")
    return _auth_response(user)
