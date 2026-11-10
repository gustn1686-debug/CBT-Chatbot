from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.models import Conversation, CrisisEvent, Message, User
from app.services.retention import purge_expired


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _guest(client) -> str:
    return client.post("/api/v1/auth/guest").json()["access_token"]


def test_session_no_and_message_seq(client):
    h = _h(_guest(client))
    c1 = client.post("/api/v1/conversations", headers=h).json()["id"]
    c2 = client.post("/api/v1/conversations", headers=h).json()["id"]
    client.delete(f"/api/v1/conversations/{c1}", headers=h)
    # 앞 회기를 지워도 번호가 겹치지 않는다
    c3 = client.post("/api/v1/conversations", headers=h).json()["id"]
    client.post(f"/api/v1/conversations/{c2}/messages", json={"content": "안녕"}, headers=h)
    client.post(f"/api/v1/conversations/{c2}/messages", json={"content": "또 안녕"}, headers=h)

    with SessionLocal() as db:
        nos = {c.id: c.session_no for c in db.scalars(select(Conversation))}
        assert nos[c2] == 2 and nos[c3] == 3
        seqs = [m.seq for m in db.scalars(select(Message).where(Message.conversation_id == c2))]
        assert sorted(seqs) == [1, 2, 3, 4]


def test_member_requires_credentials():
    with SessionLocal() as db:
        db.add(User(is_guest=False))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_upgrade_sets_upgraded_at(client):
    token = _guest(client)
    body = {"email": "up@example.com", "password": "abcd1234", "nickname": "지예"}
    client.post("/api/v1/auth/upgrade", json=body, headers=_h(token))
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "up@example.com"))
        assert user.upgraded_at is not None


def test_crisis_event_is_anonymous(client):
    token = _guest(client)
    h = _h(token)
    cid = client.post("/api/v1/conversations", headers=h).json()["id"]
    before = _crisis_count()
    client.post(f"/api/v1/conversations/{cid}/messages", json={"content": "죽고 싶어요"}, headers=h)
    client.post(
        f"/api/v1/conversations/{cid}/messages", json={"content": "평범한 이야기"}, headers=h
    )
    assert _crisis_count() == before + 1  # 위기 메시지만 기록

    with SessionLocal() as db:
        event = db.scalars(select(CrisisEvent).order_by(CrisisEvent.created_at.desc())).first()
        assert event.user_kind == "guest" and event.category == "self_harm"
        columns = {c.name for c in CrisisEvent.__table__.columns}
        assert not columns & {"user_id", "conversation_id", "content", "email", "ip"}
        user_id = db.scalar(select(User.id).order_by(User.created_at.desc()))
        assert user_id not in event.anon_code


def _crisis_count() -> int:
    with SessionLocal() as db:
        return len(db.scalars(select(CrisisEvent)).all())


def test_purge_expired(client):
    now = datetime.now(UTC)
    old = now - timedelta(days=200)
    with SessionLocal() as db:
        stale_guest = User(is_guest=True, last_active_at=now - timedelta(days=31))
        fresh_guest = User(is_guest=True, last_active_at=now - timedelta(days=29))
        member = User(is_guest=False, email="m@x.com", password_hash="x", last_active_at=now)
        db.add_all([stale_guest, fresh_guest, member])
        db.flush()
        old_conv = Conversation(
            user_id=member.id, session_no=1, updated_at=now - timedelta(days=61)
        )
        new_conv = Conversation(
            user_id=member.id, session_no=2, updated_at=now - timedelta(days=59)
        )
        guest_conv = Conversation(user_id=stale_guest.id, session_no=1)
        db.add_all([old_conv, new_conv, guest_conv])
        db.flush()
        db.add(Message(conversation_id=old_conv.id, seq=1, role="user", content="x"))
        db.add(Message(conversation_id=guest_conv.id, seq=1, role="user", content="x"))
        db.add(
            CrisisEvent(
                anon_code="a", category="c", keyword_version="v1", user_kind="guest", created_at=old
            )
        )
        db.commit()
        ids = (stale_guest.id, fresh_guest.id, member.id, old_conv.id, new_conv.id, guest_conv.id)

        result = purge_expired(db, now)
        assert (result.guests, result.conversations) == (1, 1)
        assert result.crisis_events >= 1

        stale_id, fresh_id, member_id, old_id, new_id, guest_conv_id = ids
        assert db.get(User, stale_id) is None
        assert db.get(Conversation, guest_conv_id) is None
        assert db.get(User, fresh_id) is not None
        assert db.get(User, member_id) is not None  # 회원 계정은 유지
        assert db.get(Conversation, old_id) is None
        assert db.get(Conversation, new_id) is not None
        assert db.scalars(select(Message).where(Message.conversation_id == old_id)).first() is None
