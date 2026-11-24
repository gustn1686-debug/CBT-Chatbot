"""LLM 호출.

- LLM_MODE=mock: 임시 응답
- LLM_MODE=http: OpenAI 호환 엔드포인트를 스트리밍 호출 (LLM_BASE_URL / LLM_MODEL)
- LLM_MODE=runpod: 팀 모델 API(RunPod 서버리스). 작업 제출(/run) → 결과 조회(/status/{id}) 방식이라
  답변이 완성된 뒤에 한꺼번에 오며, 화면에는 조각으로 나눠 흘려 보낸다. (model/README.md)
"""

import asyncio
import json
import time
import weakref
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

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


def summary_supported() -> bool:
    """회기 요약을 만들 수 있는 모델 설정인지. RunPod 는 상담 응답 전용일 수 있어 기본은 끈다."""
    settings = get_settings()
    return not (settings.llm_mode == "runpod" and not settings.runpod_summary_enabled)


async def stream_reply(
    history: list[dict[str, str]], memory: str | None = None
) -> AsyncIterator[str]:
    """history: [{"role": "user"|"assistant", "content": "..."}] (마지막이 이번 사용자 메시지).

    memory: 이전 회기 요약 텍스트. 있으면 시스템 프롬프트에 붙는다.
    """
    settings = get_settings()
    first = settings.llm_first_token_timeout
    total = settings.llm_total_timeout
    if settings.llm_mode == "runpod":
        source = _stream_runpod(history, memory)
        # 답변이 완성될 때까지 아무것도 오지 않으므로, 작업 대기 시간이 곧 "첫 글자까지의 시간"이다.
        first = settings.runpod_job_timeout
        total = max(total, first + 30)
    elif settings.llm_mode == "http":
        source = _stream_http(history, memory)
    else:
        source = _stream_mock()
    async with _slot(
        "chat", settings.llm_max_concurrent, settings.llm_max_queue, settings.llm_queue_wait_seconds
    ):
        async for delta in _with_timeouts(
            source, first=first, idle=settings.llm_idle_timeout, total=total
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


# --- RunPod 서버리스 ----------------------------------------------------------
# POST {endpoint}/run          {"input": {"messages": [...]}}  → {"id": "...", "status": "IN_QUEUE"}
# GET  {endpoint}/status/{id}  → {"status": "COMPLETED", "output": {"reply": "..."}}
_RUNPOD_FAILED = {"FAILED", "CANCELLED", "TIMED_OUT"}
_RUNPOD_MAX_POLL_ERRORS = 3  # 조회가 연달아 이만큼 실패하면 포기한다 (일시적 오류는 넘어간다)


def _runpod_client() -> httpx.AsyncClient:
    """RunPod 호출용 클라이언트. 요청 하나하나는 짧게 끊고, 작업 전체 시간은 바깥에서 제한한다."""
    return httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=10.0))


def _runpod_messages(history: list[dict[str, str]], memory: str | None) -> list[dict[str, str]]:
    messages = list(history)
    if get_settings().runpod_send_system_prompt:
        messages = [{"role": "system", "content": _system(memory)}, *messages]
    return messages


async def _runpod_cancel(client: httpx.AsyncClient, base: str, headers: dict, job_id: str) -> None:
    """우리가 기다리기를 그만둔 작업은 서버에서도 취소해 GPU 를 비운다. (실패해도 무시)"""
    with suppress(Exception):  # 정리 작업이라 실패해도 본 흐름에 영향을 주지 않는다
        await asyncio.wait_for(client.post(f"{base}/cancel/{job_id}", headers=headers), 3)


async def _runpod_reply(messages: list[dict[str, str]]) -> str:
    """상담 답변 (chat 모드). 시간 제한은 호출하는 쪽에서 건다."""
    return await _runpod_job({"messages": messages}, "reply")


async def _runpod_job(job_input: dict, output_key: str) -> str:
    """작업을 제출하고 완료될 때까지 조회해 output[output_key] 를 돌려준다. 시간 제한은 호출하는 쪽에서 건다."""
    settings = get_settings()
    base = settings.runpod_endpoint_url.rstrip("/")
    if not base or not settings.runpod_api_key:
        raise LLMError("RUNPOD_ENDPOINT_URL 또는 RUNPOD_API_KEY 가 설정되지 않았습니다.")
    headers = {"Authorization": f"Bearer {settings.runpod_api_key}"}

    job_id: str | None = None
    done = False
    async with _runpod_client() as client:
        try:
            try:
                res = await client.post(
                    f"{base}/run",
                    headers={**headers, "Content-Type": "application/json"},
                    json={"input": job_input},
                )
            except httpx.TimeoutException as exc:
                raise LLMTimeout(
                    "모델 서버가 응답하지 않아요. 잠시 후 다시 시도해 주세요."
                ) from exc
            except httpx.HTTPError as exc:
                raise LLMError("모델 서버에 연결하지 못했습니다.") from exc
            if res.status_code == 429:
                raise LLMBusy("지금 이용하는 분이 많아요. 잠시 후 다시 시도해 주세요.")
            if res.status_code in (401, 403):
                raise LLMError("모델 서버 인증에 실패했습니다. RUNPOD_API_KEY 를 확인하세요.")
            if res.status_code >= 400:
                raise LLMError(f"모델 서버 응답 오류({res.status_code})")
            try:
                job_id = res.json()["id"]
            except (ValueError, KeyError, TypeError) as exc:
                raise LLMError("모델 서버 응답을 읽지 못했습니다.") from exc

            errors = 0
            while True:
                try:
                    res = await client.get(f"{base}/status/{job_id}", headers=headers)
                    if res.status_code in (401, 403):
                        raise LLMError(
                            "모델 서버 인증에 실패했습니다. RUNPOD_API_KEY 를 확인하세요."
                        )
                    res.raise_for_status()
                    body = res.json()
                    errors = 0
                except LLMError:
                    raise
                except (httpx.HTTPError, ValueError) as exc:
                    errors += 1
                    if errors >= _RUNPOD_MAX_POLL_ERRORS:
                        raise LLMError("모델 서버 결과를 가져오지 못했습니다.") from exc
                    await asyncio.sleep(settings.runpod_poll_interval)
                    continue

                status = body.get("status")
                if status == "COMPLETED":
                    output = body.get("output")
                    reply = output.get(output_key) if isinstance(output, dict) else output
                    if not isinstance(reply, str) or not reply.strip():
                        raise LLMError("모델 서버가 빈 답변을 돌려줬습니다.")
                    done = True
                    return reply
                if status in _RUNPOD_FAILED:
                    done = True
                    raise LLMError(f"모델 서버 작업이 실패했습니다({status}).")
                await asyncio.sleep(settings.runpod_poll_interval)  # IN_QUEUE / IN_PROGRESS
        finally:
            if job_id and not done:  # 시간 초과, 오류, 사용자가 떠난 경우 등
                await _runpod_cancel(client, base, headers, job_id)


async def _stream_runpod(
    history: list[dict[str, str]], memory: str | None = None
) -> AsyncIterator[str]:
    settings = get_settings()
    reply = await _runpod_reply(_runpod_messages(history, memory))
    step = max(1, settings.runpod_stream_chunk_chars)
    for i in range(0, len(reply), step):
        if i and settings.runpod_stream_chunk_delay > 0:
            await asyncio.sleep(settings.runpod_stream_chunk_delay)
        yield reply[i : i + step]


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
    if settings.llm_mode == "runpod":
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        try:
            return await asyncio.wait_for(_runpod_reply(messages), settings.llm_summary_timeout)
        except TimeoutError:
            raise LLMTimeout("모델 응답이 너무 오래 걸려요.") from None
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


# --- 상담 계획: 회기 요약 · 전체 요약 ------------------------------------------------
# RunPod 는 input.mode 로 요약 작업을 고른다 (model/README.md). 결과는 output.summary 문장이다.
# 사용자에게 그대로 보여주므로 JSON 이 아니라 줄바꿈이 있는 짧은 글이다.

SESSION_SUMMARY_SYSTEM = (
    "다음은 CBT 상담 챗봇과 사용자의 한 회기 대화입니다. 사용자에게 보여줄 회기 요약을 한국어 존댓말로 "
    "2~4줄 써 주세요. 오늘 다룬 고민, 알아차린 생각과 감정, 사용자가 해 보기로 한 일을 대화에 있는 "
    "내용만으로 적고, 제안과 실제로 한 일을 구분하세요."
)
PLAN_SUMMARY_SYSTEM = (
    "다음은 한 사용자의 상담 회기별 요약입니다. 회기 전체를 돌아보는 요약을 한국어 존댓말로 3~6줄 써 "
    "주세요. 반복된 주제와 사용자가 보고한 변화를 회기 번호와 함께 적고, 기록에 없는 내용은 지어내지 마세요."
)


async def summarize_session(messages: list[dict[str, str]]) -> str:
    """한 회기 대화 → 사용자용 회기 요약. messages 는 user 로 시작해 번갈아 와야 한다."""
    settings = get_settings()
    job: dict = {"mode": "session_summary", "messages": messages}
    if settings.session_summary_prompt:
        job["summary_prompt"] = settings.session_summary_prompt
    transcript = "\n".join(
        f"{'사용자' if m['role'] == 'user' else '상담사'}: {m['content']}" for m in messages
    )
    return await _summarize(
        job, SESSION_SUMMARY_SYSTEM, transcript, _mock_session_summary(messages)
    )


async def summarize_plan(sessions: list[dict]) -> str:
    """[{"session_number": 1, "summary": "..."}, ...] (1부터 순서대로) → 전체 요약."""
    settings = get_settings()
    job: dict = {"mode": "plan_summary", "sessions": sessions}
    if settings.plan_summary_prompt:
        job["summary_prompt"] = settings.plan_summary_prompt
    text = "\n".join(f"{s['session_number']}회기: {s['summary']}" for s in sessions)
    return await _summarize(job, PLAN_SUMMARY_SYSTEM, text, _mock_plan_summary(sessions))


async def _summarize(job: dict, system: str, text: str, mock: str) -> str:
    settings = get_settings()
    async with _slot(
        "summary",
        settings.llm_summary_max_concurrent,
        max_queue=1000,
        wait=settings.llm_summary_queue_wait_seconds,
    ):
        if settings.llm_mode == "runpod":
            # 서버가 꺼져 있다 켜지는 시간까지 기다릴 수 있게 작업 대기 시간과 요약 시간 중 긴 쪽을 쓴다.
            limit = max(settings.llm_summary_timeout, settings.runpod_job_timeout)
            try:
                result = await asyncio.wait_for(_runpod_job(job, "summary"), limit)
            except TimeoutError:
                raise LLMTimeout("모델 응답이 너무 오래 걸려요.") from None
        elif settings.llm_mode == "http":
            result = await _complete(system, text)
        else:
            await asyncio.sleep(0)
            result = mock
    result = result.strip()
    if not result:
        raise LLMError("모델 서버가 빈 요약을 돌려줬습니다.")
    return result


def _mock_session_summary(messages: list[dict[str, str]]) -> str:
    first = next((m["content"] for m in messages if m["role"] == "user"), "")
    turns = sum(1 for m in messages if m["role"] == "user")
    return (
        f"오늘은 '{first[:40]}'에 대해 이야기를 나누셨어요.\n"
        f"{turns}번 마음을 털어놓으며 그때 떠오른 생각과 감정을 차분히 살펴보셨어요.\n"
        "다음 회기까지 비슷한 순간이 오면 떠오른 생각을 한 줄 적어 보기로 했어요."
    )


def _mock_plan_summary(sessions: list[dict]) -> str:
    lines = [f"{len(sessions)}번의 상담을 끝까지 마치셨어요."]
    lines += [f"{s['session_number']}회기: {s['summary'].splitlines()[0]}" for s in sessions]
    lines.append("회기를 거듭하며 떠오른 생각을 알아차리고 다르게 바라보는 연습을 이어 오셨어요.")
    return "\n".join(lines)
