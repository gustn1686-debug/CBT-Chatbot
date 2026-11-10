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


async def stream_reply(history: list[dict[str, str]]) -> AsyncIterator[str]:
    """history: [{"role": "user"|"assistant", "content": "..."}] (마지막이 이번 사용자 메시지)."""
    settings = get_settings()
    if settings.llm_mode == "http":
        async for delta in _stream_http(history):
            yield delta
    else:
        async for delta in _stream_mock():
            yield delta


async def _stream_mock() -> AsyncIterator[str]:
    for i in range(0, len(MOCK_REPLY), 4):
        await asyncio.sleep(0)
        yield MOCK_REPLY[i : i + 4]


async def _stream_http(history: list[dict[str, str]]) -> AsyncIterator[str]:
    settings = get_settings()
    if not settings.llm_base_url:
        raise LLMError("LLM_BASE_URL 이 설정되지 않았습니다.")

    headers = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"
    body = {
        "model": settings.llm_model,
        "stream": True,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *history],
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
