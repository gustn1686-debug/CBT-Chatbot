"""judge 모델 호출. OpenAI Responses API(기본) 또는 chat.completions(오픈 모델용)."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODELS_FILE = Path(__file__).resolve().parent.parent / "models.json"


def load_model_configs(path: Path | str = DEFAULT_MODELS_FILE) -> dict[str, dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


@dataclass
class Completion:
    text: str
    returned_model: str | None
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    seconds: float
    temperature_applied: float | None
    request_id: str | None = None


def cost_usd(cfg: dict, c: Completion) -> float | None:
    if "input_usd_per_million" not in cfg:
        return None
    uncached = c.input_tokens - c.cached_input_tokens
    cached_rate = cfg.get("cached_input_usd_per_million", cfg["input_usd_per_million"])
    return (uncached * cfg["input_usd_per_million"] + c.cached_input_tokens * cached_rate
            + c.output_tokens * cfg["output_usd_per_million"]) / 1_000_000


class JudgeClient:
    def __init__(self, name: str, cfg: dict, attempts: int = 4, instructions: str | None = None):
        from openai import OpenAI  # 지연 import: 테스트는 SDK 없이 가능

        self.name, self.cfg, self.attempts = name, cfg, attempts
        self.instructions = instructions  # 프롬프트 원문은 건드리지 않고 system 지시로만 추가
        self.model_id = cfg.get("model_id", name)  # 스냅샷 고정 ID는 models.json의 model_id에 적음
        base_url = cfg.get("base_url") or os.environ.get(cfg.get("base_url_env", ""), None)
        api_key = os.environ.get(cfg.get("api_key_env", "OPENAI_API_KEY"))
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.temperature = cfg.get("temperature")
        self.max_output_tokens = cfg.get("max_output_tokens", 1000)

    def complete(self, prompt: str) -> Completion:
        last: Exception | None = None
        temperature = self.temperature
        for attempt in range(1, self.attempts + 1):
            started = time.perf_counter()
            try:
                return self._call(prompt, temperature, started)
            except Exception as e:  # noqa: BLE001
                last = e
                # 추론 모델은 temperature를 거부할 수 있음: 빼고 재시도하고 실제 적용값을 기록
                if temperature is not None and "temperature" in str(e).lower():
                    temperature = None
                    continue
                if attempt < self.attempts:
                    time.sleep(2 ** attempt)
        raise RuntimeError(f"{self.name}: {self.attempts}회 시도 실패: {last}") from last

    def _call(self, prompt: str, temperature: float | None, started: float) -> Completion:
        if self.cfg.get("api", "responses") == "chat":
            kw = {} if temperature is None else {"temperature": temperature}
            messages = [{"role": "user", "content": prompt}]
            if self.instructions:
                messages.insert(0, {"role": "system", "content": self.instructions})
            r = self.client.chat.completions.create(
                model=self.model_id, messages=messages,
                max_tokens=self.max_output_tokens, **kw)
            u = r.usage
            return Completion(r.choices[0].message.content or "", r.model, u.prompt_tokens, 0,
                              u.completion_tokens, round(time.perf_counter() - started, 3), temperature)
        kw = {}
        if temperature is not None:
            kw["temperature"] = temperature
        if self.cfg.get("reasoning_effort"):
            kw["reasoning"] = {"effort": self.cfg["reasoning_effort"]}
        if self.instructions:
            kw["instructions"] = self.instructions
        r = self.client.responses.create(
            model=self.model_id, input=[{"role": "user", "content": prompt}],
            max_output_tokens=self.max_output_tokens, store=False, **kw)
        u = r.usage
        cached = getattr(getattr(u, "input_tokens_details", None), "cached_tokens", 0) or 0
        return Completion(r.output_text, getattr(r, "model", None), u.input_tokens, cached,
                          u.output_tokens, round(time.perf_counter() - started, 3), temperature,
                          getattr(r, "_request_id", None))
