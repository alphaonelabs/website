"""
Tests for activities API handlers:
  * api_list_activities()
  * api_create_activity()
  * api_get_activity()
"""

import base64
import json
import pytest
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


def _make_host_token(uid="host-1", username="alice", role="host"):
    return worker.create_token(uid, username, role, JWT)


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# api_list_activities()
# ---------------------------------------------------------------------------

class TestApiListActivities:
    def _req(self, query=""):
        url = f"http://localhost/api/activities{('?' + query) if query else ''}"
        return MockRequest(method="GET", url=url)

    def _activity_row(self, aid="act-1", title="Python 101", atype="course",
                      fmt="self_paced", sched="ongoing"):
        return MockRow(
            id=aid,
            title=title,
            description=_enc("A great course"),
            type=atype,
            format=fmt,
            schedule_type=sched,
            created_at="2024-01-01T00:00:00",
            host_name_enc=_enc("Alice"),
            participant_count=5,
            session_count=2,
        )

    async def test_returns_activities_list(self):
        row = self._activity_row()
        # prepare() call order: list query, then tags query per row
        tags_row = MockRow(name="Python")
        env = make_env(db=MockDB([
            make_stmt(all_results=[row]),   # main query
            make_stmt(all_results=[tags_row]),  # tags for row
        ]))
        r = await worker.api_list_activities(self._req(), env)
        assert r.status == 200
        data = _parse(r)
        assert "activities" in data
        assert len(data["activities"]) == 1
        assert data["activities"][0]["title"] == "Python 101"

    async def test_empty_db_returns_empty_list(self):
        env = make_env(db=MockDB([make_stmt(all_results=[])]))
        r = await worker.api_list_activities(self._req(), env)
        assert _parse(r)["activities"] == []

    async def test_type_filter_applied(self):
        row = self._activity_row(atype="meetup")
        env = make_env(db=MockDB([
            make_stmt(all_results=[row]),
            make_stmt(all_results=[]),
        ]))
        r = await worker.api_list_activities(self._req("type=meetup"), env)
        data = _parse(r)
        assert len(data["activities"]) == 1

    async def test_format_filter_applied(self):
        row = self._activity_row(fmt="live")
        env = make_env(db=MockDB([
            make_stmt(all_results=[row]),
            make_stmt(all_results=[]),
        ]))
        r = await worker.api_list_activities(self._req("format=live"), env)
        data = _parse(r)
        assert len(data["activities"]) == 1

    async def test_type_and_format_filter(self):
        row = self._activity_row()
        env = make_env(db=MockDB([
            make_stmt(all_results=[row]),
            make_stmt(all_results=[]),
        ]))
        r = await worker.api_list_activities(self._req("type=course&format=self_paced"), env)
        assert r.status == 200

    async def test_tag_filter_unknown_tag_returns_empty(self):
        # Tag not found → empty activities
        env = make_env(db=MockDB([make_stmt(first=None)]))
        r = await worker.api_list_activities(self._req("tag=NonExistent"), env)
        data = _parse(r)
        assert data["activities"] == []

    async def test_tag_filter_known_tag(self):
        tag_row = MockRow(id="tag-1")
        act_row = self._activity_row()
        env = make_env(db=MockDB([
            make_stmt(first=tag_row),          # tag lookup
            make_stmt(all_results=[act_row]),  # filtered activity query
            make_stmt(all_results=[]),         # tags for activity
        ]))
        r = await worker.api_list_activities(self._req("tag=Python"), env)
        data = _parse(r)
        assert len(data["activities"]) == 1

    async def test_search_filter_matches_title(self):
        row = self._activity_row(title="Python for Beginners")
        env = make_env(db=MockDB([
            make_stmt(all_results=[row]),
            make_stmt(all_results=[]),
        ]))
        r = await worker.api_list_activities(self._req("q=python"), env)
        data = _parse(r)
        assert len(data["activities"]) == 1

    async def test_search_filter_no_match(self):
        row = self._activity_row(title="Python for Beginners")
        env = make_env(db=MockDB([
            make_stmt(all_results=[row]),
            make_stmt(all_results=[]),
        ]))
        r = await worker.api_list_activities(self._req("q=javascript"), env)
        # "javascript" not in "Python for Beginners" → filtered out
        data = _parse(r)
        assert data["activities"] == []

    async def test_activity_fields_present(self):
        row = self._activity_row()
        env = make_env(db=MockDB([
            make_stmt(all_results=[row]),
            make_stmt(all_results=[]),
        ]))
        r = await worker.api_list_activities(self._req(), env)
        act = _parse(r)["activities"][0]
        for field in ("id", "title", "description", "type", "format",
                      "schedule_type", "host_name", "participant_count",
                      "session_count", "tags", "created_at"):
            assert field in act, f"Missing field: {field}"

    async def test_missing_table_initializes_schema_and_retries(self):
        row = self._activity_row()

        failing_stmt = make_stmt()
        failing_stmt.all.side_effect = Exception("D1_ERROR: no such table: activities: SQLITE_ERROR")
        ddl_count = len(worker._DDL)

        env = make_env(db=MockDB(
            [failing_stmt]                      # first list query fails
            + [make_stmt() for _ in range(ddl_count)] # init_db DDL statements
            + [
                make_stmt(all_results=[row]),   # retried list query succeeds
                make_stmt(all_results=[]),      # tags query
            ]
        ))

        r = await worker.api_list_activities(self._req(), env)
        assert r.status == 200
        data = _parse(r)
        assert len(data["activities"]) == 1
        assert data["activities"][0]["id"] == row.id

    async def test_non_missing_table_error_is_raised(self):
        failing_stmt = make_stmt()
        failing_stmt.all.side_effect = Exception("DB unavailable")
        env = make_env(db=MockDB([failing_stmt]))

        with pytest.raises(Exception, match="DB unavailable"):
            await worker.api_list_activities(self._req(), env)


# ---------------------------------------------------------------------------
# api_create_activity()
# ---------------------------------------------------------------------------

class TestApiCreateActivity:
    def _req(self, payload, token=None):
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return json_request("/api/activities", payload, headers=headers)

    async def test_no_auth_returns_401(self):
        env = make_env()
        r = await worker.api_create_activity(self._req({"title": "My Course"}), env)
        assert r.status == 401

    async def test_missing_title_returns_400(self):
        token = _make_host_token()
        env = make_env()
        r = await worker.api_create_activity(self._req({"description": "no title"}, token), env)
        assert r.status == 400

    async def test_successful_creation(self):
        token = _make_host_token()
        env = make_env(db=MockDB([make_stmt()]))  # INSERT run()
        r = await worker.api_create_activity(
            self._req({"title": "New Course", "description": "Awesome"}, token), env
        )
        assert r.status == 200
        data = _parse(r)
        assert data["success"] is True
        assert data["data"]["title"] == "New Course"
        assert "id" in data["data"]

    async def test_invalid_type_defaults_to_course(self):
        token = _make_host_token()
        env = make_env(db=MockDB([make_stmt()]))
        r = await worker.api_create_activity(
            self._req({"title": "T", "type": "invalid_type"}, token), env
        )
        assert r.status == 200

    async def test_invalid_format_defaults_to_self_paced(self):
        token = _make_host_token()
        env = make_env(db=MockDB([make_stmt()]))
        r = await worker.api_create_activity(
            self._req({"title": "T", "format": "invalid"}, token), env
        )
        assert r.status == 200

    async def test_tags_are_created(self):
        token = _make_host_token()
        # Stmts: INSERT activity, tag lookup (not found), INSERT tag, INSERT activity_tag
        tag_stmt = make_stmt(first=None)  # tag not found
        env = make_env(db=MockDB([
            make_stmt(),   # INSERT activity
            tag_stmt,      # SELECT tag WHERE name=?
            make_stmt(),   # INSERT tag
            make_stmt(),   # INSERT activity_tags
        ]))
        r = await worker.api_create_activity(
            self._req({"title": "T", "tags": ["Python"]}, token), env
        )
        assert r.status == 200

    async def test_existing_tags_reused(self):
        token = _make_host_token()
        existing_tag = MockRow(id="tag-existing")
        env = make_env(db=MockDB([
            make_stmt(),               # INSERT activity
            make_stmt(first=existing_tag),  # SELECT tag WHERE name=? → found
            make_stmt(),               # INSERT activity_tags
        ]))
        r = await worker.api_create_activity(
            self._req({"title": "T", "tags": ["Python"]}, token), env
        )
        assert r.status == 200

    async def test_db_error_returns_500(self):
        token = _make_host_token()
        stmt = make_stmt()
        stmt.bind.return_value.run.side_effect = Exception("DB error")
        env = make_env(db=MockDB([stmt]))
        r = await worker.api_create_activity(
            self._req({"title": "Course"}, token), env
        )
        assert r.status == 500

    async def test_invalid_json_returns_400(self):
        token = _make_host_token()
        req = MockRequest(method="POST", url="http://localhost/api/activities",
                          headers={"Authorization": f"Bearer {token}"},
                          body="not-json")
        r = await worker.api_create_activity(req, make_env())
        assert r.status == 400


# ---------------------------------------------------------------------------
# api_get_activity()
# ---------------------------------------------------------------------------

class TestApiGetActivity:
    def _req(self, act_id="act-1", token=None):
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return MockRequest(method="GET",
                           url=f"http://localhost/api/activities/{act_id}",
                           headers=headers)

    def _activity_row(self, host_uid="host-1"):
        return MockRow(
            id="act-1",
            title="Python 101",
            description=_enc("Great course"),
            type="course",
            format="self_paced",
            schedule_type="ongoing",
            created_at="2024-01-01",
            host_name_enc=_enc("Alice"),
            host_uid=host_uid,
        )

    def _count_row(self, cnt=3):
        return MockRow(cnt=cnt)

    async def test_not_found_returns_404(self):
        env = make_env(db=MockDB([make_stmt(first=None)]))
        r = await worker.api_get_activity("bad-id", self._req("bad-id"), env)
        assert r.status == 404

    async def test_unauthenticated_access_returns_activity(self):
        act = self._activity_row()
        sessions_row = MockRow(
            id="ses-1", title="Intro", description=_enc("desc"),
            start_time="2024-01-01", end_time="2024-01-01", location=_enc("online"),
        )
        count = self._count_row()
        env = make_env(db=MockDB([
            make_stmt(first=act),           # SELECT activity
            make_stmt(all_results=[sessions_row]),  # SELECT sessions
            make_stmt(all_results=[]),      # SELECT tags
            make_stmt(first=count),         # COUNT enrollments
        ]))
        r = await worker.api_get_activity("act-1", self._req(), env)
        assert r.status == 200
        data = _parse(r)
        assert "activity" in data
        assert data["is_enrolled"] is False
        assert data["is_host"] is False

    async def test_authenticated_non_enrolled_user(self):
        token = _make_host_token(uid="other-user", role="member")
        act = self._activity_row(host_uid="host-1")
        count = self._count_row()
        env = make_env(db=MockDB([
            make_stmt(first=act),
            make_stmt(first=None),          # enrollment lookup → not enrolled
            make_stmt(all_results=[]),      # sessions
            make_stmt(all_results=[]),      # tags
            make_stmt(first=count),
        ]))
        r = await worker.api_get_activity("act-1", self._req(token=token), env)
        assert r.status == 200
        data = _parse(r)
        assert data["is_enrolled"] is False
        assert data["is_host"] is False

    async def test_host_sees_is_host_true(self):
        token = _make_host_token(uid="host-1", role="host")
        act = self._activity_row(host_uid="host-1")
        count = self._count_row()
        env = make_env(db=MockDB([
            make_stmt(first=act),
            make_stmt(first=None),          # enrollment lookup
            make_stmt(all_results=[]),      # sessions
            make_stmt(all_results=[]),      # tags
            make_stmt(first=count),
        ]))
        r = await worker.api_get_activity("act-1", self._req(token=token), env)
        data = _parse(r)
        assert data["is_host"] is True

    async def test_enrolled_user_sees_is_enrolled_true(self):
        token = _make_host_token(uid="member-1", role="member")
        act = self._activity_row(host_uid="host-1")
        enrollment = MockRow(id="enr-1", role="participant", status="active")
        count = self._count_row()
        env = make_env(db=MockDB([
            make_stmt(first=act),
            make_stmt(first=enrollment),    # enrolled
            make_stmt(all_results=[]),      # sessions
            make_stmt(all_results=[]),      # tags
            make_stmt(first=count),
        ]))
        r = await worker.api_get_activity("act-1", self._req(token=token), env)
        data = _parse(r)
        assert data["is_enrolled"] is True
        assert data["enrollment"]["role"] == "participant"

    async def test_activity_fields_complete(self):
        act = self._activity_row()
        count = self._count_row(cnt=7)
        env = make_env(db=MockDB([
            make_stmt(first=act),
            make_stmt(all_results=[]),
            make_stmt(all_results=[]),
            make_stmt(first=count),
        ]))
        r = await worker.api_get_activity("act-1", self._req(), env)
        activity = _parse(r)["activity"]
        for field in ("id", "title", "description", "type", "format",
                      "schedule_type", "host_name", "participant_count", "tags", "created_at"):
            assert field in activity
        assert activity["participant_count"] == 7
