"""'점수, 설명' 응답 파싱. 설명에도 쉼표가 있으므로 첫 번째 쉼표 기준으로만 분리함."""
from __future__ import annotations

import re
from dataclasses import dataclass

SCORE_RE = re.compile(r"^[0-6]$")


@dataclass(frozen=True)
class ParsedScore:
    ok: bool
    score: int | None
    explanation: str | None
    error: str | None = None


def parse_response(raw: str | None) -> ParsedScore:
    if not raw or not raw.strip():
        return ParsedScore(False, None, None, "empty response")
    head, sep, tail = raw.strip().partition(",")
    if not sep:
        return ParsedScore(False, None, None, "no comma")
    head = head.strip()
    if not SCORE_RE.match(head):
        return ParsedScore(False, None, None, f"score not an integer in 0..6: {head[:40]!r}")
    return ParsedScore(True, int(head), tail.strip())
