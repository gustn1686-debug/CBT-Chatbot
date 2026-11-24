"""상담 계획: 계획 만들기 → 회기 마치기 → 회기 요약 → 전체 요약, 예약 알림, 푸시 구독."""

import asyncio
import json
import uuid
from datetime import UTC, datetime
from typing import ClassVar

import httpx
import pytest

from app.core.config import get_settings
from app.db import SessionLocal
from app.models import CounselingPlan, PushSubscription
from app.services import llm, plans, push

API = "/api/v1"
SCHEDULE = {"weekdays": [0, 3], "time": "22:00", "timezone": "Asia/Seoul"}


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _member(client) -> dict:
    email = f"p-{uuid.uuid4().hex[:8]}@example.com"
    res = client.post(
        f"{API}/auth/register", json={"email": email, "password": "abcd1234", "nickname": "a"}
    )
    return _h(res.json()["access_token"])


def _talk(client, h, text="발표가 걱정돼요") -> str:
    cid = client.post(f"{API}/conversations", headers=h).json()["id"]
    client.post(f"{API}/conversations/{cid}/messages", json={"content": text}, headers=h)
    return cid


def _plan(client, h, total=2) -> dict:
    res = client.post(f"{API}/plans", json={**SCHEDULE, "total_sessions": total}, headers=h)
    assert res.status_code == 201, res.text
    return res.json()["plan"]


def test_guest_cannot_make_plan(client):
    guest = _h(client.post(f"{API}/auth/guest").json()["access_token"])
    res = client.post(f"{API}/plans", json={**SCHEDULE, "total_sessions": 3}, headers=guest)
    assert res.status_code == 403 and res.json()["code"] == "member_required"


@pytest.mark.parametrize(
    "body",
    [
        {**SCHEDULE, "total_sessions": 0},
        {**SCHEDULE, "total_sessions": 13},
        {**SCHEDULE, "weekdays": [], "total_sessions": 3},
        {**SCHEDULE, "weekdays": [7], "total_sessions": 3},
        {**SCHEDULE, "time": "24:00", "total_sessions": 3},
        {**SCHEDULE, "timezone": "Mars/Base", "total_sessions": 3},
    ],
)
def test_plan_validation(client, body):
    assert client.post(f"{API}/plans", json=body, headers=_member(client)).status_code == 422


def test_create_and_read_plan(client):
    h = _member(client)
    assert client.get(f"{API}/plans/current", headers=h).json() == {"plan": None}
    plan = _plan(client, h, total=5)
    assert plan["status"] == "active" and plan["completed_sessions"] == 0
    assert plan["schedule_label"] == "매주 월·목 22:00"
    assert plan["next_reminder_at"].endswith("Z")
    assert client.get(f"{API}/plans/current", headers=h).json()["plan"]["id"] == plan["id"]
    # 진행 중인 계획은 하나만
    res = client.post(f"{API}/plans", json={**SCHEDULE, "total_sessions": 3}, headers=h)
    assert res.status_code == 409 and res.json()["code"] == "plan_exists"


def test_update_schedule_and_cancel(client):
    h = _member(client)
    plan = _plan(client, h)
    res = client.patch(
        f"{API}/plans/{plan['id']}",
        json={"weekdays": [0, 1, 2, 3, 4, 5, 6], "time": "08:30", "timezone": "Asia/Seoul"},
        headers=h,
    )
    assert res.json()["plan"]["schedule_label"] == "매일 08:30"
    assert client.post(f"{API}/plans/{plan['id']}/cancel", headers=h).status_code == 200
    assert client.get(f"{API}/plans/current", headers=h).json() == {"plan": None}
    # 다른 사람의 계획은 보이지 않는다
    other = _member(client)
    assert client.post(f"{API}/plans/{plan['id']}/cancel", headers=other).status_code == 404


def test_complete_sessions_then_plan_summary(client):
    h = _member(client)
    _plan(client, h, total=2)

    # 이야기를 나누지 않은 대화는 마칠 수 없다
    empty = client.post(f"{API}/conversations", headers=h).json()["id"]
    res = client.post(f"{API}/conversations/{empty}/complete", headers=h)
    assert res.status_code == 409 and res.json()["code"] == "empty_session"

    first = _talk(client, h, "발표가 걱정돼요")
    res = client.post(f"{API}/conversations/{first}/complete", headers=h)
    assert res.status_code == 200
    body = res.json()
    assert body["session"]["number"] == 1 and body["plan"]["completed_sessions"] == 1
    # 백그라운드 요약은 응답 뒤에 끝나 있다 (mock 모드)
    session = client.get(f"{API}/conversations/{first}/session", headers=h).json()["session"]
    assert session["summary_status"] == "done" and "발표가 걱정돼요" in session["summary"]

    # 두 번 눌러도 같은 회기
    again = client.post(f"{API}/conversations/{first}/complete", headers=h).json()
    assert again["session"]["number"] == 1 and again["plan"]["completed_sessions"] == 1

    # 마친 대화에는 더 보낼 수 없다
    res = client.post(f"{API}/conversations/{first}/messages", json={"content": "더"}, headers=h)
    assert res.status_code == 409 and res.json()["code"] == "session_completed"
    detail = client.get(f"{API}/conversations/{first}", headers=h).json()
    assert detail["session"]["number"] == 1

    second = _talk(client, h, "잠을 못 잤어요")
    body = client.post(f"{API}/conversations/{second}/complete", headers=h).json()
    assert body["session"]["number"] == 2 and body["plan"]["status"] == "completed"

    plan = client.get(f"{API}/plans/current", headers=h).json()["plan"]
    assert plan["status"] == "completed" and plan["next_reminder_at"] is None
    assert plan["summary_status"] == "done"
    assert "1회기" in plan["summary"] and "2회기" in plan["summary"]
    assert [s["number"] for s in plan["sessions"]] == [1, 2]

    # 계획이 끝났으니 더 마칠 회기가 없다. 새 계획을 만들 수 있다.
    third = _talk(client, h)
    assert client.post(f"{API}/conversations/{third}/complete", headers=h).status_code == 409
    assert _plan(client, h, total=3)["completed_sessions"] == 0


def test_summary_failure_can_be_retried(client, monkeypatch):
    h = _member(client)
    _plan(client, h, total=1)
    cid = _talk(client, h)

    async def boom(_messages):
        raise llm.LLMError("x")

    monkeypatch.setattr(llm, "summarize_session", boom)
    client.post(f"{API}/conversations/{cid}/complete", headers=h)
    plan = client.get(f"{API}/plans/current", headers=h).json()["plan"]
    assert plan["sessions"][0]["summary_status"] == "failed"
    assert plan["summary_status"] is None  # 회기 요약이 없으니 전체 요약은 시작도 안 했다

    monkeypatch.undo()
    res = client.post(f"{API}/plans/{plan['id']}/summary/retry", headers=h)
    assert res.status_code == 200
    plan = client.get(f"{API}/plans/current", headers=h).json()["plan"]
    assert plan["sessions"][0]["summary_status"] == "done"
    assert plan["summary_status"] == "done"
    assert plan["summary"] == plan["sessions"][0]["summary"]


def test_session_summary_messages_alternate():
    """모델 요약 입력은 user 로 시작하고 번갈아 와야 한다 (model/README.md §4)."""

    class M:
        def __init__(self, role, content):
            self.role, self.content = role, content

    class C:
        messages: ClassVar[list] = [
            M("assistant", "인사"),
            M("user", "a"),
            M("user", "b"),
            M("assistant", ""),
            M("assistant", "c"),
        ]

    assert plans._session_messages(C()) == [
        {"role": "user", "content": "a\nb"},
        {"role": "assistant", "content": "c"},
    ]


def test_runpod_summary_modes(monkeypatch):
    """RunPod 에는 mode 와 messages/sessions 를 보내고 output.summary 를 읽는다."""
    settings = get_settings().model_copy(
        update={
            "llm_mode": "runpod",
            "runpod_endpoint_url": "https://api.runpod.ai/v2/x",
            "runpod_api_key": "k",
            "runpod_poll_interval": 0,
            "session_summary_prompt": "두 줄로",
            "plan_summary_prompt": "마친 회기를 돌아보세요.",
        }
    )
    monkeypatch.setattr(llm, "get_settings", lambda: settings)
    llm.reset_limiters()
    sent = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/run"):
            sent.append(json.loads(request.content))
            return httpx.Response(200, json={"id": "j"})
        mode = sent[-1]["input"]["mode"]
        return httpx.Response(
            200, json={"status": "COMPLETED", "output": {"mode": mode, "summary": f" {mode} 결과 "}}
        )

    monkeypatch.setattr(
        llm, "_runpod_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    msgs = [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]
    assert asyncio.run(llm.summarize_session(msgs)) == "session_summary 결과"
    assert sent[-1]["input"] == {
        "mode": "session_summary",
        "messages": msgs,
        "summary_prompt": "두 줄로",
    }
    sessions = [{"session_number": 1, "summary": "s1"}, {"session_number": 2, "summary": "s2"}]
    assert asyncio.run(llm.summarize_plan(sessions)) == "plan_summary 결과"
    assert sent[-1]["input"] == {
        "mode": "plan_summary", "sessions": sessions, "summary_prompt": "마친 회기를 돌아보세요."
    }


# --- 예약 시각 -----------------------------------------------------------------


def _fake_plan(**kw) -> CounselingPlan:
    return CounselingPlan(
        **{
            "weekdays": [0, 3],
            "remind_time": "22:00",
            "timezone": "Asia/Seoul",
            "status": "active",
            **kw,
        }
    )


def test_due_slot_and_next_reminder():
    plan = _fake_plan()
    # 2026-11-23 은 월요일. 서울 22:00 = UTC 13:00
    assert plans.due_slot(plan, datetime(2026, 11, 23, 13, 0, tzinfo=UTC), 15) == "2026-11-23 22:00"
    assert plans.due_slot(plan, datetime(2026, 11, 23, 13, 14, tzinfo=UTC), 15) is not None
    assert plans.due_slot(plan, datetime(2026, 11, 23, 13, 15, tzinfo=UTC), 15) is None
    assert plans.due_slot(plan, datetime(2026, 11, 23, 12, 59, tzinfo=UTC), 15) is None
    assert plans.due_slot(plan, datetime(2026, 11, 24, 13, 0, tzinfo=UTC), 15) is None  # 화요일
    # 월요일 22:00 이 지났으면 다음은 목요일 22:00
    nxt = plans.next_reminder(plan, datetime(2026, 11, 23, 13, 0, tzinfo=UTC))
    assert nxt == datetime(2026, 11, 26, 13, 0, tzinfo=UTC)
    assert plans.next_reminder(_fake_plan(status="completed")) is None


def test_reminders_sent_once_per_slot(client, monkeypatch):
    h = _member(client)
    plan = _plan(client, h, total=3)
    client.post(
        f"{API}/push/subscriptions",
        json={"endpoint": "https://push.example/abc", "keys": {"p256dh": "p", "auth": "a"}},
        headers=h,
    )
    settings = get_settings().model_copy(
        update={"vapid_public_key": "pub", "vapid_private_key": "priv"}
    )
    monkeypatch.setattr(push, "get_settings", lambda: settings)
    delivered = []
    monkeypatch.setattr(push, "_send_one", lambda sub, payload: delivered.append(payload) or True)

    monday_22 = datetime(2026, 11, 23, 13, 1, tzinfo=UTC)
    assert asyncio.run(push.send_due_reminders(monday_22)) >= 1
    mine = [p for p in delivered if p["tag"] == f"plan-{plan['id']}"]
    assert len(mine) == 1 and "1회기" in mine[0]["body"]
    # 같은 예약은 다시 보내지 않는다
    delivered.clear()
    asyncio.run(push.send_due_reminders(monday_22))
    assert not [p for p in delivered if p["tag"] == f"plan-{plan['id']}"]


def test_reminder_skipped_if_session_done_today(client, monkeypatch):
    h = _member(client)
    plan = _plan(client, h, total=3)
    cid = _talk(client, h)
    client.post(f"{API}/conversations/{cid}/complete", headers=h)
    with SessionLocal() as db:
        p = db.get(CounselingPlan, plan["id"])
        p.weekdays = list(range(7))
        p.remind_time = datetime.now(UTC).astimezone(plans.ZoneInfo("Asia/Seoul")).strftime("%H:%M")
        db.commit()
    settings = get_settings().model_copy(
        update={"vapid_public_key": "pub", "vapid_private_key": "priv"}
    )
    monkeypatch.setattr(push, "get_settings", lambda: settings)
    asyncio.run(push.send_due_reminders())
    with SessionLocal() as db:
        assert db.get(CounselingPlan, plan["id"]).last_reminded_slot is None


def test_gone_subscription_is_removed(client, monkeypatch):
    h = _member(client)
    endpoint = f"https://push.example/{uuid.uuid4().hex}"
    client.post(
        f"{API}/push/subscriptions",
        json={"endpoint": endpoint, "keys": {"p256dh": "p", "auth": "a"}},
        headers=h,
    )
    settings = get_settings().model_copy(
        update={"vapid_public_key": "pub", "vapid_private_key": "priv"}
    )
    monkeypatch.setattr(push, "get_settings", lambda: settings)
    monkeypatch.setattr(push, "_send_one", lambda sub, payload: False)  # 404/410
    from app.api.v1 import push as push_api

    monkeypatch.setattr(push_api, "get_settings", lambda: settings)
    assert client.post(f"{API}/push/test", headers=h).json() == {"sent": 0}
    with SessionLocal() as db:
        assert db.query(PushSubscription).filter_by(endpoint=endpoint).count() == 0


def test_push_endpoints(client):
    h = _member(client)
    assert client.get(f"{API}/push/public-key").json() == {"public_key": None}
    res = client.post(f"{API}/push/test", headers=h)
    assert res.status_code == 503 and res.json()["code"] == "push_disabled"
    bad = {"endpoint": "http://insecure", "keys": {"p256dh": "p", "auth": "a"}}
    assert client.post(f"{API}/push/subscriptions", json=bad, headers=h).status_code == 422
    endpoint = f"https://push.example/{uuid.uuid4().hex}"
    sub = {"endpoint": endpoint, "keys": {"p256dh": "p", "auth": "a"}}
    assert client.post(f"{API}/push/subscriptions", json=sub, headers=h).status_code == 204
    # 같은 기기에서 다른 계정으로 로그인하면 그 계정으로 옮겨진다
    other = _member(client)
    assert client.post(f"{API}/push/subscriptions", json=sub, headers=other).status_code == 204
    with SessionLocal() as db:
        assert db.query(PushSubscription).filter_by(endpoint=endpoint).count() == 1
    res = client.request(
        "DELETE", f"{API}/push/subscriptions", json={"endpoint": endpoint}, headers=other
    )
    assert res.status_code == 204
    with SessionLocal() as db:
        assert db.query(PushSubscription).filter_by(endpoint=endpoint).count() == 0


def test_deleting_account_removes_plans_and_subscriptions(client):
    h = _member(client)
    me = client.get(f"{API}/me", headers=h).json()
    plan = _plan(client, h)
    cid = _talk(client, h)
    client.post(f"{API}/conversations/{cid}/complete", headers=h)
    client.post(
        f"{API}/push/subscriptions",
        json={
            "endpoint": f"https://push.example/{uuid.uuid4().hex}",
            "keys": {"p256dh": "p", "auth": "a"},
        },
        headers=h,
    )
    res = client.request("DELETE", f"{API}/me", json={"password": "abcd1234"}, headers=h)
    assert res.status_code == 204
    with SessionLocal() as db:
        assert db.get(CounselingPlan, plan["id"]) is None
        assert db.query(PushSubscription).filter_by(user_id=me["user"]["id"]).count() == 0
