"""
Tests for api_join() and api_dashboard().
"""

import base64
import json
from tests.helpers import load_worker, MockRequest, MockRow, MockDB, make_env, make_stmt, json_request

worker = load_worker()

SECRET = "test-encryption-key"
JWT = "test-jwt-secret"


def _parse(resp):
    return json.loads(resp.body)


def _enc(val: str) -> str:
    """Compute mock-AES ciphertext synchronously (IV = 12 zero bytes, ct = plaintext)."""
    iv = b"\x00" * 12
    return "v1:" + base64.b64encode(iv + val.encode("utf-8")).decode("ascii")


def _token(uid="user-1", username="alice", role="member"):
    return worker.create_token(uid, username, role, JWT)


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# api_join()
# ---------------------------------------------------------------------------

class TestApiJoin:
    def _req(self, payload, token=None):
        headers = _auth(token) if token else {}
        return json_request("/api/join", payload, headers=headers)

    async def test_no_auth_returns_401(self):
        r = await worker.api_join(self._req({"activity_id": "act-1"}), make_env())
        assert r.status == 401

    async def test_missing_activity_id_returns_400(self):
        tok = _token()
        r = await worker.api_join(self._req({}, token=tok), make_env())
        assert r.status == 400

    async def test_activity_not_found_returns_404(self):
        tok = _token()
        env = make_env(db=MockDB([make_stmt(first=None)]))
        r = await worker.api_join(self._req({"activity_id": "bad-id"}, token=tok), env)
        assert r.status == 404

    async def test_successful_join(self):
        tok = _token()
        act_row = MockRow(id="act-1")
        env = make_env(db=MockDB([
            make_stmt(first=act_row),  # activity exists
            make_stmt(),               # INSERT enrollment
        ]))
        r = await worker.api_join(self._req({"activity_id": "act-1"}, token=tok), env)
        assert r.status == 200
        assert _parse(r)["success"] is True

    async def test_invalid_role_defaults_to_participant(self):
        tok = _token()
        act_row = MockRow(id="act-1")
        env = make_env(db=MockDB([
            make_stmt(first=act_row),
            make_stmt(),
        ]))
        r = await worker.api_join(
            self._req({"activity_id": "act-1", "role": "invalid"}, token=tok), env
        )
        assert r.status == 200

    async def test_valid_role_instructor(self):
        tok = _token()
        act_row = MockRow(id="act-1")
        env = make_env(db=MockDB([
            make_stmt(first=act_row),
            make_stmt(),
        ]))
        r = await worker.api_join(
            self._req({"activity_id": "act-1", "role": "instructor"}, token=tok), env
        )
        assert r.status == 200

    async def test_db_error_returns_500(self):
        tok = _token()
        act_row = MockRow(id="act-1")
        insert_stmt = make_stmt()
        insert_stmt.bind.return_value.run.side_effect = Exception("DB error")
        env = make_env(db=MockDB([
            make_stmt(first=act_row),
            insert_stmt,
        ]))
        r = await worker.api_join(self._req({"activity_id": "act-1"}, token=tok), env)
        assert r.status == 500

    async def test_invalid_json_returns_400(self):
        tok = _token()
        req = MockRequest(method="POST", url="http://localhost/api/join",
                          headers=_auth(tok), body="not-json")
        r = await worker.api_join(req, make_env())
        assert r.status == 400


# ---------------------------------------------------------------------------
# api_dashboard()
# ---------------------------------------------------------------------------

class TestApiDashboard:
    def _req(self, token=None):
        headers = _auth(token) if token else {}
        return MockRequest(method="GET", url="http://localhost/api/dashboard", headers=headers)

    async def test_no_auth_returns_401(self):
        r = await worker.api_dashboard(self._req(), make_env())
        assert r.status == 401

    async def test_empty_dashboard(self):
        tok = _token(uid="user-1")
        env = make_env(db=MockDB([
            make_stmt(all_results=[]),  # hosted activities
            make_stmt(all_results=[]),  # joined activities
        ]))
        r = await worker.api_dashboard(self._req(tok), env)
        assert r.status == 200
        data = _parse(r)
        assert data["hosted_activities"] == []
        assert data["joined_activities"] == []

    async def test_dashboard_includes_user(self):
        tok = _token(uid="user-1", username="alice", role="member")
        env = make_env(db=MockDB([
            make_stmt(all_results=[]),
            make_stmt(all_results=[]),
        ]))
        r = await worker.api_dashboard(self._req(tok), env)
        data = _parse(r)
        assert "user" in data
        assert data["user"]["username"] == "alice"

    async def test_hosted_activities_returned(self):
        tok = _token(uid="host-1", role="host")
        hosted_row = MockRow(
            id="act-1", title="My Course", type="course",
            format="self_paced", schedule_type="ongoing",
            participant_count=3, session_count=1,
            created_at="2024-01-01",
        )
        env = make_env(db=MockDB([
            make_stmt(all_results=[hosted_row]),  # hosted query
            make_stmt(all_results=[]),             # tags for act-1
            make_stmt(all_results=[]),             # joined query
        ]))
        r = await worker.api_dashboard(self._req(tok), env)
        data = _parse(r)
        assert len(data["hosted_activities"]) == 1
        assert data["hosted_activities"][0]["title"] == "My Course"

    async def test_joined_activities_returned(self):
        tok = _token(uid="member-1")
        joined_row = MockRow(
            id="act-1", title="Python 101", type="course",
            format="self_paced", schedule_type="ongoing",
            enr_role="participant", enr_status="active",
            host_name_enc=_enc("Alice"),
            joined_at="2024-01-01",
        )
        env = make_env(db=MockDB([
            make_stmt(all_results=[]),              # hosted query (empty)
            make_stmt(all_results=[joined_row]),    # joined query
            make_stmt(all_results=[]),              # tags for act-1
        ]))
        r = await worker.api_dashboard(self._req(tok), env)
        data = _parse(r)
        assert len(data["joined_activities"]) == 1
        act = data["joined_activities"][0]
        assert act["title"] == "Python 101"
        assert act["enr_role"] == "participant"
        assert act["host_name"] == "Alice"
