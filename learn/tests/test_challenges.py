"""
Tests for challenges, submissions and points (migration 0017).
Covers:
- POST /api/challenges (role check, validation, weekly-number conflict)
- GET /api/challenges, /api/challenges/current, /api/challenges/:id (public)
- POST /api/challenges/:id/submit (auth, window, one submission, points in the same batch)
- GET /api/points (caller only)
- migration, schema.sql and _DDL stay in sync
"""

import datetime
import json
import re
from pathlib import Path

from tests.helpers import (
    MockDB,
    MockRequest,
    MockRow,
    json_request,
    load_worker,
    make_env,
    make_init_db_stmts,
    make_stmt,
)
from unittest.mock import AsyncMock

worker = load_worker()

JWT_SECRET = "test-jwt-secret"
LEARN_DIR = Path(__file__).parent.parent

TODAY = datetime.datetime.now(datetime.timezone.utc).date()
YESTERDAY = (TODAY - datetime.timedelta(days=1)).isoformat()
TOMORROW = (TODAY + datetime.timedelta(days=1)).isoformat()
LAST_WEEK = (TODAY - datetime.timedelta(days=7)).isoformat()
NEXT_WEEK = (TODAY + datetime.timedelta(days=7)).isoformat()


def _parse(resp):
    return json.loads(resp.body)


def _token(uid="user-1", username="alice", role="student"):
    return worker.create_token(uid, username, role, JWT_SECRET)


def _auth(token):
    return {"Authorization": f"Bearer {token}"} if token else {}


def _get(path, token=None):
    return MockRequest(method="GET", url=f"http://localhost{path}", headers=_auth(token))


def _post(path, body, token=None):
    return json_request(path, body, headers=_auth(token))


def _challenge_row(**overrides):
    values = dict(
        id="c-1",
        title="Week 1",
        description="Write a haiku",
        challenge_type="weekly",
        week_number=1,
        start_date=YESTERDAY,
        end_date=TOMORROW,
        points=10,
        created_at="2026-11-01 10:00:00",
    )
    values.update(overrides)
    return MockRow(**values)


def _valid_body(**overrides):
    body = {
        "title": "Week 1",
        "description": "Write a haiku",
        "challenge_type": "weekly",
        "week_number": 1,
        "start_date": YESTERDAY,
        "end_date": NEXT_WEEK,
    }
    body.update(overrides)
    return body


class RecordingDB(MockDB):
    """MockDB that remembers the SQL it prepared and supports batch()."""

    def __init__(self, stmts=None):
        super().__init__(stmts)
        self.sql = []
        self.prepared = []  # (sql, statement) for every statement handed out, including fallbacks
        self.batch = AsyncMock(return_value=[])

    def prepare(self, sql):
        clean = " ".join(sql.split())
        self.sql.append(clean)
        stmt = super().prepare(sql)
        self.prepared.append((clean, stmt))
        return stmt

    def bound_args(self, sql_prefix):
        """Arguments the first statement starting with sql_prefix was bound with."""
        for sql, stmt in self.prepared:
            if sql.startswith(sql_prefix):
                return stmt.bind.call_args.args
        raise AssertionError("no statement starting with " + sql_prefix)


class TestCreateChallenge:
    async def test_requires_login(self):
        env = make_env()
        resp = await worker.api_create_challenge(_post("/api/challenges", _valid_body()), env)
        assert resp.status == 401

    async def test_students_cannot_create(self):
        env = make_env()
        resp = await worker.api_create_challenge(
            _post("/api/challenges", _valid_body(), _token(role="student")), env
        )
        assert resp.status == 403

    async def test_host_can_create_weekly(self):
        stmt = make_stmt()
        db = RecordingDB([stmt])
        resp = await worker.api_create_challenge(
            _post("/api/challenges", _valid_body(), _token(uid="host-1", role="host")), make_env(db=db)
        )
        assert resp.status == 200
        data = _parse(resp)["data"]
        assert data["title"] == "Week 1"
        assert data["points"] == 10
        assert data["week_number"] == 1
        args = stmt.bind.call_args.args
        assert args[-1] == "host-1"  # created_by comes from the token, never the body

    async def test_admin_can_create_one_time(self):
        body = _valid_body(challenge_type="one_time")
        del body["week_number"]
        resp = await worker.api_create_challenge(
            _post("/api/challenges", body, _token(role="admin")), make_env(db=RecordingDB([make_stmt()]))
        )
        assert resp.status == 200
        assert _parse(resp)["data"]["week_number"] is None

    async def test_created_by_in_body_is_ignored(self):
        stmt = make_stmt()
        await worker.api_create_challenge(
            _post("/api/challenges", _valid_body(created_by="someone-else"), _token(uid="host-1", role="host")),
            make_env(db=RecordingDB([stmt])),
        )
        assert "someone-else" not in stmt.bind.call_args.args

    async def test_weekly_needs_week_number(self):
        body = _valid_body()
        del body["week_number"]
        resp = await worker.api_create_challenge(_post("/api/challenges", body, _token(role="host")), make_env())
        assert resp.status == 400

    async def test_one_time_rejects_week_number(self):
        resp = await worker.api_create_challenge(
            _post("/api/challenges", _valid_body(challenge_type="one_time"), _token(role="host")), make_env()
        )
        assert resp.status == 400

    async def test_rejects_bad_fields(self):
        cases = [
            {"title": "   "},
            {"description": ""},
            {"challenge_type": "daily"},
            {"week_number": 0},
            {"week_number": 10000},
            {"week_number": True},
            {"start_date": "2026-13-40"},
            {"start_date": "20261101"},
            {"end_date": "tomorrow"},
            {"end_date": LAST_WEEK},
            {"points": 0},
            {"points": 1001},
            {"points": "lots"},
        ]
        for override in cases:
            resp = await worker.api_create_challenge(
                _post("/api/challenges", _valid_body(**override), _token(role="host")), make_env()
            )
            assert resp.status == 400, override

    async def test_duplicate_week_number_returns_409(self):
        stmt = make_stmt()
        stmt.bind.return_value.run.side_effect = Exception("UNIQUE constraint failed: challenges.week_number")
        resp = await worker.api_create_challenge(
            _post("/api/challenges", _valid_body(), _token(role="host")), make_env(db=RecordingDB([stmt]))
        )
        assert resp.status == 409

    async def test_other_database_errors_are_not_hidden(self):
        stmt = make_stmt()
        stmt.bind.return_value.run.side_effect = Exception("disk on fire")
        env = make_env(db=RecordingDB([stmt]))
        try:
            await worker.api_create_challenge(_post("/api/challenges", _valid_body(), _token(role="host")), env)
        except Exception as exc:
            assert "disk on fire" in str(exc)
        else:
            raise AssertionError("the database error should propagate")


class TestReadChallenges:
    async def test_list_is_public(self):
        db = RecordingDB([make_stmt(all_results=[_challenge_row(), _challenge_row(id="c-2", week_number=2)])])
        resp = await worker.api_list_challenges(_get("/api/challenges"), make_env(db=db))
        assert resp.status == 200
        assert [c["id"] for c in _parse(resp)["challenges"]] == ["c-1", "c-2"]

    async def test_list_filters_by_type_and_bounds_limit(self):
        db = RecordingDB([make_stmt(all_results=[])])
        stmt_bind = db._stmts[0].bind
        resp = await worker.api_list_challenges(_get("/api/challenges?type=one_time&limit=9999"), make_env(db=db))
        assert resp.status == 200
        assert "WHERE challenge_type = ?" in db.sql[0]
        assert stmt_bind.call_args.args == ("one_time", 100)

    async def test_list_rejects_unknown_type(self):
        resp = await worker.api_list_challenges(_get("/api/challenges?type=hourly"), make_env())
        assert resp.status == 400

    async def test_current_returns_open_weekly_challenge(self):
        db = RecordingDB([make_stmt(first=_challenge_row())])
        resp = await worker.api_current_challenge(_get("/api/challenges/current"), make_env(db=db))
        assert resp.status == 200
        assert _parse(resp)["data"]["id"] == "c-1"
        assert "challenge_type = 'weekly'" in db.sql[0]

    async def test_current_404_when_nothing_is_open(self):
        resp = await worker.api_current_challenge(_get("/api/challenges/current"), make_env())
        assert resp.status == 404

    async def test_detail_404_for_unknown_id(self):
        resp = await worker.api_get_challenge(_get("/api/challenges/nope"), make_env(), "nope")
        assert resp.status == 404

    async def test_detail_for_anonymous_has_no_submitted_flag(self):
        db = RecordingDB([make_stmt(first=_challenge_row())])
        resp = await worker.api_get_challenge(_get("/api/challenges/c-1"), make_env(db=db), "c-1")
        assert resp.status == 200
        assert "submitted" not in _parse(resp)["data"]

    async def test_detail_tells_a_member_whether_they_submitted(self):
        db = RecordingDB([make_stmt(first=_challenge_row()), make_stmt(first=MockRow(id="s-1"))])
        resp = await worker.api_get_challenge(_get("/api/challenges/c-1", _token()), make_env(db=db), "c-1")
        assert _parse(resp)["data"]["submitted"] is True

    async def test_detail_never_returns_submission_text(self):
        db = RecordingDB([make_stmt(first=_challenge_row())])
        resp = await worker.api_get_challenge(_get("/api/challenges/c-1"), make_env(db=db), "c-1")
        assert "submission_text" not in resp.body


def _submit_req(body=None, token="default"):
    tok = _token() if token == "default" else token
    return _post("/api/challenges/c-1/submit", body if body is not None else {"submission_text": "my haiku"}, tok)


class TestSubmitChallenge:
    async def test_requires_login(self):
        resp = await worker.api_submit_challenge(_submit_req(token=None), make_env(), "c-1")
        assert resp.status == 401

    async def test_requires_text(self):
        for body in ({}, {"submission_text": "   "}):
            resp = await worker.api_submit_challenge(_submit_req(body), make_env(), "c-1")
            assert resp.status == 400

    async def test_unknown_challenge_is_404(self):
        resp = await worker.api_submit_challenge(_submit_req(), make_env(), "c-1")
        assert resp.status == 404

    async def test_records_submission_and_points_in_one_batch(self):
        db = RecordingDB([make_stmt(first=_challenge_row(points=25)), make_stmt(first=None)])
        resp = await worker.api_submit_challenge(_submit_req(token=_token(uid="user-9")), make_env(db=db), "c-1")
        assert resp.status == 200
        assert _parse(resp)["data"]["points_awarded"] == 25
        db.batch.assert_awaited_once()
        statements = db.batch.await_args.args[0]
        assert len(statements) == 2
        assert any("INSERT INTO challenge_submissions" in s for s in db.sql)
        assert any("INSERT INTO user_points" in s for s in db.sql)

    async def test_points_come_from_the_challenge_not_the_request(self):
        db = RecordingDB([make_stmt(first=_challenge_row(points=10)), make_stmt(first=None)])
        resp = await worker.api_submit_challenge(
            _submit_req({"submission_text": "x", "points_awarded": 9999, "user_id": "other"}, token=_token(uid="user-9")),
            make_env(db=db),
            "c-1",
        )
        assert _parse(resp)["data"]["points_awarded"] == 10

        # INSERT INTO challenge_submissions (id, user_id, challenge_id, submission_text, points_awarded)
        submission_args = db.bound_args("INSERT INTO challenge_submissions")
        assert submission_args[1:] == ("user-9", "c-1", "x", 10)
        # INSERT INTO user_points (id, user_id, challenge_id, amount, reason)
        points_args = db.bound_args("INSERT INTO user_points")
        assert points_args[1:4] == ("user-9", "c-1", 10)
        for args in (submission_args, points_args):
            assert 9999 not in args
            assert "other" not in args

    async def test_second_submission_returns_409_without_writing(self):
        db = RecordingDB([make_stmt(first=_challenge_row()), make_stmt(first=MockRow(id="s-1"))])
        resp = await worker.api_submit_challenge(_submit_req(), make_env(db=db), "c-1")
        assert resp.status == 409
        db.batch.assert_not_awaited()

    async def test_concurrent_duplicate_returns_409(self):
        db = RecordingDB([make_stmt(first=_challenge_row()), make_stmt(first=None)])
        db.batch.side_effect = Exception("UNIQUE constraint failed: challenge_submissions.user_id")
        resp = await worker.api_submit_challenge(_submit_req(), make_env(db=db), "c-1")
        assert resp.status == 409

    async def test_challenge_that_has_not_started_is_rejected(self):
        db = RecordingDB([make_stmt(first=_challenge_row(start_date=TOMORROW, end_date=NEXT_WEEK)), make_stmt(first=None)])
        resp = await worker.api_submit_challenge(_submit_req(), make_env(db=db), "c-1")
        assert resp.status == 400
        db.batch.assert_not_awaited()

    async def test_challenge_that_has_ended_is_rejected(self):
        db = RecordingDB([make_stmt(first=_challenge_row(start_date=LAST_WEEK, end_date=YESTERDAY)), make_stmt(first=None)])
        resp = await worker.api_submit_challenge(_submit_req(), make_env(db=db), "c-1")
        assert resp.status == 400
        db.batch.assert_not_awaited()


class TestMyPoints:
    async def test_requires_login(self):
        resp = await worker.api_my_points(_get("/api/points"), make_env())
        assert resp.status == 401

    async def test_returns_total_and_recent_for_the_caller(self):
        recent = [
            MockRow(amount=10, reason="Completed challenge: Week 1", point_type="regular",
                    challenge_id="c-1", awarded_at="2026-11-02 09:00:00"),
        ]
        db = RecordingDB([make_stmt(first=MockRow(total=35)), make_stmt(all_results=recent)])
        resp = await worker.api_my_points(_get("/api/points", _token(uid="user-7")), make_env(db=db))
        assert resp.status == 200
        data = _parse(resp)["data"]
        assert data["total_points"] == 35
        assert data["recent"][0]["amount"] == 10
        for stmt in db._stmts:
            assert stmt.bind.call_args.args == ("user-7",)

    async def test_no_rows_means_zero_points(self):
        db = RecordingDB([make_stmt(first=None), make_stmt(all_results=[])])
        resp = await worker.api_my_points(_get("/api/points", _token()), make_env(db=db))
        assert _parse(resp)["data"] == {"total_points": 0, "recent": []}


class TestRouting:
    async def test_routes_reach_the_handlers(self):
        env = make_env(db=RecordingDB([make_stmt(all_results=[])]))
        resp = await worker._dispatch(_get("/api/challenges"), env)
        assert resp.status == 200
        resp = await worker._dispatch(_get("/api/points"), make_env())
        assert resp.status == 401
        resp = await worker._dispatch(_post("/api/challenges/c-1/submit", {"submission_text": "x"}), make_env())
        assert resp.status == 401

    async def test_current_is_not_treated_as_an_id(self):
        db = RecordingDB([make_stmt(first=_challenge_row())])
        resp = await worker._dispatch(_get("/api/challenges/current"), make_env(db=db))
        assert resp.status == 200
        assert "challenge_type = 'weekly'" in db.sql[0]


class TestSchemaInSync:
    def test_tables_defined_in_migration_schema_and_ddl(self):
        migration = (LEARN_DIR / "migrations" / "0017_challenges.sql").read_text(encoding="utf-8")
        schema = (LEARN_DIR / "schema.sql").read_text(encoding="utf-8")
        ddl = "\n".join(worker._DDL)
        for text in (migration, schema, ddl):
            for table in ("challenges", "challenge_submissions", "user_points"):
                assert re.search(rf"CREATE TABLE IF NOT EXISTS {table}\b", text), table
            assert "UNIQUE (user_id, challenge_id)" in text
            assert "idx_challenges_weekly_number" in text

    async def test_init_db_still_matches_the_statement_count(self):
        stmts = await make_init_db_stmts(worker)
        env = make_env(db=MockDB(stmts))
        await worker.init_db(env)
