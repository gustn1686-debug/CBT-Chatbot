#!/usr/bin/env python3
"""ChatGPT 로그인 Codex를 맥락이 분리된 텍스트 역할로 호출한다. API 키를 사용하지 않는다."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import subprocess
import tempfile
import time

from .common import write_json
DEFAULT_OUTPUT=Path('runs/roles')

MODELS = {"sol": "gpt-6.1-sol", "teacher": "gpt-6.1-sol"}
DISABLED_FEATURES = ("apps", "shell_tool", "unified_exec", "multi_agent", "browser_use",
                     "computer_use", "image_generation", "skill_search")
PROBE_PROMPT = 'Return only {"status":"ok"}. Do not use tools.'
PROBE_SCHEMA = {"type": "object", "properties": {"status": {"type": "string", "enum": ["ok"]}},
                "required": ["status"], "additionalProperties": False}


def clean_environment():
    environment = os.environ.copy()
    for key in ("OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL"):
        environment.pop(key, None)
    return environment


def read_limits(timeout_seconds=30):
    """공식 로컬 app-server의 읽기 전용 계정 한도 조회. 리셋·크레딧 사용 요청은 없다."""
    process = subprocess.Popen(["codex", "app-server", "--stdio", "--disable", "apps"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        bufsize=0, env=clean_environment())
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + timeout_seconds
    buffer = bytearray()

    def send(message):
        process.stdin.write((json.dumps(message) + "\n").encode())
        process.stdin.flush()

    def receive(identifier):
        while time.monotonic() < deadline:
            while b"\n" in buffer:
                line, _, remaining = buffer.partition(b"\n")
                buffer[:] = remaining
                message = json.loads(line)
                if message.get("id") == identifier:
                    if "error" in message:
                        raise RuntimeError("Codex 일반 사용량 조회가 거절됐습니다.")
                    return message["result"]
            if not selector.select(max(0, deadline - time.monotonic())):
                break
            chunk = os.read(process.stdout.fileno(), 65536)
            if not chunk:
                break
            buffer.extend(chunk)
        raise TimeoutError("Codex 일반 사용량을 확인할 수 없습니다.")

    try:
        send({"id": 1, "method": "initialize", "params": {
            "clientInfo": {"name": "cbt_research_roles", "version": "1.0"},
            "capabilities": {"experimentalApi": True}}})
        receive(1)
        send({"method": "initialized", "params": {}})
        send({"id": 2, "method": "account/rateLimits/read", "params": {
            "excludeResetCreditDetails": True, "supportsLunaReserve": False}})
        return receive(2)
    finally:
        selector.close()
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def quota_windows(bucket):
    """공식 응답의 null 창은 제외하되, 누락·불명확한 사용량은 거절한다."""
    windows = {}
    for name in ("primary", "secondary"):
        if name not in bucket:
            raise RuntimeError("한도 창의 제공 여부가 확인되지 않았습니다.")
        window = bucket[name]
        if window is None:
            continue
        used = window.get("usedPercent") if isinstance(window, dict) else None
        if type(used) not in (int, float) or not math.isfinite(used) or used < 0:
            raise RuntimeError("한도 창의 잔량이 확인되지 않았습니다.")
        windows[name] = window
    if not windows:
        raise RuntimeError("확인 가능한 일반 한도 창이 없습니다.")
    return windows


def require_included_usage(limits, *, minimum_remaining=3):
    if limits.get("ordinaryUsageAllowed") is not True:
        raise RuntimeError("일반 포함 한도 사용이 허용되지 않아 중단합니다. 구매 크레딧·리셋으로 전환하지 않습니다.")
    bucket = limits.get("rateLimitsByLimitId", {}).get("codex") or limits.get("rateLimits")
    if not isinstance(bucket, dict):
        raise RuntimeError("일반 한도 잔량이 확인되지 않았습니다.")
    if bucket.get("spendControlReached") is True or bucket.get("rateLimitReachedType"):
        raise RuntimeError("서버가 사용 제한 도달을 보고하여 새 역할 호출을 중단합니다.")
    for window in quota_windows(bucket).values():
        if window["usedPercent"] >= 100 - minimum_remaining:
            raise RuntimeError("일반 사용 한도 여유가 부족해 새 역할 호출을 중단합니다.")
    return bucket


def request_identity(role: str, prompt: str, schema: dict):
    settings = {"backend": "codex_chatgpt", "model": MODELS[role], "reasoning_effort": "low",
                "ephemeral": True, "fresh_context": True, "tools_disabled": list(DISABLED_FEATURES)}
    digest = hashlib.sha256(json.dumps({"settings": settings, "prompt": prompt, "schema": schema},
                                      ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return settings, digest


def verify_cached_probes(folder: Path):
    """기존 성공 캐시만 읽는다. 이 함수는 모델을 호출하지 않는다."""
    version = subprocess.check_output(["codex", "--version"], text=True).strip()
    for role in MODELS:
        settings, digest = request_identity(role, PROBE_PROMPT, PROBE_SCHEMA)
        stored = json.loads((folder / "codex_role_cache" / (digest + ".json")).read_text())
        if (stored.get("status") != "received" or stored.get("output") != {"status": "ok"}
                or stored.get("settings") != settings or stored.get("cli_version") != version):
            raise ValueError("현재 Codex 버전·역할 설정의 성공 캐시가 없습니다.")
    limits = read_limits()
    require_included_usage(limits, minimum_remaining=15)
    write_json(folder / 'codex_role_preflight.json', {
        'successful': True, 'models': MODELS, 'reasoning_effort': 'low', 'cli_version': version,
        'authentication': 'chatgpt', 'verified_unix': time.time(), 'usage': limits,
        'verification': 'existing_success_cache_and_current_included_allowance', 'new_model_calls': 0})
    return {"successful": True, "new_model_calls": 0}


def invoke(folder: Path, role: str, prompt: str, schema: dict):
    if role not in MODELS or len(prompt.encode()) > 120000:
        raise ValueError("허용한 역할 또는 입력 크기가 아닙니다.")
    settings, digest = request_identity(role, prompt, schema)
    cache = folder / "codex_role_cache" / (digest + ".json")
    if cache.exists():
        stored = json.loads(cache.read_text())
        if stored.get("status") != "received":
            raise RuntimeError("이전 Codex 호출 상태가 불명확하여 자동 재호출하지 않습니다.")
        return stored["output"]
    status = subprocess.run(["codex", "login", "status"], capture_output=True, text=True,
                            timeout=15, env=clean_environment())
    if status.returncode != 0 or "using ChatGPT" not in status.stdout + status.stderr:
        raise RuntimeError("Codex의 ChatGPT 로그인을 확인해야 합니다. API 인증으로 대체하지 않습니다.")
    before = read_limits()
    bucket = require_included_usage(before)
    version = subprocess.check_output(["codex", "--version"], text=True).strip()
    write_json(cache, {"status": "pending_or_unknown", "role": role, "settings": settings,
                       "cli_version": version, "usage_before": before, "created_unix": time.time()})
    with tempfile.TemporaryDirectory(prefix="cbt_codex_role_", dir="/private/tmp") as directory:
        temporary = Path(directory)
        schema_path, output_path = temporary / "schema.json", temporary / "output.json"
        schema_path.write_text(json.dumps(schema, ensure_ascii=False))
        command = ["codex", "exec", "--ignore-user-config", "--ephemeral", "--skip-git-repo-check",
                   "--sandbox", "read-only", "--model", MODELS[role], "--json", "--color", "never",
                   "--output-schema", str(schema_path), "--output-last-message", str(output_path),
                   "--config", 'model_reasoning_effort="low"', "--config", 'web_search="disabled"',
                   "--config", 'service_tier="default"', "--cd", str(temporary)]
        for feature in DISABLED_FEATURES:
            command += ["--disable", feature]
        completed = subprocess.run(command + ["-"], input=prompt, capture_output=True, text=True,
                                   timeout=90 if role == "client" else 180, env=clean_environment())
        events = []
        for line in completed.stdout.splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        write_json(cache.with_suffix(".events.json"), {"events": events})
        if completed.returncode != 0 or not output_path.exists():
            # 인증 정보가 섞일 수 있는 표준 오류 원문은 출력하지 않는다.
            cache.with_suffix(".stderr.log").write_text(completed.stderr)
            raise RuntimeError("Codex 역할 호출을 완료하지 못했습니다. GPU는 시작하지 않습니다.")
        forbidden = {"command_execution", "mcp_tool_call", "web_search", "file_change"}
        if any(event.get("item", {}).get("type") in forbidden for event in events):
            raise RuntimeError("분리한 역할이 도구를 사용해 결과를 채택하지 않습니다.")
        output = json.loads(output_path.read_text())
    after = read_limits()
    after_bucket = after.get("rateLimitsByLimitId", {}).get("codex") or after.get("rateLimits") or {}
    before_credit = bucket.get("credits", {}).get("balance")
    after_credit = after_bucket.get("credits", {}).get("balance")
    if before_credit is not None and after_credit is not None and float(after_credit) < float(before_credit):
        raise RuntimeError("구매 크레딧 잔액이 감소해 추가 호출을 중단합니다.")
    write_json(cache, {"status": "received", "role": role, "settings": settings,
                       "cli_version": version, "usage_before": before, "usage_after": after,
                       "output": output, "finished_unix": time.time()})
    return output


