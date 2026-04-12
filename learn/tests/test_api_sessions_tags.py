"""
Tests for api_create_session(), api_list_tags(), api_add_activity_tags().
"""

import json
from tests.helpers import load_worker, MockRequest, MockRow, MockDB, make_env, make_stmt, json_request

worker = load_worker()

SECRET = "test-encryption-key"
JWT = "test-jwt-secret"


def _parse(resp):
    return json.loads(resp.body)


def _token(uid="host-1", username="alice", role="host"):
    return worker.create_token(uid, username, role, JWT)


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# api_create_session()
# ---------------------------------------------------------------------------

class TestApiCreateSession:
    def _req(self, payload, token=None):
        headers = _auth(token) if token else {}
        return json_request("/api/sessions", payload, headers=headers)

    async def test_no_auth_returns_401(self):
        r = await worker.api_create_session(self._req({}), make_env())
        assert r.status == 401

    async def test_missing_activity_id_returns_400(self):
        tok = _token()
        r = await worker.api_create_session(self._req({"title": "Intro"}, token=tok), make_env())
        assert r.status == 400

    async def test_missing_title_returns_400(self):
        tok = _token()
        r = await worker.api_create_session(
            self._req({"activity_id": "act-1"}, token=tok), make_env()
        )
        assert r.status == 400

    async def test_activity_not_owned_returns_404(self):
        tok = _token(uid="host-1")
        # SELECT activity WHERE id=? AND host_id=? → not found
        env = make_env(db=MockDB([make_stmt(first=None)]))
        r = await worker.api_create_session(
            self._req({"activity_id": "act-1", "title": "Intro"}, token=tok), env
        )
        assert r.status == 404

    async def test_successful_session_creation(self):
        tok = _token(uid="host-1")
        owned = MockRow(id="act-1")
        env = make_env(db=MockDB([
            make_stmt(first=owned),  # ownership check
            make_stmt(),             # INSERT session
        ]))
        r = await worker.api_create_session(
            self._req({"activity_id": "act-1", "title": "Intro"}, token=tok), env
        )
        assert r.status == 200
        data = _parse(r)
        assert data["success"] is True
        assert "id" in data["data"]

    async def test_full_session_payload(self):
        tok = _token(uid="host-1")
        owned = MockRow(id="act-1")
        env = make_env(db=MockDB([
            make_stmt(first=owned),
            make_stmt(),
        ]))
        r = await worker.api_create_session(
            self._req({
                "activity_id": "act-1",
                "title": "Session 1",
                "description": "Intro to Python",
                "start_time": "2024-06-01 10:00",
                "end_time": "2024-06-01 12:00",
                "location": "Online",
            }, token=tok), env
        )
        assert r.status == 200

    async def test_db_error_returns_500(self):
        tok = _token(uid="host-1")
        owned = MockRow(id="act-1")
        insert_stmt = make_stmt()
        insert_stmt.bind.return_value.run.side_effect = Exception("DB error")
        env = make_env(db=MockDB([
            make_stmt(first=owned),
            insert_stmt,
        ]))
        r = await worker.api_create_session(
            self._req({"activity_id": "act-1", "title": "Intro"}, token=tok), env
        )
        assert r.status == 500

    async def test_invalid_json_returns_400(self):
        tok = _token()
        req = MockRequest(method="POST", url="http://localhost/api/sessions",
                          headers=_auth(tok), body="not-json")
        r = await worker.api_create_session(req, make_env())
        assert r.status == 400


# ---------------------------------------------------------------------------
# api_list_tags()
# ---------------------------------------------------------------------------

class TestApiListTags:
    def _req(self):
        return MockRequest(method="GET", url="http://localhost/api/tags")

    async def test_returns_empty_list_when_no_tags(self):
        env = make_env(db=MockDB([make_stmt(all_results=[])]))
        r = await worker.api_list_tags(self._req(), env)
        assert r.status == 200
        data = _parse(r)
        assert data["tags"] == []

    async def test_returns_tags_list(self):
        tags = [MockRow(id="t-1", name="Python"), MockRow(id="t-2", name="JavaScript")]
        env = make_env(db=MockDB([make_stmt(all_results=tags)]))
        r = await worker.api_list_tags(self._req(), env)
        data = _parse(r)
        assert len(data["tags"]) == 2
        names = [t["name"] for t in data["tags"]]
        assert "Python" in names
        assert "JavaScript" in names

    async def test_each_tag_has_id_and_name(self):
        tags = [MockRow(id="t-1", name="Python")]
        env = make_env(db=MockDB([make_stmt(all_results=tags)]))
        r = await worker.api_list_tags(self._req(), env)
        tag = _parse(r)["tags"][0]
        assert "id" in tag
        assert "name" in tag


# ---------------------------------------------------------------------------
# api_add_activity_tags()
# ---------------------------------------------------------------------------

class TestApiAddActivityTags:
    def _req(self, payload, token=None):
        headers = _auth(token) if token else {}
        return json_request("/api/activity-tags", payload, headers=headers)

    async def test_no_auth_returns_401(self):
        r = await worker.api_add_activity_tags(self._req({}), make_env())
        assert r.status == 401

    async def test_missing_activity_id_returns_400(self):
        tok = _token()
        r = await worker.api_add_activity_tags(self._req({"tags": ["Python"]}, token=tok), make_env())
        assert r.status == 400

    async def test_activity_not_owned_returns_404(self):
        tok = _token(uid="host-1")
        env = make_env(db=MockDB([make_stmt(first=None)]))
        r = await worker.api_add_activity_tags(
            self._req({"activity_id": "act-1", "tags": ["Python"]}, token=tok), env
        )
        assert r.status == 404

    async def test_add_new_tag_to_activity(self):
        tok = _token(uid="host-1")
        owned = MockRow(id="act-1")
        env = make_env(db=MockDB([
            make_stmt(first=owned),     # ownership check
            make_stmt(first=None),      # tag not found
            make_stmt(),                # INSERT tag
            make_stmt(),                # INSERT activity_tags
        ]))
        r = await worker.api_add_activity_tags(
            self._req({"activity_id": "act-1", "tags": ["Python"]}, token=tok), env
        )
        assert r.status == 200

    async def test_add_existing_tag_to_activity(self):
        tok = _token(uid="host-1")
        owned = MockRow(id="act-1")
        existing_tag = MockRow(id="tag-python")
        env = make_env(db=MockDB([
            make_stmt(first=owned),
            make_stmt(first=existing_tag),  # tag found
            make_stmt(),                     # INSERT activity_tags
        ]))
        r = await worker.api_add_activity_tags(
            self._req({"activity_id": "act-1", "tags": ["Python"]}, token=tok), env
        )
        assert r.status == 200

    async def test_empty_tags_list_succeeds(self):
        tok = _token(uid="host-1")
        owned = MockRow(id="act-1")
        env = make_env(db=MockDB([make_stmt(first=owned)]))
        r = await worker.api_add_activity_tags(
            self._req({"activity_id": "act-1", "tags": []}, token=tok), env
        )
        assert r.status == 200

    async def test_invalid_json_returns_400(self):
        tok = _token()
        req = MockRequest(method="POST", url="http://localhost/api/activity-tags",
                          headers=_auth(tok), body="not-json")
        r = await worker.api_add_activity_tags(req, make_env())
        assert r.status == 400
