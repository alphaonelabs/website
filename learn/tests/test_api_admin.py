"""
Tests for api_admin_table_counts() and admin-path access in _dispatch().
"""

import json
from tests.helpers import load_worker, MockRequest, MockRow, MockDB, make_env, make_stmt, basic_auth_header

worker = load_worker()


def _parse(resp):
    return json.loads(resp.body)


def _admin_req(user="admin", password="adminpass", url="http://localhost/api/admin/table-counts"):
    return MockRequest(
        method="GET",
        url=url,
        headers={"Authorization": basic_auth_header(user, password)},
    )


class TestApiAdminTableCounts:
    async def test_no_auth_returns_401(self):
        req = MockRequest(method="GET", url="http://localhost/api/admin/table-counts")
        r = await worker.api_admin_table_counts(req, make_env())
        assert r.status == 401

    async def test_wrong_credentials_returns_401(self):
        r = await worker.api_admin_table_counts(
            _admin_req(password="wrong"), make_env()
        )
        assert r.status == 401

    async def test_valid_credentials_returns_200(self):
        tables_row = MockRow(name="users")
        count_row = MockRow(cnt=5)
        env = make_env(db=MockDB([
            make_stmt(all_results=[tables_row]),  # sqlite_master query
            make_stmt(first=count_row),           # COUNT(*) for users
        ]))
        r = await worker.api_admin_table_counts(_admin_req(), env)
        assert r.status == 200

    async def test_returns_tables_list(self):
        tables = [MockRow(name="users"), MockRow(name="activities")]
        count_row = MockRow(cnt=3)
        env = make_env(db=MockDB([
            make_stmt(all_results=tables),
            make_stmt(first=count_row),
            make_stmt(first=count_row),
        ]))
        r = await worker.api_admin_table_counts(_admin_req(), env)
        data = _parse(r)
        assert "tables" in data
        assert len(data["tables"]) == 2

    async def test_each_table_has_name_and_count(self):
        tables = [MockRow(name="users")]
        count_row = MockRow(cnt=10)
        env = make_env(db=MockDB([
            make_stmt(all_results=tables),
            make_stmt(first=count_row),
        ]))
        r = await worker.api_admin_table_counts(_admin_req(), env)
        entry = _parse(r)["tables"][0]
        assert entry["table"] == "users"
        assert entry["count"] == 10

    async def test_empty_database_returns_empty_list(self):
        env = make_env(db=MockDB([make_stmt(all_results=[])]))
        r = await worker.api_admin_table_counts(_admin_req(), env)
        data = _parse(r)
        assert data["tables"] == []
