"""LLM_MODE=runpod 어댑터 테스트. RunPod 서버는 httpx.MockTransport 로 흉내 낸다. (model/README.md 의 API 형식)"""

import asyncio
import json

import httpx
import pytest

from app.core.config import get_settings
from app.models import Conversation
from app.services import llm, summary

BASE = "https://api.runpod.ai/v2/test-endpoint"
KEY = "test-key-never-real"


def _use(monkeypatch, **overrides):
    settings = get_settings().model_copy(
        update={
            "llm_mode": "runpod",
            "runpod_endpoint_url": BASE,
            "runpod_api_key": KEY,
            "runpod_poll_interval": 0,
            "runpod_stream_chunk_delay": 0,
            **overrides,
        }
    )
    monkeypatch.setattr(llm, "get_settings", lambda: settings)
    llm.reset_limiters()


class FakeRunPod:
    """제출 → 조회(IN_QUEUE, IN_PROGRESS, ...) → 완료를 흉내 내는 가짜 서버. 받은 요청을 기록한다."""

    def __init__(
        self, statuses=None, reply="발표에서 어떤 순간이 가장 걱정되시나요?", run_status=200
    ):
        self.statuses = list(statuses or [{"status": "IN_QUEUE"}, {"status": "IN_PROGRESS"}])
        self.final = {"status": "COMPLETED", "output": {"reply": reply}}
        self.run_status = run_status
        self.requests: list[httpx.Request] = []
        self.polls = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path.endswith("/run"):
            if self.run_status != 200:
                return httpx.Response(self.run_status, json={"error": "x"})
            return httpx.Response(200, json={"id": "job-1", "status": "IN_QUEUE"})
        if "/status/" in path:
            self.polls += 1
            item = self.statuses.pop(0) if self.statuses else self.final
            if isinstance(item, int):
                return httpx.Response(item)
            return httpx.Response(200, json=item)
        if "/cancel/" in path:
            return httpx.Response(200, json={"id": "job-1", "status": "CANCELLED"})
        return httpx.Response(404)

    def install(self, monkeypatch):
        monkeypatch.setattr(
            llm,
            "_runpod_client",
            lambda: httpx.AsyncClient(transport=httpx.MockTransport(self.handler)),
        )

    def sent(self, suffix: str) -> list[httpx.Request]:
        return [r for r in self.requests if r.url.path.endswith(suffix) or suffix in r.url.path]


def _collect(history, memory=None) -> str:
    async def run():
        return "".join([d async for d in llm.stream_reply(history, memory)])

    return asyncio.run(run())


HISTORY = [{"role": "user", "content": "내일 발표가 걱정돼요."}]


def test_submits_job_polls_and_streams_reply_in_chunks(monkeypatch):
    fake = FakeRunPod()
    fake.install(monkeypatch)
    _use(monkeypatch, runpod_stream_chunk_chars=4)

    chunks = []

    async def run():
        async for d in llm.stream_reply(HISTORY):
            chunks.append(d)

    asyncio.run(run())
    assert "".join(chunks) == "발표에서 어떤 순간이 가장 걱정되시나요?"
    assert len(chunks) > 1 and all(
        len(c) <= 4 for c in chunks
    )  # 완성된 답변을 조각으로 나눠 보낸다
    assert fake.polls == 3  # IN_QUEUE, IN_PROGRESS, COMPLETED

    run_req = fake.sent("/run")[0]
    assert run_req.headers["authorization"] == f"Bearer {KEY}"
    assert json.loads(run_req.content) == {
        "input": {"messages": HISTORY}
    }  # 기본은 system 메시지 없음
    assert all(r.headers["authorization"] == f"Bearer {KEY}" for r in fake.requests)


def test_sends_whole_history_for_next_turn(monkeypatch):
    fake = FakeRunPod()
    fake.install(monkeypatch)
    _use(monkeypatch)
    history = [
        {"role": "user", "content": "내일 발표가 걱정돼요."},
        {"role": "assistant", "content": "발표에서 어떤 순간이 가장 걱정되시나요?"},
        {"role": "user", "content": "첫 문장을 잊어버릴까 봐요."},
    ]
    _collect(history)
    assert json.loads(fake.sent("/run")[0].content)["input"]["messages"] == history


def test_system_prompt_and_memory_only_when_enabled(monkeypatch):
    fake = FakeRunPod()
    fake.install(monkeypatch)
    _use(monkeypatch, runpod_send_system_prompt=True)
    _collect(HISTORY, memory="- (2026-11-10) 상황: 직장 상사")
    messages = json.loads(fake.sent("/run")[0].content)["input"]["messages"]
    assert messages[0]["role"] == "system"
    assert "직장 상사" in messages[0]["content"]
    assert messages[1:] == HISTORY


@pytest.mark.parametrize("status", ["FAILED", "CANCELLED", "TIMED_OUT"])
def test_failed_job_is_an_error(monkeypatch, status):
    fake = FakeRunPod(statuses=[{"status": "IN_PROGRESS"}, {"status": status}])
    fake.install(monkeypatch)
    _use(monkeypatch)
    with pytest.raises(llm.LLMError) as exc:
        _collect(HISTORY)
    assert status in str(exc.value)
    assert not fake.sent("/cancel/")  # 이미 끝난 작업은 취소하지 않는다


@pytest.mark.parametrize(
    "final",
    [
        {"status": "COMPLETED", "output": {}},
        {"status": "COMPLETED", "output": {"reply": "   "}},
        {"status": "COMPLETED"},
    ],
)
def test_empty_or_missing_reply_is_an_error(monkeypatch, final):
    fake = FakeRunPod()
    fake.final = final
    fake.install(monkeypatch)
    _use(monkeypatch)
    with pytest.raises(llm.LLMError):
        _collect(HISTORY)


def test_plain_string_output_is_accepted(monkeypatch):
    fake = FakeRunPod()
    fake.final = {"status": "COMPLETED", "output": "문자열 답변"}
    fake.install(monkeypatch)
    _use(monkeypatch)
    assert _collect(HISTORY) == "문자열 답변"


@pytest.mark.parametrize("missing", [{"runpod_api_key": ""}, {"runpod_endpoint_url": ""}])
def test_missing_config_is_an_error(monkeypatch, missing):
    fake = FakeRunPod()
    fake.install(monkeypatch)
    _use(monkeypatch, **missing)
    with pytest.raises(llm.LLMError):
        _collect(HISTORY)
    assert not fake.requests  # 설정이 없으면 요청 자체를 보내지 않는다


def test_auth_failure_does_not_leak_key(monkeypatch):
    fake = FakeRunPod(run_status=401)
    fake.install(monkeypatch)
    _use(monkeypatch)
    with pytest.raises(llm.LLMError) as exc:
        _collect(HISTORY)
    assert KEY not in str(exc.value) and "RUNPOD_API_KEY" in str(exc.value)


def test_rate_limit_is_reported_as_busy(monkeypatch):
    fake = FakeRunPod(run_status=429)
    fake.install(monkeypatch)
    _use(monkeypatch)
    with pytest.raises(llm.LLMBusy):
        _collect(HISTORY)


def test_server_error_on_submit(monkeypatch):
    fake = FakeRunPod(run_status=500)
    fake.install(monkeypatch)
    _use(monkeypatch)
    with pytest.raises(llm.LLMError):
        _collect(HISTORY)


def test_transient_poll_errors_are_tolerated(monkeypatch):
    fake = FakeRunPod(statuses=[500, {"status": "IN_PROGRESS"}, 502])
    fake.install(monkeypatch)
    _use(monkeypatch)
    assert _collect(HISTORY) == "발표에서 어떤 순간이 가장 걱정되시나요?"


def test_repeated_poll_errors_give_up_and_cancel(monkeypatch):
    fake = FakeRunPod(statuses=[500, 500, 500])
    fake.install(monkeypatch)
    _use(monkeypatch)
    with pytest.raises(llm.LLMError):
        _collect(HISTORY)
    assert fake.sent("/cancel/job-1")  # 포기한 작업은 서버에서도 취소


def test_job_timeout_is_a_timeout_and_cancels_the_job(monkeypatch):
    fake = FakeRunPod(statuses=[{"status": "IN_QUEUE"}] * 10_000)  # 영원히 대기열
    fake.install(monkeypatch)
    _use(monkeypatch, runpod_job_timeout=0.2, runpod_poll_interval=0.01)
    with pytest.raises(llm.LLMTimeout):
        _collect(HISTORY)
    assert fake.sent("/cancel/job-1")  # 우리가 기다리기를 그만둔 작업을 서버에서도 취소


def test_user_leaving_cancels_the_job(monkeypatch):
    fake = FakeRunPod(statuses=[{"status": "IN_PROGRESS"}] * 10_000)
    fake.install(monkeypatch)
    _use(monkeypatch, runpod_poll_interval=0.01)

    async def run():
        task = asyncio.create_task(_collect_async())
        await asyncio.sleep(0.1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    async def _collect_async():
        return [d async for d in llm.stream_reply(HISTORY)]

    asyncio.run(run())
    assert fake.sent("/cancel/job-1")


def test_concurrency_limit_applies_to_runpod(monkeypatch):
    fake = FakeRunPod(statuses=[{"status": "IN_PROGRESS"}] * 10_000)
    fake.install(monkeypatch)
    _use(monkeypatch, llm_max_concurrent=1, llm_max_queue=0, runpod_poll_interval=0.01)

    async def run():
        first = asyncio.create_task(_collect_async())
        await asyncio.sleep(0.1)
        with pytest.raises(llm.LLMBusy):
            await _collect_async()
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first

    async def _collect_async():
        return [d async for d in llm.stream_reply(HISTORY)]

    asyncio.run(run())


# --- 회기 요약 ---------------------------------------------------------------


def test_summary_is_off_by_default_in_runpod_mode(monkeypatch):
    fake = FakeRunPod()
    fake.install(monkeypatch)
    _use(monkeypatch)
    assert llm.summary_supported() is False
    asyncio.run(summary.summarize_stale("any-user"))  # 모델을 부르지 않고 조용히 건너뛴다
    assert not fake.requests


def test_summary_can_be_enabled(monkeypatch):
    summary_json = json.dumps({"situation": "발표", "emotions": ["불안"]}, ensure_ascii=False)
    fake = FakeRunPod(reply=summary_json)
    fake.install(monkeypatch)
    _use(monkeypatch, runpod_summary_enabled=True)
    assert llm.summary_supported() is True

    text = asyncio.run(llm.complete("요약해 줘", "사용자: 내일 발표가 걱정돼요."))
    assert json.loads(text)["situation"] == "발표"
    messages = json.loads(fake.sent("/run")[0].content)["input"]["messages"]
    assert [m["role"] for m in messages] == ["system", "user"]


def test_other_modes_keep_summaries(monkeypatch):
    settings = get_settings().model_copy(update={"llm_mode": "http"})
    monkeypatch.setattr(llm, "get_settings", lambda: settings)
    assert llm.summary_supported() is True


# --- API 전체 흐름 -----------------------------------------------------------


def _guest(client) -> dict:
    return {"Authorization": f"Bearer {client.post('/api/v1/auth/guest').json()['access_token']}"}


def test_chat_endpoint_with_runpod(client, monkeypatch):
    fake = FakeRunPod(reply="발표에서 어떤 순간이 가장 걱정되시나요?")
    fake.install(monkeypatch)
    _use(monkeypatch)
    h = _guest(client)
    cid = client.post("/api/v1/conversations", headers=h).json()["id"]

    res = client.post(
        f"/api/v1/conversations/{cid}/messages",
        json={"content": "내일 발표가 걱정돼요."},
        headers=h,
    )
    blocks = [b for b in res.text.strip().split("\n\n")]
    events = [b.split("\n")[0].removeprefix("event: ") for b in blocks]
    assert events[0] == "meta" and events[-1] == "done" and "token" in events
    streamed = "".join(
        json.loads(b.split("\n")[1].removeprefix("data: "))["delta"]
        for b in blocks
        if b.startswith("event: token")
    )
    assert streamed == "발표에서 어떤 순간이 가장 걱정되시나요?"

    detail = client.get(f"/api/v1/conversations/{cid}", headers=h).json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][1]["content"] == streamed  # 실제 답변이 저장돼 다음 턴 이력이 된다

    # 다음 턴: 이전 사용자 발화와 실제 답변이 이력으로 함께 전달된다
    fake.statuses = [{"status": "IN_PROGRESS"}]
    client.post(
        f"/api/v1/conversations/{cid}/messages",
        json={"content": "첫 문장을 잊어버릴까 봐요."},
        headers=h,
    )
    sent = json.loads(fake.sent("/run")[-1].content)["input"]["messages"]
    assert [m["role"] for m in sent] == ["user", "assistant", "user"]
    assert sent[1]["content"] == streamed


@pytest.mark.parametrize(
    ("setup", "code"),
    [
        ({"run_status": 429}, "llm_busy"),
        ({"statuses": [{"status": "FAILED"}]}, "llm_unavailable"),
    ],
)
def test_runpod_errors_become_sse_error_events(client, monkeypatch, setup, code):
    fake = FakeRunPod(**setup)
    fake.install(monkeypatch)
    _use(monkeypatch)
    h = _guest(client)
    cid = client.post("/api/v1/conversations", headers=h).json()["id"]
    res = client.post(f"/api/v1/conversations/{cid}/messages", json={"content": "안녕"}, headers=h)
    assert "event: error" in res.text and f'"code": "{code}"' in res.text


def test_runpod_timeout_becomes_llm_timeout_event(client, monkeypatch):
    fake = FakeRunPod(statuses=[{"status": "IN_QUEUE"}] * 10_000)
    fake.install(monkeypatch)
    _use(monkeypatch, runpod_job_timeout=0.2, runpod_poll_interval=0.01)
    h = _guest(client)
    cid = client.post("/api/v1/conversations", headers=h).json()["id"]
    res = client.post(f"/api/v1/conversations/{cid}/messages", json={"content": "안녕"}, headers=h)
    assert '"code": "llm_timeout"' in res.text
    assert fake.sent("/cancel/job-1")


def test_no_summary_row_changes_when_summary_is_off(client, monkeypatch):
    fake = FakeRunPod()
    fake.install(monkeypatch)
    _use(monkeypatch)
    h = _guest(client)
    cid = client.post("/api/v1/conversations", headers=h).json()["id"]
    client.post(f"/api/v1/conversations/{cid}/messages", json={"content": "안녕"}, headers=h)
    client.post(f"/api/v1/conversations/{cid}/end", headers=h)
    client.post("/api/v1/conversations", headers=h)  # 새 대화 시작 → 따라잡기 시도
    from app.db import SessionLocal

    with SessionLocal() as db:
        c = db.get(Conversation, cid)
        assert c.summary is None and c.summary_seq is None
