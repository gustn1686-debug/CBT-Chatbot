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
