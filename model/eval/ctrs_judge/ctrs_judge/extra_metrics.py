"""계산형 보조 지표 훅. 함수를 등록하면 결과 jsonl에 `metric_<name>` 열이 붙음.

예: register("repeat_rate", lambda conv: ...)  # 반복률은 CTRS로 문제가 안 잡힐 때 추가 검토
"""
from __future__ import annotations

from typing import Callable

from .conversation import Conversation

METRICS: dict[str, Callable[[Conversation], float]] = {}


def register(name: str, fn: Callable[[Conversation], float]) -> None:
    METRICS[name] = fn


def compute_all(conv: Conversation) -> dict[str, float]:
    return {f"metric_{name}": fn(conv) for name, fn in METRICS.items()}
