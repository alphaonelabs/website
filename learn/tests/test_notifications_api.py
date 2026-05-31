"""
Tests for notifications API endpoints.
"""

import base64
import json
from tests.helpers import load_worker, MockRequest, MockRow, MockDB, make_env, make_stmt

worker = load_worker()

JWT = "test-jwt-secret"


def _parse(resp):
    return json.loads(resp.body)


def _enc(val: str) -> str:
    iv = b"\x00" * 12
    return "v1:" + base64.b64encode(iv + val.encode("utf-8")).decode("ascii")


def _auth_header(uid="uid-1", username="alice", role="member"):
    token = worker.create_token(uid, username, role, JWT)
    return {"Authorization": f"Bearer {token}"}


class TestNotificationsApi:
    async def test_list_notifications(self):
        row = MockRow(
            id="n1",
            type="info",
            title=_enc("Welcome"),
            message=_enc("Hi"),
            is_read=0,
            related_id=None,
            created_at="2026-05-30 10:00",
        )
        stmt_list = make_stmt(all_results=[row])
        stmt_count = make_stmt(first=MockRow(cnt=1))
        env = make_env(db=MockDB([stmt_list, stmt_count]), jwt_secret=JWT)
        req = MockRequest(
            method="GET",
            url="http://localhost/api/notifications",
            headers=_auth_header(),
        )
        resp = await worker.api_list_notifications(req, env)
        body = _parse(resp)
        assert resp.status == 200
        assert body["data"]["unread_count"] == 1
        assert body["data"]["notifications"][0]["title"] == "Welcome"

    async def test_list_requires_auth(self):
        env = make_env(jwt_secret=JWT)
        req = MockRequest(method="GET", url="http://localhost/api/notifications")
        resp = await worker.api_list_notifications(req, env)
        assert resp.status == 401

    async def test_unread_count(self):
        stmt = make_stmt(first=MockRow(cnt=3))
        env = make_env(db=MockDB([stmt]), jwt_secret=JWT)
        req = MockRequest(
            method="GET",
            url="http://localhost/api/notifications/unread-count",
            headers=_auth_header(),
        )
        resp = await worker.api_unread_count(req, env)
        body = _parse(resp)
        assert resp.status == 200
        assert body["data"]["unread_count"] == 3

    async def test_unread_count_requires_auth(self):
        env = make_env(jwt_secret=JWT)
        req = MockRequest(method="GET", url="http://localhost/api/notifications/unread-count")
        resp = await worker.api_unread_count(req, env)
        assert resp.status == 401

    async def test_mark_one_read(self):
        stmt_select = make_stmt(first=MockRow(id="n1"))
        stmt_update = make_stmt()
        env = make_env(db=MockDB([stmt_select, stmt_update]), jwt_secret=JWT)
        req = MockRequest(
            method="POST",
            url="http://localhost/api/notifications/n1/read",
            headers=_auth_header(),
        )
        resp = await worker.api_mark_notification_read(req, env, "n1")
        assert resp.status == 200

    async def test_mark_one_read_404(self):
        stmt_select = make_stmt(first=None)
        env = make_env(db=MockDB([stmt_select]), jwt_secret=JWT)
        req = MockRequest(
            method="POST",
            url="http://localhost/api/notifications/bad/read",
            headers=_auth_header(),
        )
        resp = await worker.api_mark_notification_read(req, env, "bad")
        assert resp.status == 404

    async def test_mark_one_requires_auth(self):
        env = make_env(jwt_secret=JWT)
        req = MockRequest(method="POST", url="http://localhost/api/notifications/n1/read")
        resp = await worker.api_mark_notification_read(req, env, "n1")
        assert resp.status == 401

    async def test_mark_all_read(self):
        stmt_update = make_stmt()
        env = make_env(db=MockDB([stmt_update]), jwt_secret=JWT)
        req = MockRequest(
            method="POST",
            url="http://localhost/api/notifications/read-all",
            headers=_auth_header(),
        )
        resp = await worker.api_mark_all_read(req, env)
        assert resp.status == 200

    async def test_mark_all_requires_auth(self):
        env = make_env(jwt_secret=JWT)
        req = MockRequest(method="POST", url="http://localhost/api/notifications/read-all")
        resp = await worker.api_mark_all_read(req, env)
        assert resp.status == 401
