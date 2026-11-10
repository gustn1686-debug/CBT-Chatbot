"""LLM 호출. LLM_MODE=mock 이면 임시 응답, http 이면 OpenAI 호환 엔드포인트를 스트리밍 호출한다.

모델 서버가 준비되면 LLM_MODE=http 와 LLM_BASE_URL / LLM_MODEL 만 채우면 된다.
하네스(시스템 프롬프트) 연결은 model/harness 가 정리되면 SYSTEM_PROMPT 를 교체한다.
"""

import asyncio
import json
from collections.abc import AsyncIterator

import httpx

from app.core.config import get_settings

# 임시 시스템 프롬프트. 하네스 확정 후 교체.
SYSTEM_PROMPT = (
    "당신은 CBT(인지행동치료) 기반으로 사용자의 생각을 함께 정리해 주는 따뜻한 상담 챗봇입니다. "
    "진단이나 처방은 하지 않고, 한 번에 한 가지 질문만 합니다."
)

MOCK_REPLY = (
    "말씀해 주셔서 고마워요. 그 상황에서 어떤 생각이 가장 먼저 떠올랐는지 "
    "조금 더 이야기해 주실 수 있을까요?"
)


class LLMError(Exception):
    pass


def _system(memory: str | None) -> str:
    if not memory:
        return SYSTEM_PROMPT
    return (
        f"{SYSTEM_PROMPT}\n\n[이전 대화 요약 — 사용자가 이전에 나눈 이야기입니다. "
        "자연스럽게 이어가되, 사용자가 먼저 꺼내지 않으면 굳이 되짚지 마세요.]\n" + memory
    )


async def stream_reply(
    history: list[dict[str, str]], memory: str | None = None
) -> AsyncIterator[str]:
    """history: [{"role": "user"|"assistant", "content": "..."}] (마지막이 이번 사용자 메시지).

    memory: 이전 회기 요약 텍스트. 있으면 시스템 프롬프트에 붙는다.
    """
    settings = get_settings()
    if settings.llm_mode == "http":
        async for delta in _stream_http(history, memory):
            yield delta
    else:
        async for delta in _stream_mock():
            yield delta


async def _stream_mock() -> AsyncIterator[str]:
    for i in range(0, len(MOCK_REPLY), 4):
        await asyncio.sleep(0)
        yield MOCK_REPLY[i : i + 4]


async def _stream_http(
    history: list[dict[str, str]], memory: str | None = None
) -> AsyncIterator[str]:
    settings = get_settings()
    if not settings.llm_base_url:
        raise LLMError("LLM_BASE_URL 이 설정되지 않았습니다.")

    headers = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"
    body = {
        "model": settings.llm_model,
        "stream": True,
        "messages": [{"role": "system", "content": _system(memory)}, *history],
    }
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"

    try:
        async with (
            httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client,
            client.stream("POST", url, headers=headers, json=body) as res,
        ):
            if res.status_code != 200:
                raise LLMError(f"모델 서버 응답 오류({res.status_code})")
            async for line in res.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    return
                choices = json.loads(data).get("choices") or []
                delta = choices[0].get("delta", {}).get("content") if choices else None
                if delta:
                    yield delta
    except httpx.HTTPError as exc:
        raise LLMError("모델 서버에 연결하지 못했습니다.") from exc


async def complete(system: str, user: str) -> str:
    """스트리밍 없이 한 번에 받는 호출 (회기 요약용)."""
    settings = get_settings()
    if settings.llm_mode != "http":
        return _mock_complete(user)
    if not settings.llm_base_url:
        raise LLMError("LLM_BASE_URL 이 설정되지 않았습니다.")

    headers = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"
    body = {
        "model": settings.llm_model,
        "stream": False,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
            res = await client.post(url, headers=headers, json=body)
        if res.status_code != 200:
            raise LLMError(f"모델 서버 응답 오류({res.status_code})")
        return res.json()["choices"][0]["message"]["content"] or ""
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        raise LLMError("모델 서버 응답을 읽지 못했습니다.") from exc


def _mock_complete(user: str) -> str:
    """mock 모드: 대화에서 첫 사용자 발화를 '상황'으로 하는 고정 형식 요약."""
    first = next(
        (ln[len("사용자:") :].strip() for ln in user.splitlines() if ln.startswith("사용자:")), ""
    )
    return json.dumps(
        {
            "situation": first[:100],
            "first_thought": "",
            "emotions": [],
            "findings": "",
            "alternative": "",
            "next_action": "",
        },
        ensure_ascii=False,
    )
