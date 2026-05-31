"""
Tests for notification triggers on register/join/create_session.
"""

import json
from tests.helpers import load_worker, MockRow, MockDB, make_env, make_stmt, json_request

worker = load_worker()
JWT = "test-jwt-secret"


def _auth_header(uid="uid-1", username="alice", role="member"):
    token = worker.create_token(uid, username, role, JWT)
    return {"Authorization": f"Bearer {token}"}


class TestNotificationTriggers:
    async def test_join_creates_notifications(self):
        act = MockRow(id="act-1", title="Activity", host_id="host-1")
        stmt_act = make_stmt(first=act)
        stmt_existing = make_stmt(first=None)
        stmt_insert = make_stmt()
        stmt_participant = make_stmt(first=MockRow(name="v1:"))
        stmt_pref_select_1 = make_stmt(first=None)
        stmt_notif_insert_1 = make_stmt()
        stmt_pref_select_2 = make_stmt(first=None)
        stmt_notif_insert_2 = make_stmt()
        env = make_env(
            db=MockDB([
                stmt_act,
                stmt_existing,
                stmt_insert,
                stmt_participant,
                stmt_pref_select_1,
                stmt_notif_insert_1,
                stmt_pref_select_2,
                stmt_notif_insert_2,
            ]),
            jwt_secret=JWT,
        )
        req = json_request(
            "/api/join",
            {"activity_id": "act-1", "role": "participant"},
            headers=_auth_header(uid="user-1", username="bob"),
        )
        resp = await worker.api_join(req, env)
        assert resp.status == 200
        assert stmt_notif_insert_1.bind.return_value.run.called
        assert stmt_notif_insert_2.bind.return_value.run.called

    async def test_create_session_creates_notifications(self):
        owned = MockRow(id="act-1")
        act_row = MockRow(title="Activity")
        enrollee_rows = [MockRow(user_id="user-2")]
        stmt_owned = make_stmt(first=owned)
        stmt_insert_session = make_stmt()
        stmt_act_title = make_stmt(first=act_row)
        stmt_enrollees = make_stmt(all_results=enrollee_rows)
        stmt_pref_select = make_stmt(first=None)
        stmt_notif_insert = make_stmt()
        env = make_env(
            db=MockDB([
                stmt_owned,
                stmt_insert_session,
                stmt_act_title,
                stmt_enrollees,
                stmt_pref_select,
                stmt_notif_insert,
            ]),
            jwt_secret=JWT,
        )
        req = json_request(
            "/api/sessions",
            {
                "activity_id": "act-1",
                "title": "Session 1",
                "description": "desc",
                "start_time": "2026-05-30 10:00",
                "end_time": "2026-05-30 11:00",
                "location": "Room",
            },
            headers=_auth_header(uid="host-1", username="host"),
        )
        resp = await worker.api_create_session(req, env)
        assert resp.status == 200
        assert stmt_notif_insert.bind.return_value.run.called
