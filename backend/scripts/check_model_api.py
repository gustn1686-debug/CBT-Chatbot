"""모델 API(RunPod 서버리스) 연결 점검 스크립트.

백엔드를 띄우기 전에, 모델 API가 우리 설정(.env)으로 실제로 되는지 한 번에 확인한다.

    cd backend
    source .venv/bin/activate
    python -m scripts.check_model_api              # 기본 점검 (제출 → 조회 → 답변)
    python -m scripts.check_model_api --all        # 2번째 턴, system 메시지, 취소까지 모두 점검

확인하는 것
  1. 설정: LLM_MODE / RUNPOD_ENDPOINT_URL / RUNPOD_API_KEY (키 값은 절대 출력하지 않는다)
  2. 작업 제출(POST /run)과 결과 조회(GET /status/{id}): 상태가 바뀌는 시간, 첫 응답까지 걸린 시간
  3. (선택) 이전 대화를 붙인 2번째 턴, system 메시지를 받는지, 작업 취소(POST /cancel/{id})가 되는지

선택 점검은 모델에 요청을 더 보내므로 GPU 시간을 조금 더 쓴다.
종료 코드: 0 = 점검한 항목이 모두 통과, 1 = 하나라도 실패.
"""

import argparse
import sys
import time
from collections.abc import Callable
from pathlib import Path

import httpx

# `python scripts/check_model_api.py` 로 직접 실행해도 app 을 import 할 수 있게 한다.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings, get_settings

FAILED_STATES = {"FAILED", "CANCELLED", "TIMED_OUT"}
TEST_MESSAGE = "내일 발표가 걱정돼요."
FOLLOW_UP = "첫 문장을 잊어버릴까 봐요."


class Report:
    """점검 결과를 모아서 마지막에 요약한다."""

    def __init__(self, out: Callable[[str], None] = print):
        self.out = out
        self.rows: list[tuple[str, str, str]] = []  # (표시, 항목, 설명)

    def ok(self, name: str, detail: str = "") -> None:
        self.rows.append(("OK", name, detail))
        self.out(f"  [OK]   {name}" + (f" - {detail}" if detail else ""))

    def fail(self, name: str, detail: str, hint: str = "") -> None:
        self.rows.append(("실패", name, detail))
        self.out(f"  [실패] {name} - {detail}")
        if hint:
            self.out(f"         -> {hint}")

    def warn(self, name: str, detail: str) -> None:
        self.rows.append(("주의", name, detail))
        self.out(f"  [주의] {name} - {detail}")

    @property
    def passed(self) -> bool:
        return not any(r[0] == "실패" for r in self.rows)


def _http_hint(status: int) -> str:
    if status in (401, 403):
        return (
            "키가 틀렸거나 권한이 없습니다. 모델팀에 호출용 키를 다시 확인하세요. (RUNPOD_API_KEY)"
        )
    if status == 404:
        return "엔드포인트 주소가 틀렸습니다. RUNPOD_ENDPOINT_URL 을 확인하세요."
    if status == 429:
        return "RunPod 요청 제한에 걸렸습니다. 잠시 뒤 다시 시도하세요."
    if status >= 500:
        return "RunPod 쪽 오류입니다. 잠시 뒤 다시 시도하고, 계속되면 모델팀에 알려 주세요."
    return ""


def submit_and_wait(
    client: httpx.Client,
    base: str,
    headers: dict,
    messages: list[dict],
    *,
    timeout: float,
    poll: float,
    report: Report,
    name: str,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[bool, str, float]:
    """작업을 제출하고 끝날 때까지 조회한다. (성공 여부, 답변, 걸린 시간)을 돌려준다."""
    started = clock()
    try:
        res = client.post(f"{base}/run", headers=headers, json={"input": {"messages": messages}})
    except httpx.HTTPError as exc:
        report.fail(name, f"제출 실패: {type(exc).__name__}", "인터넷 연결과 주소를 확인하세요.")
        return False, "", clock() - started
    if res.status_code != 200:
        report.fail(name, f"제출 실패 (HTTP {res.status_code})", _http_hint(res.status_code))
        return False, "", clock() - started
    try:
        job_id = res.json()["id"]
    except (ValueError, KeyError, TypeError):
        report.fail(
            name, "제출 응답에 작업 ID(id)가 없습니다", "model/README.md 의 형식과 다릅니다."
        )
        return False, "", clock() - started
    report.out(f"         작업 제출됨 (id={job_id[:8]}…, {clock() - started:.1f}초)")

    last_status = None
    errors = 0
    while True:
        elapsed = clock() - started
        if elapsed > timeout:
            report.fail(
                name,
                f"{timeout:.0f}초 안에 끝나지 않았습니다 (마지막 상태: {last_status})",
                "서버가 꺼져 있다 켜지는 중일 수 있습니다. 모델팀에 서버를 켜 둬 달라고 요청하거나 --timeout 을 늘려 보세요.",
            )
            _cancel_quietly(client, base, headers, job_id)
            return False, "", elapsed
        try:
            res = client.get(f"{base}/status/{job_id}", headers=headers)
            if res.status_code != 200:
                raise httpx.HTTPStatusError("status", request=res.request, response=res)
            body = res.json()
            errors = 0
        except (httpx.HTTPError, ValueError) as exc:
            errors += 1
            if errors >= 3:
                report.fail(name, f"결과 조회가 연달아 실패했습니다 ({type(exc).__name__})")
                return False, "", clock() - started
            sleep(poll)
            continue

        status = body.get("status")
        if status != last_status:
            report.out(f"         상태: {status} ({clock() - started:.1f}초)")
            last_status = status
        if status == "COMPLETED":
            output = body.get("output")
            reply = output.get("reply") if isinstance(output, dict) else output
            if not isinstance(reply, str) or not reply.strip():
                report.fail(
                    name,
                    "COMPLETED 인데 output.reply 가 비어 있습니다",
                    "응답 형식을 모델팀에 확인하세요.",
                )
                return False, "", clock() - started
            return True, reply, clock() - started
        if status in FAILED_STATES:
            report.fail(
                name, f"작업이 {status} 로 끝났습니다", "모델 서버 로그를 모델팀에 확인하세요."
            )
            return False, "", clock() - started
        sleep(poll)


def _cancel_quietly(client: httpx.Client, base: str, headers: dict, job_id: str) -> None:
    try:
        client.post(f"{base}/cancel/{job_id}", headers=headers)
    except httpx.HTTPError:
        pass


def run_checks(
    settings: Settings,
    client: httpx.Client,
    *,
    message: str = TEST_MESSAGE,
    timeout: float = 300,
    poll: float = 1.0,
    second_turn: bool = False,
    system: bool = False,
    check_cancel: bool = False,
    out: Callable[[str], None] = print,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> bool:
    report = Report(out)
    out("1) 설정 확인")
    if settings.llm_mode != "runpod":
        report.warn(
            "LLM_MODE",
            f"현재 '{settings.llm_mode}' 입니다. 백엔드가 이 모델 API를 쓰려면 .env 에 LLM_MODE=runpod 가 필요합니다.",
        )
    else:
        report.ok("LLM_MODE", "runpod")
    base = settings.runpod_endpoint_url.rstrip("/")
    if base:
        report.ok("RUNPOD_ENDPOINT_URL", base)
    else:
        report.fail(
            "RUNPOD_ENDPOINT_URL",
            "비어 있습니다",
            "model/README.md 의 API 주소를 루트 .env 에 넣으세요.",
        )
    if settings.runpod_api_key:
        report.ok(
            "RUNPOD_API_KEY", f"설정됨 (길이 {len(settings.runpod_api_key)}, 값은 출력하지 않음)"
        )
    else:
        report.fail(
            "RUNPOD_API_KEY", "비어 있습니다", "모델팀에게 받은 호출용 키를 루트 .env 에 넣으세요."
        )
    if not report.passed:
        return _finish(report, settings, None)

    headers = {
        "Authorization": f"Bearer {settings.runpod_api_key}",
        "Content-Type": "application/json",
    }
    history = [{"role": "user", "content": message}]

    out("\n2) 작업 제출 → 결과 조회 (첫 요청이라 서버가 켜지는 시간이 포함될 수 있습니다)")
    ok, reply, elapsed = submit_and_wait(
        client, base, headers, history, timeout=timeout, poll=poll, report=report,
        name="상담 응답", clock=clock, sleep=sleep,
    )  # fmt: skip
    if not ok:
        return _finish(report, settings, None)
    report.ok("상담 응답", f"{elapsed:.1f}초 만에 답변을 받았습니다")
    out(f"         보낸 말: {message}")
    out(f"         받은 답: {reply[:200]}{'…' if len(reply) > 200 else ''}")

    if second_turn:
        out("\n3) 2번째 턴 (이전 대화를 붙여 보내기)")
        history2 = [
            *history,
            {"role": "assistant", "content": reply},
            {"role": "user", "content": FOLLOW_UP},
        ]
        ok2, reply2, elapsed2 = submit_and_wait(
            client, base, headers, history2, timeout=timeout, poll=poll, report=report,
            name="2번째 턴", clock=clock, sleep=sleep,
        )  # fmt: skip
        if ok2:
            report.ok("2번째 턴", f"{elapsed2:.1f}초 / 답: {reply2[:80]}")

    if system:
        out("\n4) system 메시지를 받는지 (RUNPOD_SEND_SYSTEM_PROMPT 를 켜도 되는지)")
        msgs = [
            {"role": "system", "content": "항상 존댓말로, 한 번에 한 가지만 질문하세요."},
            *history,
        ]
        ok3, _, _ = submit_and_wait(
            client, base, headers, msgs, timeout=timeout, poll=poll, report=report,
            name="system 메시지", clock=clock, sleep=sleep,
        )  # fmt: skip
        if ok3:
            report.warn(
                "system 메시지",
                "거절 없이 처리됐습니다. 다만 지시가 실제로 반영되는지는 이 점검으로 알 수 없으니 모델팀에 확인하세요.",
            )

    if check_cancel:
        out("\n5) 작업 취소 (POST /cancel/{id}) 가 되는지")
        try:
            res = client.post(f"{base}/run", headers=headers, json={"input": {"messages": history}})
            job_id = res.json()["id"]
            res = client.post(f"{base}/cancel/{job_id}", headers=headers)
            if res.status_code == 200:
                report.ok("작업 취소", f"HTTP 200, 상태: {res.json().get('status')}")
            else:
                report.fail(
                    "작업 취소", f"HTTP {res.status_code}",
                    "취소가 안 돼도 백엔드는 동작하지만, 시간 초과된 작업이 서버에 남을 수 있습니다.",
                )  # fmt: skip
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            report.fail("작업 취소", f"요청 실패 ({type(exc).__name__})")

    return _finish(report, settings, elapsed)


def _finish(report: Report, settings: Settings, first_elapsed: float | None) -> bool:
    out = report.out
    out("\n== 결과 ==")
    if first_elapsed is not None and first_elapsed > settings.runpod_job_timeout * 0.8:
        report.warn(
            "응답 시간",
            f"{first_elapsed:.0f}초 걸렸습니다. 백엔드의 RUNPOD_JOB_TIMEOUT({settings.runpod_job_timeout:.0f}초)에 "
            "가깝거나 넘습니다. 시연 때는 서버를 미리 깨워 두거나 RUNPOD_JOB_TIMEOUT 을 늘리세요.",
        )
    elif first_elapsed is not None:
        out(
            f"  응답 시간 {first_elapsed:.1f}초 (RUNPOD_JOB_TIMEOUT {settings.runpod_job_timeout:.0f}초 안)"
        )
    for mark, name, detail in report.rows:
        if mark != "OK":
            out(f"  [{mark}] {name}: {detail}")
    if report.passed:
        out("  점검한 항목이 모두 통과했습니다. 백엔드를 띄워 화면에서 확인해 보세요.")
        if first_elapsed is not None:
            out(
                "  (서버리스는 한동안 쓰지 않으면 다시 꺼집니다. 시연 직전에 한 번 더 깨워 두세요.)"
            )
    else:
        out("  실패한 항목이 있습니다. 위의 안내를 확인하세요.")
    return report.passed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="모델 API(RunPod 서버리스) 연결 점검")
    parser.add_argument("--message", default=TEST_MESSAGE, help="보내 볼 말")
    parser.add_argument(
        "--timeout", type=float, default=300, help="작업 하나를 기다리는 최대 시간(초). 기본 300"
    )
    parser.add_argument(
        "--second-turn", action="store_true", help="이전 대화를 붙인 2번째 턴도 점검"
    )
    parser.add_argument("--system", action="store_true", help="system 메시지를 받는지도 점검")
    parser.add_argument("--check-cancel", action="store_true", help="작업 취소가 되는지도 점검")
    parser.add_argument("--all", action="store_true", help="위의 선택 점검을 모두 실행")
    args = parser.parse_args(argv)

    settings = get_settings()
    with httpx.Client(timeout=httpx.Timeout(15.0, connect=10.0)) as client:
        ok = run_checks(
            settings,
            client,
            message=args.message,
            timeout=args.timeout,
            poll=max(0.5, settings.runpod_poll_interval),
            second_turn=args.second_turn or args.all,
            system=args.system or args.all,
            check_cancel=args.check_cancel or args.all,
        )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
