"""회기 요약. 지난 대화를 다 저장·전달할 수 없으므로 회기마다 짧게 요약해 두고,
새 대화를 시작할 때 이 요약을 모델에게 '기억'으로 넘긴다. 요약은 사용자에게 보여주지 않는다.

요약 시점: (1) 대화 종료를 눌렀을 때 (2) 새 대화를 시작할 때, 요약이 없거나 낡은 이전 대화.
"""

import json
import logging
import re
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Conversation, Message
from app.services import llm

log = logging.getLogger(__name__)

# 한 번에 새 대화 시작 시 따라잡을 이전 대화 수 / 모델에 넘길 요약 수
CATCH_UP_LIMIT = 5
MEMORY_LIMIT = 3
# 요약에 넣는 대화 길이 상한
MAX_MESSAGES = 60
MAX_CHARS = 6000

FIELDS = ("situation", "first_thought", "emotions", "findings", "alternative", "next_action")

SUMMARY_SYSTEM = (
    "다음은 CBT 상담 챗봇과 사용자의 대화입니다. 다음 대화에서 맥락을 이어가기 위한 요약을 "
    "JSON 객체 하나로만 답하세요. 대화에 없는 내용은 지어내지 말고 빈 문자열/빈 배열로 두세요.\n"
    '키: "situation"(상황), "first_thought"(처음 떠오른 생각), "emotions"(감정 문자열 배열), '
    '"findings"(대화에서 확인한 점), "alternative"(대안적 생각), "next_action"(다음에 해볼 행동).'
)


def _transcript(messages: list[Message]) -> str:
    lines = [
        f"{'사용자' if m.role == 'user' else '상담사'}: {m.content}"
        for m in messages[-MAX_MESSAGES:]
    ]
    return "\n".join(lines)[-MAX_CHARS:]


def parse_summary(text: str) -> dict:
    """모델 응답에서 JSON 을 꺼낸다. 형식이 깨져 있으면 전체를 '상황'에 담아 잃어버리지 않는다."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            raw = json.loads(match.group(0))
        except ValueError:
            raw = None
        if isinstance(raw, dict):
            summary = {k: raw.get(k) for k in FIELDS}
            summary["emotions"] = [str(e) for e in (summary["emotions"] or []) if e]
            for key in FIELDS:
                if key != "emotions":
                    summary[key] = str(summary[key] or "").strip()
            return summary
    return {
        **{k: "" for k in FIELDS},
        "emotions": [],
        "situation": text.strip()[:500],
    }


async def summarize_conversation(conversation_id: str) -> None:
    """한 대화를 요약해 저장한다. 실패해도 대화에는 영향이 없도록 조용히 넘어간다."""
    with SessionLocal() as db:
        c = db.get(Conversation, conversation_id)
        if c is None:
            return
        messages = list(c.messages)
        last_seq = max((m.seq for m in messages), default=0)
        if not any(m.role == "user" for m in messages) or c.summary_seq == last_seq:
            return
        transcript = _transcript(messages)

    try:
        text = await llm.complete(SUMMARY_SYSTEM, transcript)
    except llm.LLMError:
        log.warning("회기 요약 실패 (conversation=%s)", conversation_id)
        return

    summary = parse_summary(text)
    with SessionLocal() as db:
        c = db.get(Conversation, conversation_id)
        if c is None:  # 요약하는 사이 삭제됨
            return
        # 요약을 만드는 사이 대화가 이어졌더라도 last_seq 까지만 반영한 것으로 기록한다.
        c.summary = json.dumps(summary, ensure_ascii=False)
        c.summary_seq = last_seq
        db.commit()


async def summarize_stale(user_id: str, exclude_id: str | None = None) -> None:
    """새 대화를 시작할 때, 요약이 없거나 낡은 이전 대화를 최근 순으로 따라잡는다."""
    with SessionLocal() as db:
        last_seq = (
            select(func.max(Message.seq))
            .where(Message.conversation_id == Conversation.id)
            .correlate(Conversation)
            .scalar_subquery()
        )
        has_user_msg = (
            select(Message.id)
            .where(Message.conversation_id == Conversation.id, Message.role == "user")
            .correlate(Conversation)
            .exists()
        )
        stmt = (
            select(Conversation.id)
            .where(
                Conversation.user_id == user_id,
                has_user_msg,
                (Conversation.summary_seq.is_(None)) | (Conversation.summary_seq < last_seq),
            )
            .order_by(Conversation.updated_at.desc())
            .limit(CATCH_UP_LIMIT)
        )
        if exclude_id:
            stmt = stmt.where(Conversation.id != exclude_id)
        ids = list(db.scalars(stmt))
    for cid in ids:
        await summarize_conversation(cid)


def _fmt_date(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def build_memory(db: Session, user_id: str, exclude_id: str) -> str | None:
    """모델에게 넘길 이전 회기 요약 텍스트. 지금 대화는 제외한다 (이미 대화 내용으로 들어간다)."""
    rows = db.scalars(
        select(Conversation)
        .where(
            Conversation.user_id == user_id,
            Conversation.id != exclude_id,
            Conversation.summary.is_not(None),
        )
        .order_by(Conversation.updated_at.desc())
        .limit(MEMORY_LIMIT)
    ).all()
    blocks = []
    for c in reversed(rows):  # 오래된 것부터
        try:
            s = json.loads(c.summary)
        except ValueError:
            continue
        parts = [
            ("상황", s.get("situation")),
            ("처음 떠오른 생각", s.get("first_thought")),
            ("감정", ", ".join(s.get("emotions") or [])),
            ("확인한 점", s.get("findings")),
            ("대안적 생각", s.get("alternative")),
            ("다음 행동", s.get("next_action")),
        ]
        body = " / ".join(f"{k}: {v}" for k, v in parts if v)
        if body:
            blocks.append(f"- ({_fmt_date(c.updated_at)}) {body}")
    return "\n".join(blocks) or None
