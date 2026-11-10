import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    """회원 또는 비회원. 비회원은 is_guest=True 이고 email/password 가 비어 있다.

    가입(upgrade) 시 같은 행에 email/password/nickname 을 채우고 is_guest 를 False 로
    바꾸기 때문에, 대화는 옮길 필요 없이 그대로 이어진다.
    """

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "is_guest OR (email IS NOT NULL AND password_hash IS NOT NULL)",
            name="ck_users_member_has_credentials",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    is_guest: Mapped[bool] = mapped_column(Boolean, default=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nickname: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    upgraded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Conversation(Base):
    """대화 1회기."""

    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("user_id", "session_no", name="uq_conversations_user_session_no"),
        Index("ix_conversations_user_updated", "user_id", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    session_no: Mapped[int] = mapped_column(Integer)  # 사용자별 회기 번호(1부터)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | closed
    # 모델 하네스가 회기마다 만드는 상담 계획/진행 상태. 하네스 구조가 바뀔 수 있어 JSON 으로 둔다.
    plan: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # 다음 회기에 기억을 넘기기 위한 요약(JSON 문자열, app/services/summary.py). 사용자에게는 보여주지 않는다.
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 요약이 반영한 마지막 메시지 seq. 이어서 대화하면 요약이 낡은 것이 되어 다시 만든다.
    summary_seq: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    user: Mapped[User] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.seq",
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("conversation_id", "seq", name="uq_messages_conv_seq"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    seq: Mapped[int] = mapped_column(Integer)  # 대화 안의 순번(1부터)
    role: Mapped[str] = mapped_column(String(20))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    crisis: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class CrisisEvent(Base):
    """비식별 위기 감지 기록 (통계용).

    사용자·대화와 FK 를 걸지 않고, 메시지 원문과 키워드 자체도 저장하지 않는다.
    anon_code 는 HMAC(user_id, CRISIS_LOG_SECRET) 의 앞부분으로 가명 코드다. (docs/db-schema.md §3.4)
    """

    __tablename__ = "crisis_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    anon_code: Mapped[str] = mapped_column(String(32))
    category: Mapped[str] = mapped_column(String(50))
    keyword_version: Mapped[str] = mapped_column(String(20))
    user_kind: Mapped[str] = mapped_column(String(10))  # guest | member
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
