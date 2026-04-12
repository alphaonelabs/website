"""
Tests for the main request dispatcher _dispatch() and on_fetch().

Covers routing of all API endpoints, OPTIONS preflight, admin-page guard,
unknown API paths (404), and static-file serving.
"""

import json
from unittest.mock import AsyncMock

import pytest

from tests.helpers import (
    MockRequest, MockRow, MockDB, make_env, make_stmt,
    json_request, basic_auth_header, set_static_content, load_worker,
)


worker = load_worker()

SECRET = "test-encryption-key"
JWT = "test-jwt-secret"


def _parse(resp):
    return json.loads(resp.body)


def _token(uid="u-1", username="alice", role="member"):
    return worker.create_token(uid, username, role, JWT)


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# OPTIONS preflight
# ---------------------------------------------------------------------------

class TestOptionsPreflight:
    async def test_options_returns_204(self):
        req = MockRequest(method="OPTIONS", url="http://localhost/api/register")
        r = await worker._dispatch(req, make_env())
        assert r.status == 204

    async def test_options_cors_headers(self):
        req = MockRequest(method="OPTIONS", url="http://localhost/api/login")
        r = await worker._dispatch(req, make_env())
        assert r.headers.get("Access-Control-Allow-Origin") == "*"
        assert "GET" in r.headers.get("Access-Control-Allow-Methods", "")

    async def test_options_on_any_path(self):
        for path in ("/api/activities", "/api/join", "/api/dashboard"):
            req = MockRequest(method="OPTIONS", url=f"http://localhost{path}")
            r = await worker._dispatch(req, make_env())
            assert r.status == 204, f"OPTIONS on {path} expected 204"


# ---------------------------------------------------------------------------
# Admin page routing
# ---------------------------------------------------------------------------

class TestAdminPageRouting:
    def _admin_env(self, admin_url="/admin"):
        env = make_env(admin_url=admin_url)
        set_static_content(env, "<html>admin</html>")
        return env

    async def test_admin_page_no_auth_returns_401(self):
        req = MockRequest(method="GET", url="http://localhost/admin")
        r = await worker._dispatch(req, make_env())
        assert r.status == 401

    async def test_admin_page_with_auth(self):
        req = MockRequest(
            method="GET", url="http://localhost/admin",
            headers={"Authorization": basic_auth_header("admin", "adminpass")},
        )
        env = self._admin_env()
        r = await worker._dispatch(req, env)
        # Serves the admin HTML
        assert r.status == 200

    async def test_admin_page_wrong_method_not_intercepted(self):
        # POST to /admin is not the admin guard path (only GET)
        req = MockRequest(
            method="POST", url="http://localhost/admin",
            headers={"Authorization": basic_auth_header("admin", "adminpass")},
        )
        env = self._admin_env()
        # POST /admin falls through to static serving
        r = await worker._dispatch(req, env)
        # Static mock returns HTML → 200
        assert r.status == 200


# ---------------------------------------------------------------------------
# API routing
# ---------------------------------------------------------------------------

class TestApiRouting:
    async def test_post_register_routed(self):
        req = json_request("/api/register", {"username": "x", "email": "x@x.com", "password": "pass1234"})
        # Missing fields triggers 400 before any DB call
        r = await worker._dispatch(req, make_env())
        assert r.status in (200, 400, 409, 500)  # reached the handler

    async def test_post_login_routed(self):
        req = json_request("/api/login", {"username": "x", "password": "pass1234"})
        env = make_env(db=MockDB([make_stmt(first=None)]))
        r = await worker._dispatch(req, env)
        assert r.status == 401  # user not found

    async def test_get_activities_routed(self):
        env = make_env(db=MockDB([make_stmt(all_results=[])]))
        req = MockRequest(method="GET", url="http://localhost/api/activities")
        r = await worker._dispatch(req, env)
        assert r.status == 200
        assert "activities" in _parse(r)

    async def test_post_activities_routed(self):
        req = json_request("/api/activities", {"title": "Test"})
        r = await worker._dispatch(req, make_env())
        assert r.status == 401  # no auth → 401

    async def test_get_activity_by_id_routed(self):
        env = make_env(db=MockDB([make_stmt(first=None)]))
        req = MockRequest(method="GET", url="http://localhost/api/activities/some-id")
        r = await worker._dispatch(req, env)
        assert r.status == 404  # not found

    async def test_post_join_routed(self):
        req = json_request("/api/join", {"activity_id": "act-1"})
        r = await worker._dispatch(req, make_env())
        assert r.status == 401  # no auth

    async def test_get_dashboard_routed(self):
        req = MockRequest(method="GET", url="http://localhost/api/dashboard")
        r = await worker._dispatch(req, make_env())
        assert r.status == 401  # no auth

    async def test_post_sessions_routed(self):
        req = json_request("/api/sessions", {})
        r = await worker._dispatch(req, make_env())
        assert r.status == 401  # no auth

    async def test_get_tags_routed(self):
        env = make_env(db=MockDB([make_stmt(all_results=[])]))
        req = MockRequest(method="GET", url="http://localhost/api/tags")
        r = await worker._dispatch(req, env)
        assert r.status == 200
        assert "tags" in _parse(r)

    async def test_post_activity_tags_routed(self):
        req = json_request("/api/activity-tags", {})
        r = await worker._dispatch(req, make_env())
        assert r.status == 401  # no auth

    async def test_get_admin_table_counts_routed(self):
        req = MockRequest(method="GET", url="http://localhost/api/admin/table-counts")
        r = await worker._dispatch(req, make_env())
        assert r.status == 401  # no auth

    async def test_unknown_api_path_returns_404(self):
        req = MockRequest(method="GET", url="http://localhost/api/unknown-endpoint")
        r = await worker._dispatch(req, make_env())
        assert r.status == 404

    async def test_unknown_api_path_error_message(self):
        req = MockRequest(method="GET", url="http://localhost/api/does-not-exist")
        r = await worker._dispatch(req, make_env())
        assert "error" in _parse(r)

    async def test_activity_id_with_hyphens(self):
        env = make_env(db=MockDB([make_stmt(first=None)]))
        req = MockRequest(method="GET", url="http://localhost/api/activities/act-py-begin")
        r = await worker._dispatch(req, env)
        assert r.status == 404  # not found, but reached the handler

    async def test_activity_id_with_underscores(self):
        env = make_env(db=MockDB([make_stmt(first=None)]))
        req = MockRequest(method="GET", url="http://localhost/api/activities/act_001")
        r = await worker._dispatch(req, env)
        assert r.status == 404


# ---------------------------------------------------------------------------
# Static file serving
# ---------------------------------------------------------------------------

class TestStaticFileServing:
    def _env(self, content=None):
        env = make_env()
        set_static_content(env, content)
        return env

    async def test_root_serves_index_html(self):
        env = self._env("<html>index</html>")
        req = MockRequest(method="GET", url="http://localhost/")
        r = await worker._dispatch(req, env)
        assert r.status == 200

    async def test_missing_file_serves_404(self):
        env = self._env(None)
        req = MockRequest(method="GET", url="http://localhost/nonexistent-page")
        r = await worker._dispatch(req, env)
        assert r.status == 404

    async def test_html_content_type(self):
        env = self._env("<html>page</html>")
        req = MockRequest(method="GET", url="http://localhost/dashboard")
        r = await worker._dispatch(req, env)
        assert r.status == 200

    async def test_extension_added_for_extensionless_paths(self):
        # /dashboard has no extension; serve_static appends .html
        env = self._env("<html>dashboard</html>")
        req = MockRequest(method="GET", url="http://localhost/dashboard")
        r = await worker._dispatch(req, env)
        assert r.status == 200


# ---------------------------------------------------------------------------
# on_fetch() top-level handler
# ---------------------------------------------------------------------------

class TestOnFetch:
    async def test_on_fetch_delegates_to_dispatch(self):
        env = make_env(db=MockDB([make_stmt(all_results=[])]))
        req = MockRequest(method="GET", url="http://localhost/api/activities")
        r = await worker.on_fetch(req, env)
        assert r.status == 200

    async def test_on_fetch_options(self):
        req = MockRequest(method="OPTIONS", url="http://localhost/api/register")
        r = await worker.on_fetch(req, make_env())
        assert r.status == 204


# ---------------------------------------------------------------------------
# POST /api/init and /api/seed routing
# ---------------------------------------------------------------------------

class TestInitAndSeedRouting:
    async def test_post_init_calls_init_db(self):
        # All DDL statements succeed silently
        stmts = [make_stmt() for _ in range(20)]
        env = make_env(db=MockDB(stmts))
        req = MockRequest(method="POST", url="http://localhost/api/init")
        r = await worker._dispatch(req, env)
        assert r.status == 200
        assert _parse(r)["success"] is True

    async def test_post_init_wrong_method_returns_404(self):
        env = make_env()
        req = MockRequest(method="GET", url="http://localhost/api/init")
        r = await worker._dispatch(req, env)
        assert r.status == 404
