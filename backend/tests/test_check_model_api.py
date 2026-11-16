"""연결 점검 스크립트 테스트. RunPod 는 httpx.MockTransport 로 흉내 낸다."""

import httpx
import pytest

from app.core.config import get_settings
from scripts.check_model_api import main, run_checks

BASE = "https://api.runpod.ai/v2/test-endpoint"
KEY = "secret-key-must-not-be-printed"


def _settings(**kw):
    base = {"llm_mode": "runpod", "runpod_endpoint_url": BASE, "runpod_api_key": KEY}
    return get_settings().model_copy(update={**base, **kw})


class Fake:
    def __init__(self, statuses=None, run_status=200, cancel_status=200, final=None):
        self.statuses = list(statuses or [{"status": "IN_QUEUE"}, {"status": "IN_PROGRESS"}])
        self.final = final or {
            "status": "COMPLETED",
            "output": {"reply": "발표에서 어떤 순간이 걱정되시나요?"},
        }
        self.run_status, self.cancel_status = run_status, cancel_status
        self.calls: list[tuple[str, str]] = []

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.calls.append((req.method, req.url.path))
        if req.url.path.endswith("/run"):
            if self.run_status != 200:
                return httpx.Response(self.run_status, json={"error": "x"})
            return httpx.Response(200, json={"id": "job-12345678", "status": "IN_QUEUE"})
        if "/status/" in req.url.path:
            return httpx.Response(200, json=self.statuses.pop(0) if self.statuses else self.final)
        if "/cancel/" in req.url.path:
            return httpx.Response(self.cancel_status, json={"status": "CANCELLED"})
        return httpx.Response(404)


def _run(settings, fake, **kw):
    lines: list[str] = []
    client = httpx.Client(transport=httpx.MockTransport(fake))
    clock = iter(range(10_000))  # 호출마다 1초씩 흐르는 가짜 시계
    ok = run_checks(
        settings,
        client,
        poll=0,
        out=lines.append,
        clock=lambda: float(next(clock)),
        sleep=lambda s: None,
        **kw,
    )
    return ok, "\n".join(lines)


def test_passes_and_never_prints_the_key():
    ok, out = _run(_settings(), Fake())
    assert ok
    assert "작업 제출됨" in out and "IN_QUEUE" in out and "COMPLETED" in out
    assert "발표에서 어떤 순간이 걱정되시나요?" in out
    assert KEY not in out and "secret-key" not in out  # 키 값은 절대 출력하지 않는다
    assert "설정됨 (길이" in out


@pytest.mark.parametrize(
    ("overrides", "needle"),
    [
        ({"runpod_api_key": ""}, "RUNPOD_API_KEY"),
        ({"runpod_endpoint_url": ""}, "RUNPOD_ENDPOINT_URL"),
    ],
)
def test_missing_settings_fail_without_calling_the_server(overrides, needle):
    fake = Fake()
    ok, out = _run(_settings(**overrides), fake)
    assert not ok and needle in out and "비어 있습니다" in out
    assert fake.calls == []


def test_warns_when_mode_is_not_runpod():
    ok, out = _run(_settings(llm_mode="mock"), Fake())
    assert ok and "LLM_MODE=runpod" in out


@pytest.mark.parametrize(
    ("status", "hint"),
    [
        (401, "키가 틀렸"),
        (403, "키가 틀렸"),
        (404, "주소가 틀렸"),
        (429, "요청 제한"),
        (500, "RunPod 쪽 오류"),
    ],
)
def test_http_errors_give_hints(status, hint):
    ok, out = _run(_settings(), Fake(run_status=status))
    assert not ok and f"HTTP {status}" in out and hint in out
    assert KEY not in out


@pytest.mark.parametrize("state", ["FAILED", "CANCELLED", "TIMED_OUT"])
def test_failed_job(state):
    ok, out = _run(_settings(), Fake(statuses=[{"status": state}]))
    assert not ok and state in out


def test_empty_reply_fails():
    ok, out = _run(_settings(), Fake(final={"status": "COMPLETED", "output": {}}))
    assert not ok and "output.reply" in out


def test_timeout_fails_and_cancels():
    fake = Fake(statuses=[{"status": "IN_QUEUE"}] * 10_000)
    ok, out = _run(_settings(), fake, timeout=20)
    assert not ok and "안에 끝나지 않았습니다" in out
    assert ("POST", "/v2/test-endpoint/cancel/job-12345678") in fake.calls


def test_slow_first_response_warns_about_job_timeout():
    fake = Fake(statuses=[{"status": "IN_QUEUE"}] * 150)
    ok, out = _run(_settings(runpod_job_timeout=120), fake)
    assert ok and "RUNPOD_JOB_TIMEOUT" in out and "미리 깨워" in out


def test_optional_checks_run_only_when_asked():
    fake = Fake()
    _run(_settings(), fake)
    assert sum(1 for m, p in fake.calls if p.endswith("/run")) == 1

    fake = Fake()
    ok, out = _run(_settings(), fake, second_turn=True, system=True, check_cancel=True)
    runs = sum(1 for m, p in fake.calls if p.endswith("/run"))
    assert ok and runs == 4  # 기본 + 2번째 턴 + system + 취소 점검용
    assert ("POST", "/v2/test-endpoint/cancel/job-12345678") in fake.calls
    assert "2번째 턴" in out and "system 메시지" in out and "작업 취소" in out
    assert "실제로 반영되는지는 이 점검으로 알 수 없으니" in out


def test_cancel_failure_is_reported():
    ok, out = _run(_settings(), Fake(cancel_status=404), check_cancel=True)
    assert not ok and "작업 취소" in out and "HTTP 404" in out


def test_main_exit_code(monkeypatch, capsys):
    monkeypatch.setattr(
        "scripts.check_model_api.get_settings", lambda: _settings(runpod_api_key="")
    )
    assert main([]) == 1
    assert "RUNPOD_API_KEY" in capsys.readouterr().out
