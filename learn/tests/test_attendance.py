"""
Tests for session attendance tracking and student participation register.
Covers:
- POST /api/sessions/:id/attendance (host authorization, validation, saving records)
- GET  /api/sessions/:id/attendance (host restriction, student participation register retrieval)
- Attendance percentage calculations in student dashboard (api_dashboard) and activity detail (api_get_activity)
- Non-host permission denial (403) and unauthenticated rejection (401)
- Dispatcher routing for attendance endpoints
"""

import base64
import json
import pytest
from tests.helpers import (
    load_worker,
    MockRequest,
    MockRow,
    MockDB,
    make_env,
    make_stmt,
    json_request,
)

worker = load_worker()

JWT_SECRET = "test-jwt-secret"
ENC_KEY = "test-encryption-key"


def _parse(resp):
    return json.loads(resp.body)


def _token(uid="host-1", username="instructor", role="host"):
    return worker.create_token(uid, username, role, JWT_SECRET)


def _auth(token):
    return {"Authorization": f"Bearer {token}"} if token else {}


def _enc(val: str) -> str:
    """Compute mock-AES ciphertext synchronously (IV = 12 zero bytes, ct = plaintext)."""
    iv = b"\x00" * 12
    return "v1:" + base64.b64encode(iv + val.encode("utf-8")).decode("ascii")


# ---------------------------------------------------------------------------
# POST /api/sessions/:id/attendance
# ---------------------------------------------------------------------------

class TestPostSessionAttendance:
    def _req(self, sid, payload, token=None):
        headers = _auth(token) if token else {}
        return json_request(f"/api/sessions/{sid}/attendance", payload, headers=headers)

    async def test_no_auth_returns_401(self):
        req = self._req("s-1", [{"user_id": "u-1", "status": "attended"}])
        r = await worker.api_record_session_attendance(req, make_env(), "s-1")
        assert r.status == 401
        data = _parse(r)
        assert "Authentication required" in data.get("error", "")

    async def test_session_not_found_returns_404(self):
        tok = _token(uid="host-1")
        env = make_env(db=MockDB([make_stmt(first=None)]))
        req = self._req("nonexistent", [{"user_id": "u-1", "status": "attended"}], token=tok)
        r = await worker.api_record_session_attendance(req, env, "nonexistent")
        assert r.status == 404
        assert "Session not found" in _parse(r).get("error", "")

    async def test_non_host_permission_denial_returns_403(self):
        tok = _token(uid="student-1", role="member")
        session_row = MockRow(id="s-1", activity_id="act-1", title="Week 1", host_id="host-1")
        env = make_env(db=MockDB([make_stmt(first=session_row)]))
        req = self._req("s-1", [{"user_id": "u-1", "status": "attended"}], token=tok)
        r = await worker.api_record_session_attendance(req, env, "s-1")
        assert r.status == 403
        assert "Host access required" in _parse(r).get("error", "")

    async def test_invalid_json_body_returns_400(self):
        tok = _token(uid="host-1")
        session_row = MockRow(id="s-1", activity_id="act-1", title="Week 1", host_id="host-1")
        env = make_env(db=MockDB([make_stmt(first=session_row)]))
        req = MockRequest(
            method="POST",
            url="http://localhost/api/sessions/s-1/attendance",
            headers=_auth(tok),
            body="invalid-json{",
        )
        r = await worker.api_record_session_attendance(req, env, "s-1")
        assert r.status == 400
        assert "Invalid JSON body" in _parse(r).get("error", "")

    async def test_invalid_payload_type_returns_400(self):
        tok = _token(uid="host-1")
        session_row = MockRow(id="s-1", activity_id="act-1", title="Week 1", host_id="host-1")
        env = make_env(db=MockDB([make_stmt(first=session_row)]))
        req = self._req("s-1", {"invalid_key": "not-attendance"}, token=tok)
        r = await worker.api_record_session_attendance(req, env, "s-1")
        assert r.status == 400

    async def test_missing_user_id_returns_400(self):
        tok = _token(uid="host-1")
        session_row = MockRow(id="s-1", activity_id="act-1", title="Week 1", host_id="host-1")
        env = make_env(db=MockDB([make_stmt(first=session_row)]))
        req = self._req("s-1", [{"status": "attended"}], token=tok)
        r = await worker.api_record_session_attendance(req, env, "s-1")
        assert r.status == 400
        assert "user_id is required" in _parse(r).get("error", "")

    async def test_invalid_status_returns_400(self):
        tok = _token(uid="host-1")
        session_row = MockRow(id="s-1", activity_id="act-1", title="Week 1", host_id="host-1")
        env = make_env(db=MockDB([make_stmt(first=session_row)]))
        req = self._req("s-1", [{"user_id": "u-1", "status": "present"}], token=tok)
        r = await worker.api_record_session_attendance(req, env, "s-1")
        assert r.status == 400
        assert "Must be one of: attended, missed, registered" in _parse(r).get("error", "")

    async def test_host_successfully_marks_attendance_direct_list(self):
        tok = _token(uid="host-1")
        session_row = MockRow(id="s-1", activity_id="act-1", title="Week 1", host_id="host-1")
        env = make_env(db=MockDB([
            make_stmt(first=session_row),  # session check
            make_stmt(),                   # upsert u-1
            make_stmt(),                   # upsert u-2
            make_stmt(),                   # upsert u-3
        ]))
        payload = [
            {"user_id": "u-1", "status": "attended"},
            {"user_id": "u-2", "status": "missed"},
            {"user_id": "u-3", "status": "attended"},
        ]
        req = self._req("s-1", payload, token=tok)
        r = await worker.api_record_session_attendance(req, env, "s-1")
        assert r.status == 200
        data = _parse(r)
        assert data["success"] is True
        assert data["updated"] == 3
        assert len(data["records"]) == 3
        assert data["records"][0] == {"user_id": "u-1", "status": "attended"}
        assert data["records"][1] == {"user_id": "u-2", "status": "missed"}
        assert data["records"][2] == {"user_id": "u-3", "status": "attended"}

    async def test_host_successfully_marks_attendance_object_wrapper(self):
        tok = _token(uid="host-1")
        session_row = MockRow(id="s-1", activity_id="act-1", title="Week 1", host_id="host-1")
        env = make_env(db=MockDB([
            make_stmt(first=session_row),
            make_stmt(),
        ]))
        payload = {
            "attendance": [
                {"user_id": "u-1", "status": "attended"}
            ]
        }
        req = self._req("s-1", payload, token=tok)
        r = await worker.api_record_session_attendance(req, env, "s-1")
        assert r.status == 200
        data = _parse(r)
        assert data["success"] is True
        assert data["updated"] == 1

    async def test_host_successfully_undos_attendance_with_registered_status(self):
        tok = _token(uid="host-1")
        session_row = MockRow(id="s-1", activity_id="act-1", title="Week 1", host_id="host-1")
        env = make_env(db=MockDB([
            make_stmt(first=session_row),  # session check
            make_stmt(),                   # delete u-1 from session_attendance
            make_stmt(),                   # delete u-2 from session_attendance
        ]))
        payload = [
            {"user_id": "u-1", "status": "registered"},
            {"user_id": "u-2", "status": "unmarked"},
        ]
        req = self._req("s-1", payload, token=tok)
        r = await worker.api_record_session_attendance(req, env, "s-1")
        assert r.status == 200
        data = _parse(r)
        assert data["success"] is True
        assert data["updated"] == 2
        assert len(data["records"]) == 2
        assert data["records"][0] == {"user_id": "u-1", "status": "registered"}
        assert data["records"][1] == {"user_id": "u-2", "status": "unmarked"}


# ---------------------------------------------------------------------------
# GET /api/sessions/:id/attendance
# ---------------------------------------------------------------------------

class TestGetSessionAttendance:
    def _req(self, sid, token=None):
        headers = _auth(token) if token else {}
        return MockRequest(method="GET", url=f"http://localhost/api/sessions/{sid}/attendance", headers=headers)

    async def test_no_auth_returns_401(self):
        req = self._req("s-1")
        r = await worker.api_get_session_attendance(req, make_env(), "s-1")
        assert r.status == 401

    async def test_session_not_found_returns_404(self):
        tok = _token(uid="host-1")
        env = make_env(db=MockDB([make_stmt(first=None)]))
        r = await worker.api_get_session_attendance(self._req("s-999", tok), env, "s-999")
        assert r.status == 404

    async def test_non_host_permission_denial_returns_403(self):
        tok = _token(uid="student-1", role="member")
        session_row = MockRow(id="s-1", activity_id="act-1", title="Week 1", host_id="host-1", activity_title="Course 101")
        env = make_env(db=MockDB([make_stmt(first=session_row)]))
        r = await worker.api_get_session_attendance(self._req("s-1", tok), env, "s-1")
        assert r.status == 403
        assert "Host access required" in _parse(r).get("error", "")

    async def test_host_retrieves_attendance_register_with_summary(self):
        tok = _token(uid="host-1")
        session_row = MockRow(id="s-1", activity_id="act-1", title="Week 1", host_id="host-1", activity_title="Intro to Python")
        
        # Enrolled students with attendance statuses
        student1 = MockRow(
            user_id="u-1", enr_role="participant", enr_status="active",
            name=_enc("Alice Bob"), username=_enc("alice"), email=_enc("alice@example.com"),
            attendance_id="att-1", attendance_status="attended", marked_at="2026-10-25 10:00:00", updated_at="2026-10-25 10:00:00"
        )
        student2 = MockRow(
            user_id="u-2", enr_role="participant", enr_status="active",
            name=_enc("Charlie Dan"), username=_enc("charlie"), email=_enc("charlie@example.com"),
            attendance_id="att-2", attendance_status="missed", marked_at="2026-10-25 10:00:00", updated_at="2026-10-25 10:00:00"
        )
        student3 = MockRow(
            user_id="u-3", enr_role="participant", enr_status="active",
            name=_enc("Eve Frank"), username=_enc("eve"), email=_enc("eve@example.com"),
            attendance_id=None, attendance_status=None, marked_at=None, updated_at=None
        )

        env = make_env(
            db=MockDB([
                make_stmt(first=session_row),                           # session lookup
                make_stmt(all_results=[student1, student2, student3]),  # enrollments query
                make_stmt(all_results=[]),                              # extra attendance query
            ]),
            enc_key=ENC_KEY,
        )

        r = await worker.api_get_session_attendance(self._req("s-1", tok), env, "s-1")
        assert r.status == 200
        data = _parse(r)
        assert data["success"] is True
        assert data["session_id"] == "s-1"
        assert data["session_title"] == "Week 1"
        assert len(data["attendance"]) == 3

        att = data["attendance"]
        assert att[0]["user_id"] == "u-1"
        assert att[0]["name"] == "Alice Bob"
        assert att[0]["status"] == "attended"

        assert att[1]["user_id"] == "u-2"
        assert att[1]["name"] == "Charlie Dan"
        assert att[1]["status"] == "missed"

        assert att[2]["user_id"] == "u-3"
        assert att[2]["status"] == "registered"

        summary = data["summary"]
        assert summary["total"] == 3
        assert summary["attended"] == 1
        assert summary["missed"] == 1
        assert summary["registered"] == 1
        assert summary["attendance_rate"] == 33.3


# ---------------------------------------------------------------------------
# Attendance Percentage Calculations in Dashboard & Activity Detail
# ---------------------------------------------------------------------------

class TestAttendancePercentageCalculation:
    async def test_dashboard_attendance_percentage_calculation(self):
        tok = _token(uid="student-1", username="student", role="member")
        
        # Student enrolled in two activities:
        # act-1: 4 sessions, 3 attended -> 75.0%
        # act-2: 2 sessions, 2 attended -> 100.0%
        # Overall: 5 attended out of 6 sessions -> 83.3%
        act1_row = MockRow(
            id="act-1", title="Python 101", description="", slug="python-101",
            type="course", format="self_paced", schedule_type="multi_session",
            enr_role="participant", enr_status="active", joined_at="2026-01-01",
            host_name_enc=_enc("Professor X"),
            session_count=4, attended_count=3,
        )
        act2_row = MockRow(
            id="act-2", title="Web Dev 101", description="", slug="web-dev-101",
            type="course", format="live", schedule_type="multi_session",
            enr_role="participant", enr_status="active", joined_at="2026-01-02",
            host_name_enc=_enc("Professor Y"),
            session_count=2, attended_count=2,
        )

        env = make_env(
            db=MockDB([
                make_stmt(all_results=[]),                    # hosted activities (empty)
                make_stmt(all_results=[act1_row, act2_row]),  # joined activities
                make_stmt(all_results=[]),                    # tags for act-1
                make_stmt(all_results=[]),                    # tags for act-2
            ]),
            enc_key=ENC_KEY,
        )

        req = MockRequest(method="GET", url="http://localhost/api/dashboard", headers=_auth(tok))
        r = await worker.api_dashboard(req, env)
        assert r.status == 200
        data = _parse(r)

        joined = data["joined_activities"]
        assert len(joined) == 2
        assert joined[0]["title"] == "Python 101"
        assert joined[0]["session_count"] == 4
        assert joined[0]["attended_sessions"] == 3
        assert joined[0]["attendance_percentage"] == 75.0

        assert joined[1]["title"] == "Web Dev 101"
        assert joined[1]["session_count"] == 2
        assert joined[1]["attended_sessions"] == 2
        assert joined[1]["attendance_percentage"] == 100.0

        assert data["attendance_percentage"] == 83.3
        summary = data["attendance_summary"]
        assert summary["total_sessions"] == 6
        assert summary["attended_sessions"] == 5
        assert summary["attendance_percentage"] == 83.3

    async def test_dashboard_zero_sessions_safe(self):
        tok = _token(uid="student-1", role="member")
        act_row = MockRow(
            id="act-1", title="Self Paced Course", description="", slug="self-paced",
            type="course", format="self_paced", schedule_type="ongoing",
            enr_role="participant", enr_status="active", joined_at="2026-01-01",
            host_name_enc=_enc("Prof"),
            session_count=0, attended_count=0,
        )

        env = make_env(
            db=MockDB([
                make_stmt(all_results=[]),
                make_stmt(all_results=[act_row]),
                make_stmt(all_results=[]),
            ]),
            enc_key=ENC_KEY,
        )

        req = MockRequest(method="GET", url="http://localhost/api/dashboard", headers=_auth(tok))
        r = await worker.api_dashboard(req, env)
        assert r.status == 200
        data = _parse(r)
        assert data["joined_activities"][0]["attendance_percentage"] is None
        assert data["attendance_percentage"] is None
        assert data["attendance_summary"]["total_sessions"] == 0

    async def test_activity_detail_attendance_percentage_for_enrolled_student(self):
        tok = _token(uid="student-1", role="member")

        act_row = MockRow(
            id="act-1", title="Data Science", description="", type="course",
            format="live", schedule_type="multi_session", host_id="host-1",
            host_uid="host-1", host_name_enc=_enc("Host User"), created_at="2026-01-01",
            status="published", slug="data-science",
        )
        enr_row = MockRow(id="enr-1", role="participant", status="active", user_id="student-1", activity_id="act-1")
        
        # 3 sessions: session 1 attended, session 2 missed, session 3 unrecorded
        s1 = MockRow(id="s-1", title="Session 1", description="", start_time="10:00", end_time="11:00", location="")
        s2 = MockRow(id="s-2", title="Session 2", description="", start_time="10:00", end_time="11:00", location="")
        s3 = MockRow(id="s-3", title="Session 3", description="", start_time="10:00", end_time="11:00", location="")

        # User attendance records
        att1 = MockRow(session_id="s-1", status="attended", created_at="2026-10-25", updated_at="2026-10-25")
        att2 = MockRow(session_id="s-2", status="missed", created_at="2026-10-25", updated_at="2026-10-25")

        env = make_env(
            db=MockDB([
                make_stmt(first=act_row),                  # find activity
                make_stmt(first=enr_row),                  # check enrollment
                make_stmt(first=None),                     # completion check
                make_stmt(first=None),                     # interest check
                make_stmt(all_results=[att1, att2]),       # user attendance rows
                make_stmt(all_results=[s1, s2, s3]),       # sessions
                make_stmt(all_results=[]),                 # tags
                make_stmt(first=MockRow(cnt=1)),           # enrollment count
                make_stmt(first=MockRow(cnt=0)),           # interest count
            ]),
            enc_key=ENC_KEY,
        )

        req = MockRequest(method="GET", url="http://localhost/api/activities/act-1", headers=_auth(tok))
        r = await worker.api_get_activity("act-1", req, env)
        assert r.status == 200
        data = _parse(r)
        
        assert data["is_enrolled"] is True
        sessions = data["sessions"]
        assert len(sessions) == 3
        assert sessions[0]["my_attendance"] == "attended"
        assert sessions[1]["my_attendance"] == "missed"
        assert sessions[2]["my_attendance"] is None

        att = data["attendance"]
        assert att["total_sessions"] == 3
        assert att["attended"] == 1
        assert att["missed"] == 1
        assert att["percentage"] == 33.3


# ---------------------------------------------------------------------------
# Dispatcher End-to-End Route Matching
# ---------------------------------------------------------------------------

class TestAttendanceDispatcher:
    async def test_dispatch_get_session_attendance(self):
        tok = _token(uid="host-1")
        session_row = MockRow(id="s-100", activity_id="act-1", title="Class 1", host_id="host-1", activity_title="Math")
        env = make_env(
            db=MockDB([
                make_stmt(first=session_row),
                make_stmt(all_results=[]),
                make_stmt(all_results=[]),
            ]),
            enc_key=ENC_KEY,
        )
        req = MockRequest(method="GET", url="http://localhost/api/sessions/s-100/attendance", headers=_auth(tok))
        r = await worker._dispatch(req, env)
        assert r.status == 200
        data = _parse(r)
        assert data["session_id"] == "s-100"

    async def test_dispatch_post_session_attendance(self):
        tok = _token(uid="host-1")
        session_row = MockRow(id="s-100", activity_id="act-1", title="Class 1", host_id="host-1")
        env = make_env(
            db=MockDB([
                make_stmt(first=session_row),
                make_stmt(),
            ]),
            enc_key=ENC_KEY,
        )
        req = json_request(
            "/api/sessions/s-100/attendance",
            [{"user_id": "u-1", "status": "attended"}],
            headers=_auth(tok),
        )
        r = await worker._dispatch(req, env)
        assert r.status == 200
        data = _parse(r)
        assert data["success"] is True
        assert data["updated"] == 1
