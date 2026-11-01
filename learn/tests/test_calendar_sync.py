"""
Tests for Calendar Sync (.ics Export & iCal Subscription Feed):
  * _escape_ical_text()
  * _parse_iso_datetime()
  * _fold_ical_line()
  * _generate_vcalendar()
  * api_activity_calendar_ics()
  * api_user_calendar_ics()
  * _dispatch routing for calendar endpoints
"""

import base64
import datetime
import pytest
from tests.helpers import load_worker, MockRequest, MockRow, MockDB, make_env, make_stmt

worker = load_worker()

SECRET = "test-encryption-key"
JWT = "test-jwt-secret"


def _enc(val: str) -> str:
    """Compute mock AES ciphertext synchronously using the test stub."""
    iv = b"\x00" * 12
    return "v1:" + base64.b64encode(iv + val.encode("utf-8")).decode("ascii")


def _make_user_token(uid="user-1", username="student_user", role="member"):
    return worker.create_token(uid, username, role, JWT)


def _make_host_token(uid="host-1", username="instructor_alice", role="host"):
    return worker.create_token(uid, username, role, JWT)


# ===========================================================================
# 1. Unit Tests for RFC 5545 Helpers
# ===========================================================================

class TestIcsHelpers:
    def test_escape_ical_text_empty(self):
        assert worker._escape_ical_text("") == ""
        assert worker._escape_ical_text(None) == ""

    def test_escape_ical_text_special_characters(self):
        raw = r"Backslash \ Semicolon ; Comma , and newlines" + "\r\nLine2\nLine3"
        escaped = worker._escape_ical_text(raw)
        assert r"\\" in escaped
        assert r"\;" in escaped
        assert r"\," in escaped
        assert r"\nLine2\nLine3" in escaped
        assert "\r" not in escaped
        assert "\n" not in escaped

    def test_parse_iso_datetime(self):
        # Full ISO with Z
        dt = worker._parse_iso_datetime("2026-10-25T14:30:00Z")
        assert dt is not None
        assert dt.year == 2026 and dt.month == 10 and dt.day == 25
        assert dt.hour == 14 and dt.minute == 30 and dt.second == 0
        assert dt.tzinfo == datetime.timezone.utc

        # SQLite format: space separator
        dt2 = worker._parse_iso_datetime("2026-10-25 14:30:00")
        assert dt2 is not None
        assert dt2.hour == 14 and dt2.minute == 30

        # Date only
        dt3 = worker._parse_iso_datetime("2026-10-25")
        assert dt3 is not None
        assert dt3.year == 2026 and dt3.month == 10 and dt3.day == 25
        assert dt3.hour == 0

        # Empty / None / Invalid
        assert worker._parse_iso_datetime(None) is None
        assert worker._parse_iso_datetime("") is None
        assert worker._parse_iso_datetime("not-a-date") is None

    def test_fold_ical_line_short(self):
        short = "SUMMARY:Short line under 75 octets"
        assert worker._fold_ical_line(short) == short

    def test_fold_ical_line_long(self):
        long_line = "DESCRIPTION:" + ("X" * 120)
        folded = worker._fold_ical_line(long_line)
        lines = folded.split("\r\n")
        assert len(lines) == 2
        assert len(lines[0].encode("utf-8")) <= 75
        assert lines[1].startswith(" ")
        assert len(lines[1].encode("utf-8")) <= 75

    def test_generate_vcalendar_structure(self):
        events = [{
            "uid": "session-123@alphaonelabs.com",
            "summary": "Intro to Python: Session 1",
            "description": "Getting started with syntax",
            "location": "Zoom Room 42",
            "start_time": "2026-10-25T14:00:00Z",
            "end_time": "2026-10-25T15:30:00Z",
            "created_at": "2026-10-01T00:00:00Z",
            "url": "https://alphaonelabs.com/activity/python-101",
        }]
        ics = worker._generate_vcalendar(
            events,
            calendar_name="Python Course",
            calendar_description="Python Sessions",
        )

        assert ics.startswith("BEGIN:VCALENDAR\r\n")
        assert "VERSION:2.0\r\n" in ics
        assert "PRODID:-//Alpha One Labs//Learn Calendar//EN\r\n" in ics
        assert "X-WR-CALNAME:Python Course\r\n" in ics
        assert "X-WR-CALDESC:Python Sessions\r\n" in ics
        assert "BEGIN:VEVENT\r\n" in ics
        assert "UID:session-123@alphaonelabs.com\r\n" in ics
        assert "DTSTART:20261025T140000Z\r\n" in ics
        assert "DTEND:20261025T153000Z\r\n" in ics
        assert "SUMMARY:Intro to Python: Session 1\r\n" in ics
        assert "DESCRIPTION:Getting started with syntax\r\n" in ics
        assert "LOCATION:Zoom Room 42\r\n" in ics
        assert "URL:https://alphaonelabs.com/activity/python-101\r\n" in ics
        assert "STATUS:CONFIRMED\r\n" in ics
        assert "END:VEVENT\r\n" in ics
        assert ics.endswith("END:VCALENDAR\r\n")


# ===========================================================================
# 2. Activity Calendar .ics Export Tests
# ===========================================================================

class TestActivityCalendarIcs:
    async def test_not_found(self):
        db = MockDB([
            make_stmt(first=None),  # by slug
            make_stmt(first=None),  # by id
        ])
        env = make_env(db=db, enc_key=SECRET, jwt_secret=JWT)
        req = MockRequest(method="GET", url="http://localhost/api/activities/missing/calendar.ics")
        resp = await worker.api_activity_calendar_ics("missing", req, env)
        assert resp.status == 404
        assert "Activity not found" in resp.body

    async def test_activity_with_sessions_anonymous(self):
        act_row = MockRow(
            id="act-1",
            slug="python-workshop",
            title="Python Workshop",
            description=_enc("Learn Python fast"),
            host_id="host-1",
            host_name_enc=_enc("Alice"),
            host_uid="host-1",
            created_at="2026-10-01 10:00:00",
        )
        ses_row = MockRow(
            id="ses-1",
            activity_id="act-1",
            title="Session 1",
            description=_enc("Private curriculum notes"),
            start_time="2026-10-20 18:00:00",
            end_time="2026-10-20 19:30:00",
            location=_enc("https://meet.google.com/abc-defg-hij"),
            created_at="2026-10-02 10:00:00",
        )
        db = MockDB([
            make_stmt(first=act_row),  # find by slug
            make_stmt(all_results=[ses_row]),  # find sessions
        ])
        env = make_env(db=db, enc_key=SECRET, jwt_secret=JWT)
        req = MockRequest(method="GET", url="http://localhost/api/activities/python-workshop/calendar.ics")
        resp = await worker.api_activity_calendar_ics("python-workshop", req, env)

        assert resp.status == 200
        assert "text/calendar" in resp.headers["Content-Type"]
        assert 'filename="activity-python-workshop.ics"' in resp.headers["Content-Disposition"]
        assert "BEGIN:VCALENDAR" in resp.body
        assert "SUMMARY:Python Workshop: Session 1" in resp.body
        # Non-enrolled anonymous user: meeting link must be locked
        assert "Join activity to unlock meeting location/link" in resp.body
        assert "https://meet.google.com/abc-defg-hij" not in resp.body

    async def test_activity_with_sessions_enrolled_user(self):
        user_tok = _make_user_token(uid="user-1")
        act_row = MockRow(
            id="act-1",
            slug="python-workshop",
            title="Python Workshop",
            description=_enc("Learn Python fast"),
            host_id="host-99",
            host_name_enc=_enc("Instructor Bob"),
            host_uid="host-99",
            created_at="2026-10-01 10:00:00",
        )
        enrollment_row = MockRow(id="enr-1")
        ses_row = MockRow(
            id="ses-1",
            activity_id="act-1",
            title="Session 1",
            description=_enc("Private curriculum notes"),
            start_time="2026-10-20 18:00:00",
            end_time="2026-10-20 19:30:00",
            location=_enc("https://meet.google.com/private-link"),
            created_at="2026-10-02 10:00:00",
        )
        db = MockDB([
            make_stmt(first=act_row),       # find by slug
            make_stmt(first=enrollment_row), # verify enrollment
            make_stmt(all_results=[ses_row]),  # sessions
        ])
        env = make_env(db=db, enc_key=SECRET, jwt_secret=JWT)
        req = MockRequest(
            method="GET",
            url=f"http://localhost/api/activities/python-workshop/calendar.ics?token={user_tok}",
        )
        resp = await worker.api_activity_calendar_ics("python-workshop", req, env)

        assert resp.status == 200
        # Enrolled member gets decrypted location and notes
        assert "https://meet.google.com/private-link" in resp.body
        assert "Private curriculum notes" in resp.body

    async def test_activity_without_sessions_generates_activity_event(self):
        act_row = MockRow(
            id="act-self-paced",
            slug="self-paced-ai",
            title="Self-Paced AI Course",
            description=_enc("Learn AI at your own pace"),
            host_id="host-1",
            host_name_enc=_enc("Alice"),
            host_uid="host-1",
            created_at="2026-10-01 10:00:00",
        )
        db = MockDB([
            make_stmt(first=act_row),  # find by slug
            make_stmt(all_results=[]),    # 0 sessions
        ])
        env = make_env(db=db, enc_key=SECRET, jwt_secret=JWT)
        req = MockRequest(method="GET", url="http://localhost/api/activities/self-paced-ai/calendar.ics")
        resp = await worker.api_activity_calendar_ics("self-paced-ai", req, env)

        assert resp.status == 200
        assert "BEGIN:VEVENT" in resp.body
        assert "SUMMARY:Self-Paced AI Course" in resp.body
        assert "UID:activity-act-self-paced@alphaonelabs.com" in resp.body


# ===========================================================================
# 3. User Schedule iCal Subscription Feed Tests
# ===========================================================================

class TestUserCalendarFeed:
    async def test_unauthorized_without_token(self):
        env = make_env(enc_key=SECRET, jwt_secret=JWT)
        req = MockRequest(method="GET", url="http://localhost/api/calendar/user.ics")
        resp = await worker.api_user_calendar_ics(req, env)
        assert resp.status == 401
        assert "Authentication required" in resp.body

    async def test_unauthorized_with_invalid_token(self):
        env = make_env(enc_key=SECRET, jwt_secret=JWT)
        req = MockRequest(method="GET", url="http://localhost/api/calendar/user.ics?token=bad.sig.token")
        resp = await worker.api_user_calendar_ics(req, env)
        assert resp.status == 401

    async def test_authorized_enrolled_schedule_query_param(self):
        user_tok = _make_user_token(uid="student-42")
        rows = [
            MockRow(
                session_id="ses-1",
                session_title="Week 1 Live Lab",
                session_desc=_enc("Lab assignments walkthrough"),
                start_time="2026-10-22 17:00:00",
                end_time="2026-10-22 18:30:00",
                session_loc=_enc("Room 101 / Zoom"),
                session_created="2026-10-01 12:00:00",
                activity_id="act-web",
                activity_slug="web-dev-101",
                activity_title="Web Development 101",
                activity_desc=_enc("Full stack web development"),
                user_role="participant",
            ),
            MockRow(
                session_id="ses-2",
                session_title="Office Hours",
                session_desc=_enc("Ask the instructor anything"),
                start_time="2026-10-24 15:00:00",
                end_time="2026-10-24 16:00:00",
                session_loc=_enc("Discord Stage"),
                session_created="2026-10-01 12:00:00",
                activity_id="act-adv",
                activity_slug="adv-python",
                activity_title="Advanced Python",
                activity_desc=_enc("Deep dive into Python"),
                user_role="host",
            ),
        ]
        db = MockDB([make_stmt(all_results=rows)])
        env = make_env(db=db, enc_key=SECRET, jwt_secret=JWT)
        req = MockRequest(method="GET", url=f"http://localhost/api/calendar/user.ics?token={user_tok}")
        resp = await worker.api_user_calendar_ics(req, env)

        assert resp.status == 200
        assert "text/calendar" in resp.headers["Content-Type"]
        assert 'filename="my_schedule.ics"' in resp.headers["Content-Disposition"]
        assert "X-WR-CALNAME:My Alpha One Labs Schedule" in resp.body
        # Enrolled session
        assert "SUMMARY:Web Development 101: Week 1 Live Lab" in resp.body
        assert "LOCATION:Room 101 / Zoom" in resp.body
        # Hosted session
        assert "SUMMARY:[Teaching] Advanced Python: Office Hours" in resp.body
        assert "LOCATION:Discord Stage" in resp.body

    async def test_authorized_via_bearer_header(self):
        user_tok = _make_user_token(uid="student-42")
        db = MockDB([make_stmt(all_results=[])])
        env = make_env(db=db, enc_key=SECRET, jwt_secret=JWT)
        req = MockRequest(
            method="GET",
            url="http://localhost/api/calendar/user.ics",
            headers={"Authorization": f"Bearer {user_tok}"},
        )
        resp = await worker.api_user_calendar_ics(req, env)
        assert resp.status == 200
        assert "BEGIN:VCALENDAR" in resp.body


# ===========================================================================
# 4. Dispatcher Integration Tests
# ===========================================================================

class TestCalendarDispatcherRouting:
    async def test_route_activity_calendar_ics(self):
        act_row = MockRow(
            id="act-1",
            slug="react-bootcamp",
            title="React Bootcamp",
            description="",
            host_id="h1",
            host_name_enc="",
            host_uid="h1",
            created_at="2026-10-01 10:00:00",
        )
        db = MockDB([
            make_stmt(first=act_row),
            make_stmt(all_results=[]),
        ])
        env = make_env(db=db, enc_key=SECRET, jwt_secret=JWT)
        req = MockRequest(method="GET", url="http://localhost/api/activities/react-bootcamp/calendar.ics")
        resp = await worker._dispatch(req, env)
        assert resp.status == 200
        assert "text/calendar" in resp.headers.get("Content-Type", "")
        assert "BEGIN:VCALENDAR" in resp.body

    async def test_route_user_calendar_ics(self):
        user_tok = _make_user_token()
        db = MockDB([make_stmt(all_results=[])])
        env = make_env(db=db, enc_key=SECRET, jwt_secret=JWT)
        req = MockRequest(method="GET", url=f"http://localhost/api/calendar/user.ics?token={user_tok}")
        resp = await worker._dispatch(req, env)
        assert resp.status == 200
        assert "text/calendar" in resp.headers.get("Content-Type", "")

    async def test_calendar_options_preflight(self):
        env = make_env(enc_key=SECRET, jwt_secret=JWT)
        req = MockRequest(method="OPTIONS", url="http://localhost/api/activities/react-bootcamp/calendar.ics")
        resp = await worker._dispatch(req, env)
        assert resp.status == 204
        assert "Access-Control-Allow-Origin" in resp.headers
