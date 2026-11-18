import json

from tests.helpers import MockRequest, load_worker, make_env, make_stmt

worker = load_worker()


class _DB:
    def __init__(self, credentials_error=None):
        self.credentials_error = credentials_error
        self.sql = []
        self.stmts = {}

    def prepare(self, sql):
        self.sql.append(sql)
        stmt = make_stmt()
        if sql.startswith("UPDATE credentials") and self.credentials_error:
            stmt.bind.return_value.run.side_effect = Exception(self.credentials_error)
        self.stmts[sql] = stmt
        return stmt


def _delete_request():
    token = worker.create_token("u1", "someone", "member", "test-jwt-secret")
    return MockRequest(
        method="DELETE",
        url="http://localhost/api/profile",
        headers={"Authorization": "Bearer " + token},
        body=json.dumps({"confirmation": "DELETE"}),
    )


async def test_credential_unlink_failure_aborts_deletion():
    db = _DB(credentials_error="disk I/O error")
    env = make_env(db=db)
    env.SENTRY_DSN = ""
    resp = await worker.api_delete_account(_delete_request(), env)
    assert resp.status == 500
    assert not any(s.startswith("UPDATE users SET username_hash") for s in db.sql)
    assert not any(s.startswith("DELETE FROM") for s in db.sql)


async def test_missing_credentials_table_is_tolerated():
    db = _DB(credentials_error="no such table: credentials")
    env = make_env(db=db)
    resp = await worker.api_delete_account(_delete_request(), env)
    assert resp.status == 200

async def test_credentials_unlinked_for_this_user_before_account_is_anonymized():
    db = _DB()
    env = make_env(db=db)
    resp = await worker.api_delete_account(_delete_request(), env)
    assert resp.status == 200

    unlink_sql = "UPDATE credentials SET user_id=NULL, certificate_id=NULL WHERE user_id=?"
    stmt = db.stmts[unlink_sql]
    stmt.bind.assert_called_once_with("u1")
    stmt.bind.return_value.run.assert_awaited_once()

    unlink = db.sql.index(unlink_sql)
    anonymize = next(i for i, s in enumerate(db.sql) if s.startswith("UPDATE users SET username_hash"))
    first_delete = next(i for i, s in enumerate(db.sql) if s.startswith("DELETE FROM"))
    assert unlink < first_delete < anonymize