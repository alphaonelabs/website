import json
from types import SimpleNamespace

from tests.helpers import MockRequest, load_worker, make_env

worker = load_worker()

UNLINK_SQL = "UPDATE credentials SET user_id=NULL, certificate_id=NULL WHERE user_id=?"
ENROLLMENTS_SQL = "DELETE FROM enrollments WHERE user_id=?"


class _Bound:
    def __init__(self, db, sql, args):
        self.db, self.sql, self.args = db, sql, args

    async def run(self):
        self.db.events.append(("run", self.sql, self.args))

    async def all(self):
        if self.db.fail_cart_lookup and self.sql.startswith("SELECT id FROM activity_carts"):
            raise Exception("cart lookup failed")
        self.db.events.append(("all", self.sql, self.args))
        return SimpleNamespace(results=[])


class _Stmt:
    def __init__(self, db, sql):
        self.db, self.sql = db, sql

    def bind(self, *args):
        return _Bound(self.db, self.sql, args)


class _DB:
    def __init__(self, credentials_error=None, fail_cart_lookup=False):
        self.credentials_error = credentials_error
        self.fail_cart_lookup = fail_cart_lookup
        self.events = []
        self.batch_attempts = 0

    def prepare(self, sql):
        return _Stmt(self, sql)

    async def batch(self, stmts):
        self.batch_attempts += 1
        if self.credentials_error and any(s.sql == UNLINK_SQL for s in stmts):
            raise Exception(self.credentials_error)   # whole batch rolls back
        self.events.append(("batch", [(s.sql, s.args) for s in stmts]))

    def sqls_run(self):
        return [e[1] for e in self.events if e[0] == "run"]


def _delete_request():
    token = worker.create_token("u1", "someone", "member", "test-jwt-secret")
    return MockRequest(
        method="DELETE",
        url="http://localhost/api/profile",
        headers={"Authorization": "Bearer " + token},
        body=json.dumps({"confirmation": "DELETE"}),
    )


def _env(db):
    env = make_env(db=db)
    env.SENTRY_DSN = ""
    return env


async def test_unlink_and_enrollment_delete_are_one_atomic_batch_before_other_deletes():
    db = _DB()
    resp = await worker.api_delete_account(_delete_request(), _env(db))
    assert resp.status == 200

    batches = [e for e in db.events if e[0] == "batch"]
    assert len(batches) == 1
    assert batches[0][1] == [(UNLINK_SQL, ("u1",)), (ENROLLMENTS_SQL, ("u1",))]

    batch_idx = db.events.index(batches[0])
    first_delete = next(i for i, e in enumerate(db.events)
                        if e[0] == "run" and e[1].startswith("DELETE FROM"))
    anonymize = next(i for i, e in enumerate(db.events)
                     if e[0] == "run" and e[1].startswith("UPDATE users SET username_hash"))
    assert batch_idx < first_delete < anonymize


async def test_unlink_failure_aborts_before_anything_is_changed():
    db = _DB(credentials_error="disk I/O error")
    resp = await worker.api_delete_account(_delete_request(), _env(db))
    assert resp.status == 500
    assert db.batch_attempts == 1                      # the injected error was actually hit
    assert not any(e[0] == "batch" for e in db.events)  # nothing committed
    assert db.sqls_run() == []                          # no deletes, no anonymization


async def test_cart_lookup_failure_leaves_credential_link_intact():
    db = _DB(fail_cart_lookup=True)
    resp = await worker.api_delete_account(_delete_request(), _env(db))
    assert resp.status == 500
    assert db.batch_attempts == 0                       # unlink never attempted
    assert db.sqls_run() == []


async def test_missing_credentials_table_still_removes_enrollments():
    db = _DB(credentials_error="no such table: credentials")
    resp = await worker.api_delete_account(_delete_request(), _env(db))
    assert resp.status == 200
    assert db.batch_attempts == 2
    batches = [e for e in db.events if e[0] == "batch"]
    assert batches == [("batch", [(ENROLLMENTS_SQL, ("u1",))])]