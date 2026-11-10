"""번역 정제된 CACTUS 한국어 json(리스트)을 judge 입력 jsonl 형식으로 변환함.

원본 항목의 dialogue는 '상담사: ...' / '내담자: ...' 줄 단위 문자열임.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

ROLE_MAP = {"상담사": "therapist", "내담자": "client"}
META_KEYS = ("attitude", "cbt_technique", "patterns", "thought")


def parse_dialogue(dialogue: str) -> list[dict]:
    turns = []
    for line in dialogue.split("\n"):
        if not line.strip():
            continue
        speaker, sep, text = line.partition(":")
        if not sep or speaker.strip() not in ROLE_MAP:
            raise ValueError(f"알 수 없는 화자 줄: {line[:40]!r}")
        turns.append({"role": ROLE_MAP[speaker.strip()], "text": text.strip()})
    return turns


def convert(records: list[dict], id_prefix: str = "cactus_ko") -> list[dict]:
    out = []
    for i, r in enumerate(records):
        meta = {k: r[k] for k in META_KEYS if k in r}
        meta["source_index"] = i
        out.append({"conversation_id": f"{id_prefix}_{i:04d}", "turns": parse_dialogue(r["dialogue"]), "meta": meta})
    return out


def write_jsonl(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def sample(rows: list[dict], n: int, seed: int = 0) -> list[dict]:
    return sorted(random.Random(seed).sample(rows, n), key=lambda r: r["conversation_id"])
