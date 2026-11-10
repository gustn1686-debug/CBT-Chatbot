import json

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Conversation
from app.services import llm, summary


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _guest(client) -> dict:
    return _h(client.post("/api/v1/auth/guest").json()["access_token"])


def _chat(client, h, cid, text):
    return client.post(f"/api/v1/conversations/{cid}/messages", json={"content": text}, headers=h)


def _conv(cid):
    with SessionLocal() as db:
        c = db.get(Conversation, cid)
        return c.summary, c.summary_seq


def test_parse_summary_json_and_fallback():
    ok = summary.parse_summary(
        '앞말 {"situation": "발표", "first_thought": "망했다", "emotions": ["불안", ""], '
        '"findings": "", "alternative": null, "next_action": "숨쉬기"} 뒷말'
    )
    assert ok["situation"] == "발표" and ok["emotions"] == ["불안"] and ok["alternative"] == ""
    broken = summary.parse_summary("그냥 문장으로 답했어요")
    assert broken["situation"] == "그냥 문장으로 답했어요" and broken["emotions"] == []


def test_end_conversation_summarizes_and_hides_it(client):
    h = _guest(client)
    cid = client.post("/api/v1/conversations", headers=h).json()["id"]
    _chat(client, h, cid, "발표 때문에 불안해요")

    assert client.post(f"/api/v1/conversations/{cid}/end", headers=h).status_code == 204
    text, seq = _conv(cid)
    assert json.loads(text)["situation"] == "발표 때문에 불안해요"
    assert seq == 2

    # 사용자에게는 노출하지 않는다
    detail = client.get(f"/api/v1/conversations/{cid}", headers=h).json()
    assert "summary" not in detail
    assert "summary" not in client.get("/api/v1/conversations", headers=h).json()["items"][0]


def test_end_requires_owner(client):
    a, b = _guest(client), _guest(client)
    cid = client.post("/api/v1/conversations", headers=a).json()["id"]
    assert client.post(f"/api/v1/conversations/{cid}/end", headers=b).status_code == 403


def test_new_conversation_catches_up_and_remembers(client, monkeypatch):
    h = _guest(client)
    old = client.post("/api/v1/conversations", headers=h).json()["id"]
    _chat(client, h, old, "직장 상사 때문에 힘들어요")  # 종료 버튼 없이 나감

    new = client.post("/api/v1/conversations", headers=h).json()["id"]  # 백그라운드로 따라잡기
    assert json.loads(_conv(old)[0])["situation"] == "직장 상사 때문에 힘들어요"
    assert _conv(new)[0] is None  # 빈 대화는 요약하지 않는다

    seen = {}

    async def spy(history, memory=None):
        seen["memory"] = memory
        yield "네"

    monkeypatch.setattr(llm, "stream_reply", spy)
    _chat(client, h, new, "안녕하세요")
    assert "직장 상사 때문에 힘들어요" in seen["memory"]


def test_resuming_makes_summary_stale_and_it_is_refreshed(client):
    h = _guest(client)
    cid = client.post("/api/v1/conversations", headers=h).json()["id"]
    _chat(client, h, cid, "첫 이야기")
    client.post(f"/api/v1/conversations/{cid}/end", headers=h)
    assert _conv(cid)[1] == 2

    _chat(client, h, cid, "이어서 이야기")  # 목록에서 이어서 대화
    assert _conv(cid)[1] == 2  # 아직 낡은 요약
    client.post("/api/v1/conversations", headers=h)  # 새 대화 시작 → 따라잡기
    assert _conv(cid)[1] == 4


def test_memory_excludes_current_and_other_users(client, monkeypatch):
    a, b = _guest(client), _guest(client)
    ca = client.post("/api/v1/conversations", headers=a).json()["id"]
    _chat(client, a, ca, "A 의 비밀 이야기")
    client.post(f"/api/v1/conversations/{ca}/end", headers=a)

    seen = {}

    async def spy(history, memory=None):
        seen["memory"] = memory
        yield "네"

    monkeypatch.setattr(llm, "stream_reply", spy)
    cb = client.post("/api/v1/conversations", headers=b).json()["id"]
    _chat(client, b, cb, "안녕")
    assert seen["memory"] is None  # 다른 사용자의 요약은 보이지 않는다

    _chat(client, a, ca, "또 이야기")  # 지금 대화의 요약은 넣지 않는다
    assert seen["memory"] is None


def test_crisis_message_gets_no_memory(client, monkeypatch):
    h = _guest(client)
    old = client.post("/api/v1/conversations", headers=h).json()["id"]
    _chat(client, h, old, "이전 이야기")
    client.post(f"/api/v1/conversations/{old}/end", headers=h)
    new = client.post("/api/v1/conversations", headers=h).json()["id"]

    async def boom(*_):
        raise AssertionError("위기 시에는 LLM 을 부르지 않는다")
        yield

    monkeypatch.setattr(llm, "stream_reply", boom)
    assert _chat(client, h, new, "죽고 싶어요").status_code == 200


def test_delete_all_conversations(client):
    h = _guest(client)
    other = _guest(client)
    for _ in range(2):
        cid = client.post("/api/v1/conversations", headers=h).json()["id"]
        _chat(client, h, cid, "안녕")
    keep = client.post("/api/v1/conversations", headers=other).json()["id"]

    assert client.delete("/api/v1/conversations", headers=h).status_code == 204
    assert client.get("/api/v1/conversations", headers=h).json()["items"] == []
    assert client.get(f"/api/v1/conversations/{keep}", headers=other).status_code == 200
    with SessionLocal() as db:
        assert db.scalars(select(Conversation).where(Conversation.id == cid)).first() is None
