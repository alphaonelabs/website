"""
Tests to ensure join is idempotent and does not trigger notifications twice.
"""

import json
from tests.helpers import load_worker, MockRow, MockDB, make_env, make_stmt, json_request

worker = load_worker()
JWT = "test-jwt-secret"


def _auth_header(uid="user-1", username="alice", role="member"):
    token = worker.create_token(uid, username, role, JWT)
    return {"Authorization": f"Bearer {token}"}


def _parse(resp):
    return json.loads(resp.body)


class TestJoinIdempotent:
    async def test_join_second_time_no_notifications(self):
        act = MockRow(id="act-1", title="Activity", host_id="host-1")
        existing = MockRow(id="enr-1")
        stmt_act = make_stmt(first=act)
        stmt_existing = make_stmt(first=existing)
        env = make_env(db=MockDB([stmt_act, stmt_existing]), jwt_secret=JWT)
        req = json_request(
            "/api/join",
            {"activity_id": "act-1", "role": "participant"},
            headers=_auth_header(),
        )
        resp = await worker.api_join(req, env)
        assert resp.status == 200
        assert _parse(resp)["message"] == "Already joined this activity"
        assert env.DB._idx == 2
