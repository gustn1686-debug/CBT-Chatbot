"""대화 x judge 모델 x 항목 x 회차 실행과 jsonl 저장. 같은 --out으로 다시 실행하면 완료분은 건너뜀."""
from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .client import Completion, cost_usd
from .conversation import Conversation
from .extra_metrics import compute_all
from .parse import parse_response
from .prompts import PromptItem

Key = tuple[str, str, str, int]  # (conversation_id, judge, item, run_index)


def load_done(path: Path) -> set[Key]:
    done: set[Key] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("api_error") is None:  # API 실패 건은 재실행 대상
                    done.add((r["conversation_id"], r["judge"], r["item"], r["run_index"]))
    return done


def run(
    conversations: list[Conversation],
    items: list[PromptItem],
    judges: dict[str, tuple[dict, Callable[[str], Completion]]],  # name -> (cfg, complete_fn)
    out_path: Path,
    runs: int = 1,
    workers: int = 4,
    extra_fields: dict | None = None,
) -> dict:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = load_done(out_path)
    tasks = [
        (c, name, it, k)
        for c in conversations for name in judges for it in items for k in range(1, runs + 1)
        if (c.conversation_id, name, it.item, k) not in done
    ]
    lock = threading.Lock()
    stats = {"total": len(tasks), "parsed": 0, "parse_failed": 0, "api_failed": 0, "cost_usd": 0.0}

    def work(task):
        conv, name, it, k = task
        cfg, complete = judges[name]
        text = conv.to_text()
        row = {
            "conversation_id": conv.conversation_id, "conversation": text, "meta": conv.meta,
            "judge": name, "item": it.item, "run_index": k, "prompt_sha256": it.sha256,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "temperature_config": cfg.get("temperature"), "reasoning_effort": cfg.get("reasoning_effort"),
            "score": None, "explanation": None, "raw_response": None, "parse_ok": False,
            "parse_error": None, "api_error": None, **(extra_fields or {}), **compute_all(conv),
        }
        try:
            c = complete(it.render(text))
        except Exception as e:  # noqa: BLE001
            row["api_error"] = str(e)
        else:
            p = parse_response(c.text)
            usd = cost_usd(cfg, c)
            row.update(
                raw_response=c.text, score=p.score, explanation=p.explanation, parse_ok=p.ok,
                parse_error=p.error, returned_model=c.returned_model,
                temperature_applied=c.temperature_applied, input_tokens=c.input_tokens,
                cached_input_tokens=c.cached_input_tokens, output_tokens=c.output_tokens,
                seconds=c.seconds, cost_usd=usd, request_id=c.request_id,
            )
        with lock:
            with open(out_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            if row["api_error"]:
                stats["api_failed"] += 1
            elif row["parse_ok"]:
                stats["parsed"] += 1
            else:
                stats["parse_failed"] += 1
            stats["cost_usd"] += row.get("cost_usd") or 0.0

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(work, tasks))
    return stats
