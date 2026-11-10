import base64
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.errors import AppError
from app.db import SessionLocal, get_db
from app.models import Conversation, Message, User
from app.services import llm
from app.services.crisis import CRISIS_MESSAGE, CRISIS_RESOURCES, detect_crisis

router = APIRouter(prefix="/conversations", tags=["conversations"])

# LLM 에 넘기는 최근 메시지 수 상한
HISTORY_LIMIT = 40


class CreateConversation(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class SendMessage(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


def _iso(dt: datetime) -> str:
    # SQLite 는 tz 정보를 잃으므로 UTC 로 간주한다.
    return dt.replace(tzinfo=None).isoformat(timespec="seconds") + "Z"


def _message_count(db: Session, conversation_id: str) -> int:
    return db.scalar(
        select(func.count()).select_from(Message).where(Message.conversation_id == conversation_id)
    )


def _summary(db: Session, c: Conversation) -> dict:
    return {
        "id": c.id,
        "title": c.title,
        "created_at": _iso(c.created_at),
        "updated_at": _iso(c.updated_at),
        "message_count": _message_count(db, c.id),
    }


def _get_owned(db: Session, user: User, conversation_id: str) -> Conversation:
    c = db.get(Conversation, conversation_id)
    if c is None:
        raise AppError(404, "not_found", "대화를 찾을 수 없습니다.")
    if c.user_id != user.id:
        raise AppError(403, "forbidden", "접근할 수 없는 대화입니다.")
    return c


def _signup_required(db: Session, user: User) -> bool:
    if not user.is_guest:
        return False
    count = db.scalar(
        select(func.count()).select_from(Conversation).where(Conversation.user_id == user.id)
    )
    return count >= get_settings().guest_session_limit


@router.post("", status_code=201)
def create_conversation(
    body: CreateConversation | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    c = Conversation(user_id=user.id, title=body.title if body else None)
    db.add(c)
    db.commit()
    db.refresh(c)
    return _summary(db, c)


@router.get("")
def list_conversations(
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    offset = 0
    if cursor:
        try:
            offset = int(base64.urlsafe_b64decode(cursor.encode()).decode())
            if offset < 0:
                raise ValueError
        except ValueError:
            raise AppError(400, "bad_request", "cursor 가 올바르지 않습니다.") from None

    rows = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc(), Conversation.id)
        .offset(offset)
        .limit(limit + 1)
    ).all()
    page = rows[:limit]
    next_cursor = (
        base64.urlsafe_b64encode(str(offset + limit).encode()).decode()
        if len(rows) > limit
        else None
    )
    return {
        "items": [
            {
                "id": c.id,
                "title": c.title,
                "updated_at": _iso(c.updated_at),
                "message_count": _message_count(db, c.id),
            }
            for c in page
        ],
        "next_cursor": next_cursor,
    }


@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    c = _get_owned(db, user, conversation_id)
    messages = []
    for m in c.messages:
        item = {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "created_at": _iso(m.created_at),
        }
        if m.role == "assistant":
            item["crisis"] = m.crisis
        messages.append(item)
    return {"id": c.id, "title": c.title, "messages": messages}


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    c = _get_owned(db, user, conversation_id)
    db.delete(c)
    db.commit()
    return Response(status_code=204)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    body: SendMessage,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    c = _get_owned(db, user, conversation_id)
    content = body.content.strip()
    if not content:
        raise AppError(422, "validation_error", "내용을 입력해 주세요.")

    crisis = detect_crisis(content)
    signup_required = _signup_required(db, user)

    # 이전 대화 + 이번 사용자 메시지 (스트림 시작 전에 사용자 메시지를 저장)
    previous = [{"role": m.role, "content": m.content} for m in c.messages][-HISTORY_LIMIT:]
    db.add(Message(conversation_id=c.id, role="user", content=content))
    if c.title is None:
        c.title = content[:30]
    db.commit()

    assistant = Message(conversation_id=c.id, role="assistant", content="", crisis=crisis)
    db.add(assistant)
    db.commit()
    assistant_id = assistant.id
    history = [*previous, {"role": "user", "content": content}]

    async def events() -> AsyncIterator[str]:
        meta = {"message_id": assistant_id, "crisis": crisis, "signup_required": signup_required}
        if crisis:
            meta["crisis_resources"] = CRISIS_RESOURCES
        yield _sse("meta", meta)

        parts: list[str] = []
        finish = "stop"
        try:
            if crisis:
                parts.append(CRISIS_MESSAGE)
                yield _sse("token", {"delta": CRISIS_MESSAGE})
            else:
                async for delta in llm.stream_reply(history):
                    parts.append(delta)
                    yield _sse("token", {"delta": delta})
        except llm.LLMError as exc:
            finish = "error"
            yield _sse("error", {"code": "llm_unavailable", "message": str(exc)})
        except Exception:  # noqa: BLE001 - 스트림 안에서는 에러 이벤트로 알려야 한다
            finish = "error"
            yield _sse(
                "error", {"code": "internal_error", "message": "응답 생성 중 오류가 났어요."}
            )
        finally:
            # 스트림이 끊겨도 받은 만큼 저장 (빈 응답이면 자리만 차지하므로 삭제)
            with SessionLocal() as session:
                row = session.get(Message, assistant_id)
                if row is not None:
                    text = "".join(parts)
                    if text:
                        row.content = text
                    else:
                        session.delete(row)
                    conv = session.get(Conversation, conversation_id)
                    if conv is not None:
                        conv.updated_at = datetime.now(UTC)
                    session.commit()

        if finish == "stop":
            yield _sse("done", {"message_id": assistant_id, "finish_reason": "stop"})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
