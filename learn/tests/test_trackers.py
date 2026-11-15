"""
Tests for progress trackers (migration 0016).
Covers:
- POST /api/trackers (auth, validation, ownership, defaults)
- GET /api/trackers (caller's own trackers only)
- GET /api/trackers/:id (owner only, 404 for anything else)
- migration, schema.sql and _DDL stay in sync
"""

import json
import re
from pathlib import Path

import pytest
from tests.helpers import (
    load_worker,
    MockRequest,
    MockRow,
    MockDB,
    make_env,
    make_stmt,
    json_request,
    make_init_db_stmts,
)

worker = load_worker()

JWT_SECRET = "test-jwt-secret"
LEARN_DIR = Path(__file__).parent.parent


def _parse(resp):
    return json.loads(resp.body)


def _token(uid="user-1", username="alice", role="student"):
    return worker.create_token(uid, username, role, JWT_SECRET)


def _auth(token):
    return {"Authorization": f"Bearer {token}"} if token else {}


def _get(path, token=None):
    return MockRequest(method="GET", url=f"http://localhost{path}", headers=_auth(token))


def _row(**overrides):
    values = dict(
        id="t-1", title="Read books", description="", current_value=3,
        target_value=10, color="green-600", is_public=0, embed_code="embed-1",
        created_at="2026-11-01 10:00:00", updated_at=None,
    )
    values.update(overrides)
    return MockRow(**values)


def _create_req(body, token="default"):
    tok = _token() if token == "default" else token
    return json_request("/api/trackers", body, headers=_auth(tok))


class TestCreateTracker:
    async def test_requires_auth(self):
        r = await worker.api_create_tracker(_create_req({"title": "x", "target_value": 5}, token=None), make_env())
        assert r.status == 401

    async def test_creates_private_tracker_with_defaults(self):
        stmt = make_stmt()
        r = await worker.api_create_tracker(
            _create_req({"title": "Read books", "target_value": 10}), make_env(db=MockDB([stmt]))
        )
        assert r.status == 200
        data = _parse(r)["data"]
        assert data["title"] == "Read books"
        assert data["current_value"] == 0
        assert data["target_value"] == 10
        assert data["percentage"] == 0
        assert data["color"] == "blue-600"
        assert data["is_public"] is False
        assert data["embed_code"] and data["embed_code"] != data["id"]

    async def test_owner_comes_from_token_not_body(self):
        stmt = make_stmt()
        body = {"title": "Mine", "target_value": 5, "user_id": "someone-else"}
        r = await worker.api_create_tracker(_create_req(body), make_env(db=MockDB([stmt])))
        assert r.status == 200
        bound = stmt.bind.call_args.args
        assert bound[1] == "user-1"
        assert "someone-else" not in bound

    async def test_public_flag_color_and_percentage_cap(self):
        body = {"title": "Done", "target_value": 10, "current_value": 15,
                "color": "red-600", "is_public": True}
        r = await worker.api_create_tracker(_create_req(body), make_env(db=MockDB([make_stmt()])))
        assert r.status == 200
        data = _parse(r)["data"]
        assert data["percentage"] == 100
        assert data["is_public"] is True
        assert data["color"] == "red-600"

    async def test_long_title_is_truncated(self):
        r = await worker.api_create_tracker(
            _create_req({"title": "a" * 150, "target_value": 5}), make_env(db=MockDB([make_stmt()]))
        )
        assert r.status == 200
        assert len(_parse(r)["data"]["title"]) == 100

    @pytest.mark.parametrize("body", [
        {"title": "   ", "target_value": 5},
        {"target_value": 5},
        {"title": "x"},
        {"title": "x", "target_value": 0},
        {"title": "x", "target_value": -3},
        {"title": "x", "target_value": "abc"},
        {"title": "x", "target_value": True},
        {"title": "x", "target_value": 5.5},
        {"title": "x", "target_value": 10 ** 12},
        {"title": "x", "target_value": 10, "current_value": -1},
        {"title": "x", "target_value": 10, "color": "hotpink"},
        {"title": "x", "target_value": 10, "is_public": "yes"},
    ])
    async def test_invalid_input_returns_400_and_writes_nothing(self, body):
        stmt = make_stmt()
        r = await worker.api_create_tracker(_create_req(body), make_env(db=MockDB([stmt])))
        assert r.status == 400
        assert stmt.bind.call_count == 0

    async def test_creates_table_and_retries_when_missing(self):
        first = make_stmt()
        first.bind.return_value.run.side_effect = Exception("no such table: progress_trackers")
        stmts = [first] + await make_init_db_stmts(worker) + [make_stmt()]
        r = await worker.api_create_tracker(
            _create_req({"title": "x", "target_value": 5}), make_env(db=MockDB(stmts))
        )
        assert r.status == 200


class TestListTrackers:
    async def test_requires_auth(self):
        r = await worker.api_list_trackers(_get("/api/trackers"), make_env())
        assert r.status == 401

    async def test_returns_only_the_callers_trackers(self):
        stmt = make_stmt(all_results=[
            _row(),
            _row(id="t-2", current_value=10, target_value=10, is_public=1, embed_code="embed-2"),
        ])
        r = await worker.api_list_trackers(_get("/api/trackers", _token()), make_env(db=MockDB([stmt])))
        assert r.status == 200
        trackers = _parse(r)["trackers"]
        assert [t["id"] for t in trackers] == ["t-1", "t-2"]
        assert trackers[0]["percentage"] == 30
        assert trackers[1]["percentage"] == 100
        assert trackers[1]["is_public"] is True
        assert stmt.bind.call_args.args == ("user-1",)

    async def test_empty_list(self):
        stmt = make_stmt(all_results=[])
        r = await worker.api_list_trackers(_get("/api/trackers", _token()), make_env(db=MockDB([stmt])))
        assert r.status == 200
        assert _parse(r)["trackers"] == []


class TestGetTracker:
    async def test_requires_auth(self):
        r = await worker.api_get_tracker(_get("/api/trackers/t-1"), make_env(), "t-1")
        assert r.status == 401

    async def test_returns_own_tracker(self):
        stmt = make_stmt(first=_row())
        r = await worker.api_get_tracker(
            _get("/api/trackers/t-1", _token()), make_env(db=MockDB([stmt])), "t-1"
        )
        assert r.status == 200
        assert _parse(r)["data"]["id"] == "t-1"
        # the lookup is scoped to the caller, so other people's trackers never match
        assert stmt.bind.call_args.args == ("t-1", "user-1")

    async def test_missing_or_foreign_tracker_is_404(self):
        stmt = make_stmt(first=None)
        r = await worker.api_get_tracker(
            _get("/api/trackers/t-9", _token()), make_env(db=MockDB([stmt])), "t-9"
        )
        assert r.status == 404
        assert "Tracker not found" in _parse(r).get("error", "")


class TestSchemaInSync:
    def test_table_defined_in_migration_schema_and_ddl(self):
        migration = (LEARN_DIR / "migrations" / "0016_progress_trackers.sql").read_text(encoding="utf-8")
        schema = (LEARN_DIR / "schema.sql").read_text(encoding="utf-8")
        ddl = "\n".join(worker._DDL)
        for text in (migration, schema, ddl):
            assert "progress_trackers" in text
            assert re.search(r"is_public\s+INTEGER NOT NULL DEFAULT 0", text)
