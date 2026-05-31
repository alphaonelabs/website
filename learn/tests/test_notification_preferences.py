"""
Tests for notification preferences endpoints.
"""

import json
from tests.helpers import load_worker, MockRequest, MockRow, MockDB, make_env, make_stmt

worker = load_worker()
JWT = "test-jwt-secret"


def _parse(resp):
    return json.loads(resp.body)


def _auth_header(uid="uid-1", username="alice", role="member"):
    token = worker.create_token(uid, username, role, JWT)
    return {"Authorization": f"Bearer {token}"}


class TestNotificationPreferences:
    async def test_get_defaults(self):
        stmt = make_stmt(first=None)
        env = make_env(db=MockDB([stmt]), jwt_secret=JWT)
        req = MockRequest(
            method="GET",
            url="http://localhost/api/notification-preferences",
            headers=_auth_header(),
        )
        resp = await worker.api_get_notification_preferences(req, env)
        body = _parse(resp)
        assert resp.status == 200
        assert body["data"]["enrollment_notify"] is True
        assert body["data"]["session_notify"] is True
        assert body["data"]["system_notify"] is True

    async def test_get_requires_auth(self):
        env = make_env(jwt_secret=JWT)
        req = MockRequest(method="GET", url="http://localhost/api/notification-preferences")
        resp = await worker.api_get_notification_preferences(req, env)
        assert resp.status == 401

    async def test_patch_partial_update(self):
        current = MockRow(enrollment_notify=0, session_notify=1, system_notify=1)
        stmt_select = make_stmt(first=current)
        stmt_upsert = make_stmt()
        env = make_env(db=MockDB([stmt_select, stmt_upsert]), jwt_secret=JWT)
        req = MockRequest(
            method="PATCH",
            url="http://localhost/api/notification-preferences",
            headers={**_auth_header(), "Content-Type": "application/json"},
            body=json.dumps({"enrollment_notify": True}),
        )
        resp = await worker.api_patch_notification_preferences(req, env)
        body = _parse(resp)
        assert resp.status == 200
        assert body["data"]["enrollment_notify"] is True
        assert body["data"]["session_notify"] is True
        assert body["data"]["system_notify"] is True
        assert stmt_upsert.bind.called
        assert stmt_upsert.bind.call_args[0] == ("uid-1", 1, 1, 1)

    async def test_patch_invalid_boolean(self):
        env = make_env(jwt_secret=JWT)
        req = MockRequest(
            method="PATCH",
            url="http://localhost/api/notification-preferences",
            headers={**_auth_header(), "Content-Type": "application/json"},
            body=json.dumps({"session_notify": "yes"}),
        )
        resp = await worker.api_patch_notification_preferences(req, env)
        assert resp.status == 400

    async def test_patch_requires_auth(self):
        env = make_env(jwt_secret=JWT)
        req = MockRequest(
            method="PATCH",
            url="http://localhost/api/notification-preferences",
            headers={"Content-Type": "application/json"},
            body=json.dumps({"session_notify": True}),
        )
        resp = await worker.api_patch_notification_preferences(req, env)
        assert resp.status == 401
