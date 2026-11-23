from __future__ import annotations

import json
import sqlite3
from types import SimpleNamespace
from typing import Any, Sequence

from tests.helpers import MockRequest, load_worker, make_env

worker = load_worker()

UNLINK_SQL = "UPDATE credentials SET user_id=NULL, certificate_id=NULL WHERE user_id=?"
ENROLLMENTS_SQL = "DELETE FROM enrollments WHERE user_id=?"
CART_ITEMS_SQL = "DELETE FROM activity_cart_items WHERE cart_id=?"
CART_LOOKUP_SQL = "SELECT id FROM activity_carts WHERE user_id=?"

Args = tuple[Any, ...]


def is_write(sql: str) -> bool:
    return not sql.lstrip().upper().startswith("SELECT")


class _Bound:
    def __init__(self, db: "_DB", sql: str, args: Args) -> None:
        self.db, self.sql, self.args = db, sql, args

    async def run(self) -> SimpleNamespace:
        return await self.db.execute(self.sql, self.args)

    async def all(self) -> SimpleNamespace:
        return await self.db.execute(self.sql, self.args)


class _Stmt:
    def __init__(self, db: "_DB", sql: str) -> None:
        self.db, self.sql = db, sql

    def bind(self, *args: Any) -> _Bound:
        return _Bound(self.db, self.sql, args)


class _DB:
    def __init__(
        self,
        *,
        batch_error: str | None = None,
        fail_cart_lookup: bool = False,
        carts: bool = False,
        fail_sql: str | None = None,
    ) -> None:
        self.batch_error = batch_error
        self.fail_cart_lookup = fail_cart_lookup
        self.carts = carts
        self.fail_sql = fail_sql
        self.events: list[tuple[Any, ...]] = []
        self.cart_lookups: list[Args] = []
        self.batch_attempts: list[list[tuple[str, Args]]] = []

    def prepare(self, sql: str) -> _Stmt:
        return _Stmt(self, sql)

    async def execute(self, sql: str, args: Args) -> SimpleNamespace:
        self.events.append(("exec", sql, args))
        if sql == CART_LOOKUP_SQL:
            self.cart_lookups.append(args)
            if self.fail_cart_lookup:
                raise RuntimeError("cart lookup failed")
            return SimpleNamespace(results=[SimpleNamespace(id="cart-1")] if self.carts else [])
        if self.fail_sql and sql.startswith(self.fail_sql):
            raise RuntimeError("cleanup failed")
        return SimpleNamespace(results=[], meta={"changes": 1})

    async def batch(self, stmts: Sequence[_Bound]) -> None:
        payload = [(s.sql, s.args) for s in stmts]
        self.batch_attempts.append(payload)
        if self.batch_error:
            has_unlink = any(sql == UNLINK_SQL for sql, _ in payload)
            if has_unlink or "credentials" not in self.batch_error:
                raise RuntimeError(self.batch_error)  # whole batch rolls back
        self.events.append(("batch", payload))

    def writes(self) -> list[str]:
        out: list[str] = []
        for e in self.events:
            if e[0] == "exec" and is_write(e[1]):
                out.append(e[1])
            elif e[0] == "batch":
                out.extend(sql for sql, _ in e[1])
        return out


def _delete_request() -> MockRequest:
    token = worker.create_token("u1", "someone", "member", "test-jwt-secret")
    return MockRequest(
        method="DELETE",
        url="http://localhost/api/profile",
        headers={"Authorization": "Bearer " + token},
        body=json.dumps({"confirmation": "DELETE"}),
    )


async def _delete(db: _DB) -> Any:
    env = make_env(db=db)
    env.SENTRY_DSN = ""
    return await worker.api_delete_account(_delete_request(), env)


async def test_critical_changes_commit_in_one_batch_before_any_other_write() -> None:
    db = _DB(carts=True)
    resp = await _delete(db)
    assert resp.status == 200

    assert len(db.batch_attempts) == 1
    revoke, unlink, enrollments, anonymize = db.batch_attempts[0]

    assert revoke[0].startswith("UPDATE credentials SET status='revoked'")
    assert revoke[1] == ("u1",)

    assert unlink == (UNLINK_SQL, ("u1",))
    assert enrollments == (ENROLLMENTS_SQL, ("u1",))

    assert anonymize[0].startswith("UPDATE users SET username_hash")
    assert anonymize[1][-1] == "u1"

    batch_idx = next(i for i, e in enumerate(db.events) if e[0] == "batch")
    assert [e for e in db.events[:batch_idx] if e[0] == "exec" and is_write(e[1])] == []

    cart_delete = next(i for i, e in enumerate(db.events) if e[0] == "exec" and e[1] == CART_ITEMS_SQL)
    assert cart_delete > batch_idx
    assert db.events[cart_delete][2] == ("cart-1",)
    assert ENROLLMENTS_SQL not in [e[1] for e in db.events if e[0] == "exec"]


async def test_batch_failure_changes_nothing_and_aborts() -> None:
    db = _DB(batch_error="disk I/O error")
    resp = await _delete(db)
    assert resp.status == 500
    assert len(db.batch_attempts) == 1          # the injected error was actually hit
    assert db.writes() == []                    # nothing committed, nothing executed


async def test_cart_lookup_failure_aborts_before_any_change() -> None:
    db = _DB(fail_cart_lookup=True)
    resp = await _delete(db)
    assert resp.status == 500
    assert db.cart_lookups == [("u1",)]         # the lookup itself raised
    assert db.batch_attempts == []
    assert db.writes() == []


async def test_missing_credentials_table_retries_without_unlink() -> None:
    db = _DB(batch_error="no such table: credentials")
    resp = await _delete(db)
    assert resp.status == 200
    assert len(db.batch_attempts) == 2
    first, second = db.batch_attempts

    assert first[0][0].startswith("UPDATE credentials SET status='revoked'")
    assert first[0][1] == ("u1",)

    assert first[1] == (UNLINK_SQL, ("u1",))
    assert first[2] == (ENROLLMENTS_SQL, ("u1",))
    assert len(first) == 4

    assert second[0] == (ENROLLMENTS_SQL, ("u1",))
    assert len(second) == 2
    assert second[1][0].startswith("UPDATE users SET username_hash")


async def test_other_missing_table_is_not_swallowed() -> None:
    db = _DB(batch_error="no such table: enrollments")
    resp = await _delete(db)
    assert resp.status == 500
    assert len(db.batch_attempts) == 1
    assert db.writes() == []


async def test_cleanup_failure_after_commit_does_not_fail_the_deletion() -> None:
    db = _DB(carts=True, fail_sql="DELETE FROM activity_cart_items")
    resp = await _delete(db)
    assert resp.status == 200
    assert len(db.batch_attempts) == 1


def _enroll_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE users (id TEXT PRIMARY KEY, password_hash TEXT);
        CREATE TABLE enrollments (
            id TEXT PRIMARY KEY, activity_id TEXT, user_id TEXT,
            role TEXT, status TEXT DEFAULT 'active', UNIQUE (activity_id, user_id));
        INSERT INTO users VALUES ('active', 'abc'), ('gone', 'deleted:xyz');
        """
    )
    return conn


def test_join_insert_is_skipped_for_a_deleted_account() -> None:
    conn = _enroll_db()
    for uid, expected in (("active", 1), ("gone", 0)):
        cur = conn.execute(worker._JOIN_ENROLL_SQL, ("e-" + uid, "a1", uid, "participant", uid))
        assert cur.rowcount == expected


def test_checkout_insert_is_skipped_for_a_deleted_account() -> None:
    conn = _enroll_db()
    for uid, expected in (("active", 1), ("gone", 0)):
        cur = conn.execute(
            worker._CHECKOUT_ENROLL_SQL, ("e-" + uid, "a1", uid, "participant", "active", uid)
        )
        assert cur.rowcount == expected

def test_password_updates_skip_deleted_accounts() -> None:
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        "CREATE TABLE users (id TEXT PRIMARY KEY, password_hash TEXT);"
        "INSERT INTO users VALUES ('active','old'), ('gone','deleted:xyz');"
    )
    sql = "UPDATE users SET password_hash=? WHERE id=? AND password_hash NOT LIKE 'deleted:%'"
    assert conn.execute(sql, ("new", "active")).rowcount == 1
    assert conn.execute(sql, ("new", "gone")).rowcount == 0
    assert conn.execute("SELECT password_hash FROM users WHERE id='gone'").fetchone()[0] == "deleted:xyz"