"""LLM 호출. LLM_MODE=mock 이면 임시 응답, http 이면 OpenAI 호환 엔드포인트를 스트리밍 호출한다.

모델 서버가 준비되면 LLM_MODE=http 와 LLM_BASE_URL / LLM_MODEL 만 채우면 된다.
하네스(시스템 프롬프트) 연결은 model/harness 가 정리되면 SYSTEM_PROMPT 를 교체한다.
"""

import asyncio
import json
import time
import weakref
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

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
    """모델 호출 실패. code 는 SSE error 이벤트의 code 로 그대로 나간다."""

    code = "llm_unavailable"


class LLMBusy(LLMError):
    """동시 호출 제한에 걸림 (모델 서버를 보호하려고 일부러 거절)."""

    code = "llm_busy"


class LLMTimeout(LLMError):
    code = "llm_timeout"


# --- 동시 호출 제한 ---------------------------------------------------------
# 모델 서버(GPU)는 한꺼번에 받을 수 있는 요청이 한정돼 있어서, 몰리면 모두가 느려진다.
# 자리가 없으면 잠깐 기다리게 하고, 기다리는 줄도 길어지면 바로 거절해서 "이용자가 많아요"로 안내한다.
# 대화 응답과 회기 요약은 따로 센다 (요약이 대화 응답 자리를 다 차지하지 않도록).


class _Limiter:
    def __init__(self, limit: int):
        self.sem = asyncio.Semaphore(max(1, limit))
        self.waiting = 0


# asyncio.Semaphore 는 이벤트 루프에 묶이므로 루프별로 만든다.
_limiters: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, dict[str, _Limiter]]" = (
    weakref.WeakKeyDictionary()
)


def reset_limiters() -> None:
    """설정을 바꾼 뒤(주로 테스트) 제한 상태를 처음부터 다시 만든다."""
    _limiters.clear()


def _limiter(name: str, limit: int) -> _Limiter:
    per_loop = _limiters.setdefault(asyncio.get_running_loop(), {})
    if name not in per_loop:
        per_loop[name] = _Limiter(limit)
    return per_loop[name]


@asynccontextmanager
async def _slot(name: str, limit: int, max_queue: int, wait: float) -> AsyncIterator[None]:
    lim = _limiter(name, limit)
    if lim.sem.locked():  # 자리가 모두 찼다
        if lim.waiting >= max_queue:
            raise LLMBusy("지금 이용하는 분이 많아요. 잠시 후 다시 시도해 주세요.")
        lim.waiting += 1
        try:
            await asyncio.wait_for(lim.sem.acquire(), wait)
        except TimeoutError:
            raise LLMBusy("지금 이용하는 분이 많아요. 잠시 후 다시 시도해 주세요.") from None
        finally:
            lim.waiting -= 1
    else:
        await lim.sem.acquire()
    try:
        yield
    finally:
        lim.sem.release()


async def _with_timeouts(
    source: AsyncIterator[str], first: float, idle: float, total: float
) -> AsyncIterator[str]:
    """글자 조각 스트림에 시간 제한을 건다.

    첫 조각은 first 초, 이후 조각 사이는 idle 초, 전체는 total 초 안에 와야 한다.
    """
    deadline = time.monotonic() + total
    it = source.__aiter__()
    got_first = False
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise LLMTimeout("모델 응답이 너무 오래 걸려요. 잠시 후 다시 시도해 주세요.")
            limit = min(idle if got_first else first, remaining)
            try:
                chunk = await asyncio.wait_for(it.__anext__(), limit)
            except StopAsyncIteration:
                return
            except TimeoutError:
                raise LLMTimeout(
                    "모델 응답이 너무 오래 걸려요. 잠시 후 다시 시도해 주세요."
                ) from None
            got_first = True
            yield chunk
    finally:
        aclose = getattr(it, "aclose", None)
        if aclose is not None:
            await aclose()


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
    source = _stream_http(history, memory) if settings.llm_mode == "http" else _stream_mock()
    async with _slot(
        "chat", settings.llm_max_concurrent, settings.llm_max_queue, settings.llm_queue_wait_seconds
    ):
        async for delta in _with_timeouts(
            source,
            first=settings.llm_first_token_timeout,
            idle=settings.llm_idle_timeout,
            total=settings.llm_total_timeout,
        ):
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
            httpx.AsyncClient(
                timeout=httpx.Timeout(
                    settings.llm_first_token_timeout, connect=10.0, write=10.0, pool=10.0
                )
            ) as client,
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
    except httpx.TimeoutException as exc:
        raise LLMTimeout("모델 응답이 너무 오래 걸려요. 잠시 후 다시 시도해 주세요.") from exc
    except httpx.HTTPError as exc:
        raise LLMError("모델 서버에 연결하지 못했습니다.") from exc


async def complete(system: str, user: str) -> str:
    """스트리밍 없이 한 번에 받는 호출 (회기 요약용)."""
    settings = get_settings()
    async with _slot(
        "summary",
        settings.llm_summary_max_concurrent,
        max_queue=1000,
        wait=settings.llm_summary_queue_wait_seconds,
    ):
        return await _complete(system, user)


async def _complete(system: str, user: str) -> str:
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
    timeout = httpx.Timeout(settings.llm_summary_timeout, connect=10.0, write=10.0, pool=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            res = await client.post(url, headers=headers, json=body)
        if res.status_code != 200:
            raise LLMError(f"모델 서버 응답 오류({res.status_code})")
        return res.json()["choices"][0]["message"]["content"] or ""
    except httpx.TimeoutException as exc:
        raise LLMTimeout("모델 응답이 너무 오래 걸려요.") from exc
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
