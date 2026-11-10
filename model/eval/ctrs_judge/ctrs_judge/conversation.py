"""대화 입력(jsonl) 로드와 프롬프트용 직렬화.

한 줄 = 대화 1개:
{"conversation_id": "...", "turns": [{"role": "client|therapist", "text": "..."}], "meta": {...}}
챗봇 대화도 이 형식으로만 바꿔 넣으면 같은 파이프라인으로 채점됨.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

ROLE_LABEL = {"client": "Client", "therapist": "Therapist"}


@dataclass(frozen=True)
class Conversation:
    conversation_id: str
    turns: list[dict]
    meta: dict = field(default_factory=dict)

    def to_text(self) -> str:
        return "\n".join(f"{ROLE_LABEL[t['role']]}: {t['text'].strip()}" for t in self.turns)


def parse_conversation(obj: dict) -> Conversation:
    cid = obj.get("conversation_id")
    turns = obj.get("turns")
    if not cid or not isinstance(turns, list) or not turns:
        raise ValueError("conversation_id와 비어 있지 않은 turns가 필요함")
    for t in turns:
        if t.get("role") not in ROLE_LABEL or not isinstance(t.get("text"), str):
            raise ValueError(f"{cid}: 잘못된 turn {t!r}")
    return Conversation(str(cid), turns, obj.get("meta") or {})


def load_conversations(path: Path | str, limit: int | None = None) -> list[Conversation]:
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                out.append(parse_conversation(json.loads(line)))
                if limit and len(out) >= limit:
                    break
    return out
