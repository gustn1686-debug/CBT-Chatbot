import json

import pytest


def _guest(client) -> dict:
    token = client.post("/api/v1/auth/guest").json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.split("\n"))
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def test_requires_auth(client):
    assert client.get("/api/v1/conversations").status_code == 401
    assert client.post("/api/v1/conversations").status_code == 401


def test_create_list_get_delete(client):
    h = _guest(client)
    created = client.post("/api/v1/conversations", json={}, headers=h)
    assert created.status_code == 201
    cid = created.json()["id"]
    assert created.json()["message_count"] == 0

    listed = client.get("/api/v1/conversations", headers=h).json()
    assert [i["id"] for i in listed["items"]] == [cid]
    assert listed["next_cursor"] is None

    detail = client.get(f"/api/v1/conversations/{cid}", headers=h).json()
    assert detail["messages"] == []

    assert client.delete(f"/api/v1/conversations/{cid}", headers=h).status_code == 204
    assert client.get(f"/api/v1/conversations/{cid}", headers=h).status_code == 404


def test_create_without_body(client):
    h = _guest(client)
    assert client.post("/api/v1/conversations", headers=h).status_code == 201


def test_other_users_conversation_is_forbidden(client):
    a, b = _guest(client), _guest(client)
    cid = client.post("/api/v1/conversations", headers=a).json()["id"]
    for res in (
        client.get(f"/api/v1/conversations/{cid}", headers=b),
        client.delete(f"/api/v1/conversations/{cid}", headers=b),
        client.post(f"/api/v1/conversations/{cid}/messages", json={"content": "hi"}, headers=b),
    ):
        assert res.status_code == 403
        assert res.json()["code"] == "forbidden"


def test_pagination(client):
    h = _guest(client)
    ids = {client.post("/api/v1/conversations", headers=h).json()["id"] for _ in range(3)}
    first = client.get("/api/v1/conversations?limit=2", headers=h).json()
    assert len(first["items"]) == 2 and first["next_cursor"]
    second = client.get(
        f"/api/v1/conversations?limit=2&cursor={first['next_cursor']}", headers=h
    ).json()
    assert len(second["items"]) == 1 and second["next_cursor"] is None
    assert {i["id"] for i in first["items"] + second["items"]} == ids
    assert client.get("/api/v1/conversations?cursor=zzz", headers=h).status_code == 400


def test_chat_stream_and_persist(client):
    h = _guest(client)
    cid = client.post("/api/v1/conversations", headers=h).json()["id"]
    res = client.post(
        f"/api/v1/conversations/{cid}/messages", json={"content": "요즘 잠이 안 와요"}, headers=h
    )
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(res.text)
    assert events[0][0] == "meta"
    assert [e for e, _ in events][-1] == "done"
    assert events[0][1]["crisis"] is False
    streamed = "".join(d["delta"] for e, d in events if e == "token")
    assert streamed

    detail = client.get(f"/api/v1/conversations/{cid}", headers=h).json()
    assert detail["title"] == "요즘 잠이 안 와요"
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][1]["content"] == streamed
    assert detail["messages"][1]["id"] == events[0][1]["message_id"]


def test_crisis_skips_llm(client, monkeypatch):
    from app.services import llm

    async def boom(_):
        raise AssertionError("위기 시에는 LLM 을 호출하면 안 됨")
        yield

    monkeypatch.setattr(llm, "stream_reply", boom)
    h = _guest(client)
    cid = client.post("/api/v1/conversations", headers=h).json()["id"]
    res = client.post(
        f"/api/v1/conversations/{cid}/messages", json={"content": "그냥 죽고  싶어요"}, headers=h
    )
    events = _parse_sse(res.text)
    meta = events[0][1]
    assert meta["crisis"] is True
    assert meta["crisis_resources"][0]["tel"] == "109"
    assert events[-1][0] == "done"
    streamed = "".join(d["delta"] for e, d in events if e == "token")
    assert "109" in streamed and len(streamed) < 100  # 시트와 중복되지 않는 짧은 문구
    detail = client.get(f"/api/v1/conversations/{cid}", headers=h).json()
    assert detail["messages"][1]["crisis"] is True
    assert detail["messages"][1]["content"] == streamed


def test_llm_error_event(client, monkeypatch):
    from app.services import llm

    async def failing(_):
        raise llm.LLMError("모델 서버에 연결하지 못했습니다.")
        yield

    monkeypatch.setattr(llm, "stream_reply", failing)
    h = _guest(client)
    cid = client.post("/api/v1/conversations", headers=h).json()["id"]
    res = client.post(f"/api/v1/conversations/{cid}/messages", json={"content": "안녕"}, headers=h)
    events = _parse_sse(res.text)
    assert [e for e, _ in events] == ["meta", "error"]
    assert events[1][1]["code"] == "llm_unavailable"
    # 빈 assistant 메시지는 남기지 않는다
    detail = client.get(f"/api/v1/conversations/{cid}", headers=h).json()
    assert [m["role"] for m in detail["messages"]] == ["user"]


@pytest.mark.parametrize("content", ["", "   "])
def test_empty_message_rejected(client, content):
    h = _guest(client)
    cid = client.post("/api/v1/conversations", headers=h).json()["id"]
    res = client.post(f"/api/v1/conversations/{cid}/messages", json={"content": content}, headers=h)
    assert res.status_code in (422,)


def test_signup_required_after_limit(client):
    h = _guest(client)
    for _ in range(3):
        cid = client.post("/api/v1/conversations", headers=h).json()["id"]
    res = client.post(f"/api/v1/conversations/{cid}/messages", json={"content": "안녕"}, headers=h)
    assert _parse_sse(res.text)[0][1]["signup_required"] is True
