import asyncio
import json

import pytest

from app.core.config import get_settings
from app.services import llm


def _use(monkeypatch, **overrides):
    """설정 일부를 바꾸고 동시 호출 제한 상태를 새로 만든다."""
    settings = get_settings().model_copy(update=overrides)
    monkeypatch.setattr(llm, "get_settings", lambda: settings)
    llm.reset_limiters()


def _gated_mock(monkeypatch, gate: asyncio.Event):
    """gate 가 열릴 때까지 첫 글자를 내지 않는 mock 모델."""

    async def stream():
        await gate.wait()
        yield "네"

    monkeypatch.setattr(llm, "_stream_mock", stream)


async def _collect(history=None) -> str:
    return "".join([d async for d in llm.stream_reply(history or [])])


def test_busy_when_slots_and_queue_are_full(monkeypatch):
    _use(monkeypatch, llm_max_concurrent=1, llm_max_queue=0)

    async def run():
        gate = asyncio.Event()
        _gated_mock(monkeypatch, gate)
        first = asyncio.create_task(_collect())
        await asyncio.sleep(0.01)  # first 가 자리를 잡는다
        with pytest.raises(llm.LLMBusy):
            await _collect()
        gate.set()
        assert await first == "네"

    asyncio.run(run())


def test_waits_for_a_free_slot(monkeypatch):
    _use(monkeypatch, llm_max_concurrent=1, llm_max_queue=1, llm_queue_wait_seconds=2)

    async def run():
        gate = asyncio.Event()
        _gated_mock(monkeypatch, gate)
        first = asyncio.create_task(_collect())
        await asyncio.sleep(0.01)
        second = asyncio.create_task(_collect())  # 줄을 서서 기다린다
        await asyncio.sleep(0.01)
        assert not second.done()
        gate.set()
        assert await first == "네" and await second == "네"

    asyncio.run(run())


def test_busy_when_waiting_too_long(monkeypatch):
    _use(monkeypatch, llm_max_concurrent=1, llm_max_queue=1, llm_queue_wait_seconds=0.05)

    async def run():
        gate = asyncio.Event()
        _gated_mock(monkeypatch, gate)
        first = asyncio.create_task(_collect())
        await asyncio.sleep(0.01)
        with pytest.raises(llm.LLMBusy):
            await _collect()
        gate.set()
        await first

    asyncio.run(run())


def test_queue_limit_rejects_immediately(monkeypatch):
    _use(monkeypatch, llm_max_concurrent=1, llm_max_queue=1, llm_queue_wait_seconds=5)

    async def run():
        gate = asyncio.Event()
        _gated_mock(monkeypatch, gate)
        first = asyncio.create_task(_collect())
        await asyncio.sleep(0.01)
        waiting = asyncio.create_task(_collect())  # 줄 1칸을 차지
        await asyncio.sleep(0.01)
        started = asyncio.get_running_loop().time()
        with pytest.raises(llm.LLMBusy):
            await _collect()  # 줄이 꽉 차서 기다리지 않고 바로 거절
        assert asyncio.get_running_loop().time() - started < 1
        gate.set()
        await asyncio.gather(first, waiting)

    asyncio.run(run())


def test_slot_is_released_when_client_goes_away(monkeypatch):
    _use(monkeypatch, llm_max_concurrent=1, llm_max_queue=0)

    async def run():
        async def endless():
            while True:
                yield "가"
                await asyncio.sleep(0)

        monkeypatch.setattr(llm, "_stream_mock", endless)
        stream = llm.stream_reply([])
        assert await stream.__anext__() == "가"
        await stream.aclose()  # 사용자가 화면을 닫음

        async def quick():
            yield "나"

        monkeypatch.setattr(llm, "_stream_mock", quick)
        assert await _collect() == "나"  # 자리가 반납돼 바로 쓸 수 있다

    asyncio.run(run())


def test_slot_is_released_after_error(monkeypatch):
    _use(monkeypatch, llm_max_concurrent=1, llm_max_queue=0)

    async def run():
        async def broken():
            raise llm.LLMError("boom")
            yield

        monkeypatch.setattr(llm, "_stream_mock", broken)
        with pytest.raises(llm.LLMError):
            await _collect()

        async def ok():
            yield "다"

        monkeypatch.setattr(llm, "_stream_mock", ok)
        assert await _collect() == "다"

    asyncio.run(run())


def test_summary_and_chat_use_separate_slots(monkeypatch):
    _use(monkeypatch, llm_max_concurrent=1, llm_max_queue=0, llm_summary_max_concurrent=1)

    async def run():
        gate = asyncio.Event()
        _gated_mock(monkeypatch, gate)
        chat = asyncio.create_task(_collect())  # 대화 응답이 자리를 차지한 상태에서도
        await asyncio.sleep(0.01)
        text = await llm.complete("sys", "사용자: 안녕")  # 요약은 막히지 않는다
        assert json.loads(text)["situation"] == "안녕"
        gate.set()
        await chat

    asyncio.run(run())


def test_summaries_run_one_at_a_time(monkeypatch):
    _use(monkeypatch, llm_summary_max_concurrent=1)
    running, peak = 0, 0

    async def slow_complete(system, user):
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.02)
        running -= 1
        return "{}"

    monkeypatch.setattr(llm, "_complete", slow_complete)

    async def run():
        await asyncio.gather(*(llm.complete("s", "u") for _ in range(4)))

    asyncio.run(run())
    assert peak == 1  # 요약이 몰려도 모델에는 한 번에 하나만 간다


# --- 시간 제한 ---------------------------------------------------------------


async def _drain(source, **kw) -> list[str]:
    return [c async for c in llm._with_timeouts(source, **kw)]


def test_first_token_timeout():
    async def never():
        await asyncio.sleep(5)
        yield "x"

    with pytest.raises(llm.LLMTimeout):
        asyncio.run(_drain(never(), first=0.05, idle=5, total=5))


def test_idle_timeout_keeps_what_arrived():
    got = []

    async def stalls():
        yield "하나"
        await asyncio.sleep(5)
        yield "둘"

    async def run():
        async for c in llm._with_timeouts(stalls(), first=1, idle=0.05, total=5):
            got.append(c)

    with pytest.raises(llm.LLMTimeout):
        asyncio.run(run())
    assert got == ["하나"]  # 첫 글자 이후에는 idle 시간이 적용되고, 받은 만큼은 남는다


def test_total_timeout():
    async def steady():
        while True:
            await asyncio.sleep(0.02)
            yield "."

    with pytest.raises(llm.LLMTimeout):
        asyncio.run(_drain(steady(), first=1, idle=1, total=0.1))


def test_no_timeout_for_normal_stream():
    async def normal():
        for c in "안녕":
            yield c

    assert asyncio.run(_drain(normal(), first=1, idle=1, total=5)) == ["안", "녕"]
