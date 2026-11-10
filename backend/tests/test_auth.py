import pytest


def test_guest_token_and_me(client):
    res = client.post("/api/v1/auth/guest")
    assert res.status_code == 200
    body = res.json()
    assert body["kind"] == "guest"
    assert body["expires_in"] == 2592000

    me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json() == {
        "kind": "guest",
        "user": None,
        "usage": {"session_count": 0, "guest_session_limit": 3, "signup_required": False},
    }


def test_me_without_token(client):
    res = client.get("/api/v1/me")
    assert res.status_code == 401
    assert res.json()["code"] == "auth_invalid_token"


def test_me_with_bad_token(client):
    res = client.get("/api/v1/me", headers={"Authorization": "Bearer nope"})
    assert res.status_code == 401
    assert res.json()["code"] == "auth_invalid_token"


REG = {"email": "Ji@Example.com", "password": "abcd1234", "nickname": "지예"}


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_register_and_login(client):
    res = client.post("/api/v1/auth/register", json=REG)
    assert res.status_code == 201
    body = res.json()
    assert body["kind"] == "user"
    assert body["user"]["email"] == "ji@example.com"  # 소문자로 정규화
    assert body["user"]["nickname"] == "지예"

    me = client.get("/api/v1/me", headers=_h(body["access_token"])).json()
    assert me["kind"] == "user" and me["user"]["nickname"] == "지예"

    ok = client.post(
        "/api/v1/auth/login", json={"email": " JI@example.com ", "password": "abcd1234"}
    )
    assert ok.status_code == 200 and ok.json()["user"]["id"] == body["user"]["id"]


def test_register_email_taken(client):
    client.post("/api/v1/auth/register", json={**REG, "email": "dup@example.com"})
    res = client.post("/api/v1/auth/register", json={**REG, "email": "DUP@example.com"})
    assert res.status_code == 409
    assert res.json()["code"] == "email_taken"


def test_login_wrong_credentials(client):
    client.post("/api/v1/auth/register", json={**REG, "email": "w@example.com"})
    for payload in (
        {"email": "w@example.com", "password": "wrong1234"},
        {"email": "nobody@example.com", "password": "abcd1234"},
    ):
        res = client.post("/api/v1/auth/login", json=payload)
        assert res.status_code == 401
        assert res.json()["code"] == "auth_invalid_credentials"


@pytest.mark.parametrize(
    "patch",
    [
        {"email": "not-an-email"},
        {"password": "short1"},
        {"password": "onlyletters"},
        {"password": "12345678"},
        {"nickname": "   "},
    ],
)
def test_register_validation(client, patch):
    res = client.post("/api/v1/auth/register", json={**REG, "email": "v@example.com", **patch})
    assert res.status_code == 422
    assert res.json()["code"] == "validation_error"


def test_guest_cannot_login(client):
    res = client.post("/api/v1/auth/login", json={"email": "x@example.com", "password": "x"})
    assert res.status_code == 401


@pytest.mark.parametrize("path", ["/api/v1/auth/upgrade", "/api/v1/auth/register"])
def test_guest_upgrade_keeps_conversations(client, path):
    guest = client.post("/api/v1/auth/guest").json()["access_token"]
    cid = client.post("/api/v1/conversations", headers=_h(guest)).json()["id"]

    res = client.post(path, json={**REG, "email": f"g{path[-3:]}@example.com"}, headers=_h(guest))
    assert res.status_code == 201
    user_token = res.json()["access_token"]

    # 같은 계정으로 이어져서 대화가 그대로 보인다
    items = client.get("/api/v1/conversations", headers=_h(user_token)).json()["items"]
    assert [i["id"] for i in items] == [cid]
    assert client.get("/api/v1/me", headers=_h(user_token)).json()["kind"] == "user"


def test_upgrade_requires_token_and_guest(client):
    assert client.post("/api/v1/auth/upgrade", json=REG).status_code == 401
    token = client.post("/api/v1/auth/register", json={**REG, "email": "u@example.com"}).json()[
        "access_token"
    ]
    res = client.post(
        "/api/v1/auth/upgrade", json={**REG, "email": "u2@example.com"}, headers=_h(token)
    )
    assert res.status_code == 400


def test_upgrade_email_taken_keeps_guest(client):
    client.post("/api/v1/auth/register", json={**REG, "email": "t@example.com"})
    guest = client.post("/api/v1/auth/guest").json()["access_token"]
    res = client.post(
        "/api/v1/auth/upgrade", json={**REG, "email": "t@example.com"}, headers=_h(guest)
    )
    assert res.status_code == 409
    assert client.get("/api/v1/me", headers=_h(guest)).json()["kind"] == "guest"
