"""
Tests for challenge badges (migration 0018).
Covers:
- POST /api/badges (role check, validation, challenge must exist)
- GET /api/badges (public) and GET /api/badges/me (caller only)
- submitting a challenge awards its active badges in the same batch as the points
- account deletion removes the user's challenge data
- migration, schema.sql and _DDL stay in sync
"""

import datetime
import json
import re
from pathlib import Path
from unittest.mock import AsyncMock

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

worker = load_worker()

JWT_SECRET = "test-jwt-secret"
LEARN_DIR = Path(__file__).parent.parent

TODAY = datetime.datetime.now(datetime.timezone.utc).date()
YESTERDAY = (TODAY - datetime.timedelta(days=1)).isoformat()
TOMORROW = (TODAY + datetime.timedelta(days=1)).isoformat()


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
        id="c-1", title="Week 1", description="Write a haiku", challenge_type="weekly",
        week_number=1, start_date=YESTERDAY, end_date=TOMORROW, points=10,
        created_at="2026-11-01 10:00:00",
    )
    values.update(overrides)
    return MockRow(**values)


def _badge_row(**overrides):
    values = dict(
        id="b-1", name="Haiku Master", description="Wrote a haiku", badge_type="challenge",
        challenge_id="c-1", icon="medal", is_active=1, created_at="2026-11-01 10:00:00",
    )
    values.update(overrides)
    return MockRow(**values)


def _valid_body(**overrides):
    body = {"name": "Haiku Master", "description": "Wrote a haiku", "challenge_id": "c-1"}
    body.update(overrides)
    return body


class RecordingDB(MockDB):
    """MockDB that remembers every statement it hands out and supports batch()."""

    def __init__(self, stmts=None):
        super().__init__(stmts)
        self.prepared = []
        self.batch = AsyncMock(return_value=[])

    def prepare(self, sql):
        clean = " ".join(sql.split())
        stmt = super().prepare(sql)
        self.prepared.append((clean, stmt))
        return stmt

    def statement(self, sql_prefix):
        for sql, stmt in self.prepared:
            if sql.startswith(sql_prefix):
                return stmt
        raise AssertionError("no statement starting with " + sql_prefix)

    def bound_args(self, sql_prefix):
        return self.statement(sql_prefix).bind.call_args.args


class TestCreateBadge:
    async def test_requires_login(self):
        resp = await worker.api_create_badge(_post("/api/badges", _valid_body()), make_env())
        assert resp.status == 401

    async def test_students_cannot_create(self):
        resp = await worker.api_create_badge(_post("/api/badges", _valid_body(), _token()), make_env())
        assert resp.status == 403

    async def test_host_creates_a_badge_for_an_existing_challenge(self):
        db = RecordingDB([make_stmt(first=MockRow(id="c-1")), make_stmt()])
        resp = await worker.api_create_badge(
            _post("/api/badges", _valid_body(), _token(uid="host-1", role="host")), make_env(db=db)
        )
        assert resp.status == 200
        data = _parse(resp)["data"]
        assert data["name"] == "Haiku Master"
        assert data["icon"] == "medal"
        args = db.bound_args("INSERT INTO badges")
        assert args[-1] == "host-1"  # created_by comes from the token
        assert args[4] == "c-1"

    async def test_created_by_in_body_is_ignored(self):
        db = RecordingDB([make_stmt(first=MockRow(id="c-1")), make_stmt()])
        await worker.api_create_badge(
            _post("/api/badges", _valid_body(created_by="someone-else"), _token(uid="host-1", role="host")),
            make_env(db=db),
        )
        assert "someone-else" not in db.bound_args("INSERT INTO badges")

    async def test_unknown_challenge_is_404_and_writes_nothing(self):
        db = RecordingDB([make_stmt(first=None)])
        resp = await worker.api_create_badge(
            _post("/api/badges", _valid_body(), _token(role="host")), make_env(db=db)
        )
        assert resp.status == 404
        assert not any(sql.startswith("INSERT") for sql, _ in db.prepared)

    async def test_rejects_bad_fields(self):
        cases = [
            {"name": "  "},
            {"description": ""},
            {"badge_type": "teacher_awarded"},
            {"challenge_id": ""},
        ]
        for override in cases:
            resp = await worker.api_create_badge(
                _post("/api/badges", _valid_body(**override), _token(role="admin")), make_env()
            )
            assert resp.status == 400, override

    async def test_long_icon_is_cut_to_16_characters(self):
        db = RecordingDB([make_stmt(first=MockRow(id="c-1")), make_stmt()])
        resp = await worker.api_create_badge(
            _post("/api/badges", _valid_body(icon="x" * 50), _token(role="host")), make_env(db=db)
        )
        assert len(_parse(resp)["data"]["icon"]) == 16


class TestReadBadges:
    async def test_list_is_public_and_only_asks_for_active_badges(self):
        db = RecordingDB([make_stmt(all_results=[_badge_row(), _badge_row(id="b-2", name="Zed")])])
        resp = await worker.api_list_badges(_get("/api/badges"), make_env(db=db))
        assert resp.status == 200
        assert [b["id"] for b in _parse(resp)["badges"]] == ["b-1", "b-2"]
        assert "is_active = 1" in db.prepared[0][0]

    async def test_list_can_filter_by_challenge_and_bounds_the_limit(self):
        db = RecordingDB([make_stmt(all_results=[])])
        await worker.api_list_badges(_get("/api/badges?challenge_id=c-9&limit=9999"), make_env(db=db))
        assert "AND challenge_id = ?" in db.prepared[0][0]
        assert db.bound_args("SELECT") == ("c-9", 100)

    async def test_my_badges_requires_login(self):
        resp = await worker.api_my_badges(_get("/api/badges/me"), make_env())
        assert resp.status == 401

    async def test_my_badges_only_asks_for_the_callers_rows(self):
        earned = MockRow(id="b-1", name="Haiku Master", description="d", icon="medal",
                         challenge_id="c-1", award_method="challenge_completion",
                         awarded_at="2026-11-02 09:00:00")
        db = RecordingDB([make_stmt(all_results=[earned])])
        resp = await worker.api_my_badges(_get("/api/badges/me", _token(uid="user-7")), make_env(db=db))
        assert resp.status == 200
        assert _parse(resp)["data"]["badges"][0]["name"] == "Haiku Master"
        assert db.bound_args("SELECT") == ("user-7",)

    async def test_me_is_not_treated_as_an_id(self):
        db = RecordingDB([make_stmt(all_results=[])])
        resp = await worker._dispatch(_get("/api/badges/me", _token()), make_env(db=db))
        assert resp.status == 200
        assert "JOIN badges" in db.prepared[0][0]


def _submit(db, uid="user-9"):
    req = _post("/api/challenges/c-1/submit", {"submission_text": "my haiku"}, _token(uid=uid))
    return worker.api_submit_challenge(req, make_env(db=db), "c-1")


class TestBadgeAwardOnSubmit:
    async def test_active_badges_are_awarded_in_the_same_batch(self):
        db = RecordingDB([
            make_stmt(first=_challenge_row()),                                   # challenge
            make_stmt(first=None),                                               # no earlier submission
            make_stmt(all_results=[MockRow(id="b-1", name="Haiku Master")]),     # badges for the challenge
        ])
        resp = await _submit(db)
        assert resp.status == 200
        data = _parse(resp)["data"]
        assert data["badges_awarded"] == [{"id": "b-1", "name": "Haiku Master"}]
        db.batch.assert_awaited_once()
        assert len(db.batch.await_args.args[0]) == 3  # submission, points, badge

        submission_args = db.bound_args("INSERT INTO challenge_submissions")
        badge_args = db.bound_args("INSERT OR IGNORE INTO user_badges")
        assert badge_args[1:3] == ("user-9", "b-1")
        assert badge_args[3] == submission_args[0]  # linked to this submission

    async def test_every_active_badge_gets_its_own_row(self):
        db = RecordingDB([
            make_stmt(first=_challenge_row()),
            make_stmt(first=None),
            make_stmt(all_results=[MockRow(id="b-1", name="A"), MockRow(id="b-2", name="B")]),
        ])
        resp = await _submit(db)
        assert len(_parse(resp)["data"]["badges_awarded"]) == 2
        assert len(db.batch.await_args.args[0]) == 4

    async def test_no_badges_means_only_submission_and_points(self):
        db = RecordingDB([make_stmt(first=_challenge_row()), make_stmt(first=None), make_stmt(all_results=[])])
        resp = await _submit(db)
        assert _parse(resp)["data"]["badges_awarded"] == []
        assert len(db.batch.await_args.args[0]) == 2

    async def test_the_badge_lookup_only_asks_for_active_badges_of_this_challenge(self):
        db = RecordingDB([make_stmt(first=_challenge_row()), make_stmt(first=None), make_stmt(all_results=[])])
        await _submit(db)
        sql = next(s for s, _ in db.prepared if s.startswith("SELECT id, name FROM badges"))
        assert "challenge_id = ?" in sql and "is_active = 1" in sql
        assert db.bound_args("SELECT id, name FROM badges") == ("c-1",)

    async def test_a_second_submission_awards_nothing(self):
        db = RecordingDB([make_stmt(first=_challenge_row()), make_stmt(first=MockRow(id="s-1"))])
        resp = await _submit(db)
        assert resp.status == 409
        db.batch.assert_not_awaited()

    async def test_a_rejected_batch_awards_no_badge(self):
        db = RecordingDB([
            make_stmt(first=_challenge_row()), make_stmt(first=None),
            make_stmt(all_results=[MockRow(id="b-1", name="A")]),
        ])
        db.batch.side_effect = Exception("UNIQUE constraint failed: challenge_submissions.user_id")
        resp = await _submit(db)
        assert resp.status == 409
        assert "badges_awarded" not in resp.body


class BindRecordingDB(MockDB):
    """MockDB that remembers every (sql, bound values) pair the handler runs."""

    def __init__(self):
        super().__init__()
        self.calls = []

    def prepare(self, sql):
        stmt = super().prepare(sql)
        normalized = " ".join(sql.split())
        original_bind = stmt.bind

        def bind(*args):
            self.calls.append((normalized, args))
            return original_bind(*args)

        stmt.bind = bind
        return stmt


class TestAccountDeletion:
    async def test_account_deletion_removes_the_users_challenge_data(self):
        db = BindRecordingDB()
        req = json_request("/api/profile", {"confirmation": "DELETE"}, headers=_auth(_token()), method="DELETE")
        resp = await worker.api_delete_account(req, make_env(db=db))
        assert resp.status == 200
        for sql in (
            "DELETE FROM user_badges WHERE user_id=?",
            "DELETE FROM user_points WHERE user_id=?",
            "DELETE FROM challenge_submissions WHERE user_id=?",
            "UPDATE challenges SET created_by=NULL WHERE created_by=?",
            "UPDATE badges SET created_by=NULL WHERE created_by=?",
        ):
            assert (sql, ("user-1",)) in db.calls, sql


class TestSchemaInSync:
    def test_tables_defined_in_migration_schema_and_ddl(self):
        migration = (LEARN_DIR / "migrations" / "0018_badges.sql").read_text(encoding="utf-8")
        schema = (LEARN_DIR / "schema.sql").read_text(encoding="utf-8")
        ddl = "\n".join(worker._DDL)
        for text in (migration, schema, ddl):
            for table in ("badges", "user_badges"):
                assert re.search(rf"CREATE TABLE IF NOT EXISTS {table}\b", text), table
            assert "UNIQUE (user_id, badge_id)" in text
            assert "idx_badges_challenge" in text

    async def test_init_db_still_matches_the_statement_count(self):
        env = make_env(db=MockDB(await make_init_db_stmts(worker)))
        await worker.init_db(env)
