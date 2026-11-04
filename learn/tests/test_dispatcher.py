"""
Tests for the main request dispatcher _dispatch() and on_fetch().

Covers routing of all API endpoints, OPTIONS preflight, admin-page guard,
unknown API paths (404), and static-file serving.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.helpers import (
    MockDB,
    MockRequest,
    basic_auth_header,
    json_request,
    load_worker,
    make_env,
    make_stmt,
    set_static_content,
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

    async def test_affiliations_clean_route_serves_page(self):
        env = self._env("<html>affiliations rendered</html>")
        req = MockRequest(method="GET", url="http://localhost/affiliations")
        r = await worker._dispatch(req, env)
        assert r.status == 200

    async def test_missing_file_renders_404_template_without_raw_tags(self):
        from unittest.mock import MagicMock
        env = make_env()
        async def mock_get(key, *args, **kwargs):
            if key == "404.html":
                return "{% extends 'base.html' %}{% block content %}Path: {{ requested_path }}{% endblock %}"
            return None
        sc = MagicMock()
        sc.get = AsyncMock(side_effect=mock_get)
        setattr(env, "__STATIC_CONTENT", sc)

        req = MockRequest(method="GET", url="http://localhost/nonexistent-page")
        r = await worker._dispatch(req, env)
        assert r.status == 404
        assert "{%" not in r.body
        assert "{{" not in r.body

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

    async def test_post_seed_without_auth_returns_401(self):
        env = make_env()
        req = MockRequest(method="POST", url="http://localhost/api/seed")
        r = await worker._dispatch(req, env)
        assert r.status == 401
        assert env.DB._idx == 0

    async def test_post_seed_wrong_basic_auth_does_not_seed(self):
        env = make_env()
        req = MockRequest(
            method="POST",
            url="http://localhost/api/seed",
            headers={"Authorization": basic_auth_header("admin", "wrong")},
        )
        r = await worker._dispatch(req, env)
        assert r.status == 401
        assert env.DB._idx == 0

    async def test_post_seed_with_admin_auth_seeds(self, monkeypatch):
        seeded = {}

        async def fake_init(_env):
            seeded["init"] = True

        async def fake_seed(_env, key):
            seeded["key"] = key

        monkeypatch.setattr(worker, "init_db", fake_init)
        monkeypatch.setattr(worker, "seed_db", fake_seed)
        env = make_env()
        req = MockRequest(
            method="POST",
            url="http://localhost/api/seed",
            headers={"Authorization": basic_auth_header("admin", "adminpass")},
        )
        r = await worker._dispatch(req, env)
        assert r.status == 200
        assert _parse(r)["success"] is True
        assert seeded == {"init": True, "key": "test-encryption-key"}

# Study groups redirection
class TestStudyGroupRedirection:
    async def test_study_groups_serves_static_page(self):
        env = make_env()
        set_static_content(env, "<html>study groups</html>")
        req = MockRequest(method="GET", url="http://localhost/study-groups")
        r = await worker._dispatch(req, env)
        assert r.status == 200

    async def test_study_groups_html_serves_static_page(self):
        env = make_env()
        set_static_content(env, "<html>study groups</html>")
        req = MockRequest(method="GET", url="http://localhost/study-groups.html")
        r = await worker._dispatch(req, env)
        assert r.status == 200

    async def test_study_group_slug_redirects_to_activity_slug(self):
        env = make_env()
        req = MockRequest(method="GET", url="http://localhost/study-groups/my-awesome-group")
        r = await worker._dispatch(req, env)
        assert r.status == 302
        assert r.headers.get("Location") == "http://localhost/activity/my-awesome-group"

    async def test_study_group_singular_slug_redirects_to_activity_slug(self):
        env = make_env()
        req = MockRequest(method="GET", url="http://localhost/study-group/my-awesome-group")
        r = await worker._dispatch(req, env)
        assert r.status == 302
        assert r.headers.get("Location") == "http://localhost/activity/my-awesome-group"


# ---------------------------------------------------------------------------
# Rate limiting tests (Issue 4)
# ---------------------------------------------------------------------------

class TestAuthRateLimiting:
    @pytest.fixture(autouse=True)
    def setup_limiter(self):
        worker._AUTH_RATE_LIMIT_STATE.clear()
        yield
        worker._AUTH_RATE_LIMIT_STATE.clear()

    async def test_burst_login_returns_429_after_5_failed_attempts(self):
        env = make_env(db=MockDB([make_stmt(first=None) for _ in range(12)]))
        ip = "198.51.100.55"

        for i in range(5):
            req = json_request(
                "/api/login",
                {"username": f"user{i}", "password": "WrongPassword1!"},
                headers={"CF-Connecting-IP": ip},
            )
            r = await worker._dispatch(req, env)
            assert r.status == 401, f"Attempt {i+1} should return 401, got {r.status}"

        # 6th burst request must be blocked
        blocked_req = json_request(
            "/api/login",
            {"username": "user5", "password": "WrongPassword1!"},
            headers={"CF-Connecting-IP": ip},
        )
        r_blocked = await worker._dispatch(blocked_req, env)
        assert r_blocked.status == 429
        assert "Retry-After" in r_blocked.headers
        assert int(r_blocked.headers["Retry-After"]) > 0
        assert "Too many requests" in _parse(r_blocked).get("error", "")

    async def test_burst_register_returns_429_after_5_attempts(self):
        env = make_env(db=MockDB([make_stmt() for _ in range(12)]))
        ip = "198.51.100.56"

        for i in range(5):
            req = json_request(
                "/api/register",
                {"username": f"user{i}", "email": f"user{i}@example.com", "password": "SuperSecret123!"},
                headers={"CF-Connecting-IP": ip},
            )
            r = await worker._dispatch(req, env)
            assert r.status == 200, f"Attempt {i+1} should return 200, got {r.status}"

        blocked_req = json_request(
            "/api/register",
            {"username": "user5", "email": "user5@example.com", "password": "SuperSecret123!"},
            headers={"CF-Connecting-IP": ip},
        )
        r_blocked = await worker._dispatch(blocked_req, env)
        assert r_blocked.status == 429
        assert "Retry-After" in r_blocked.headers
        assert int(r_blocked.headers["Retry-After"]) > 0

    async def test_burst_forgot_password_returns_429_after_5_attempts(self):
        env = make_env(db=MockDB([make_stmt(first=None) for _ in range(12)]))
        ip = "198.51.100.57"

        for i in range(5):
            req = json_request(
                "/api/forgot-password",
                {"email": f"test{i}@example.com"},
                headers={"CF-Connecting-IP": ip},
            )
            r = await worker._dispatch(req, env)
            assert r.status == 200, f"Attempt {i+1} should return 200, got {r.status}"

        blocked_req = json_request(
            "/api/forgot-password",
            {"email": "test5@example.com"},
            headers={"CF-Connecting-IP": ip},
        )
        r_blocked = await worker._dispatch(blocked_req, env)
        assert r_blocked.status == 429
        assert "Retry-After" in r_blocked.headers
        assert int(r_blocked.headers["Retry-After"]) > 0

    async def test_rate_limiting_via_durable_object_actor(self):
        do = worker.RateLimiterDO()
        mock_binding = MagicMock()
        mock_binding.idFromName.return_value = "rate_limiter_id"
        mock_binding.get.return_value = do

        env = make_env(db=MockDB([make_stmt(first=None) for _ in range(12)]))
        env.RATE_LIMITER_DO = mock_binding

        ip = "198.51.100.77"
        for i in range(5):
            req = json_request(
                "/api/login",
                {"username": f"user{i}", "password": "WrongPassword1!"},
                headers={"CF-Connecting-IP": ip},
            )
            r = await worker._dispatch(req, env)
            assert r.status == 401

        blocked_req = json_request(
            "/api/login",
            {"username": "user5", "password": "WrongPassword1!"},
            headers={"CF-Connecting-IP": ip},
        )
        r_blocked = await worker._dispatch(blocked_req, env)
        assert r_blocked.status == 429
        assert "Retry-After" in r_blocked.headers
        assert int(r_blocked.headers["Retry-After"]) > 0
        assert len(do.windows) > 0

    async def test_rate_limiting_via_kv_store(self):
        storage = {}
        mock_kv = MagicMock()
        async def mock_get(key):
            return storage.get(key)
        async def mock_put(key, val, expiration_ttl=None):
            storage[key] = val
        mock_kv.get = AsyncMock(side_effect=mock_get)
        mock_kv.put = AsyncMock(side_effect=mock_put)

        env = make_env(db=MockDB([make_stmt(first=None) for _ in range(12)]))
        env.RATE_LIMIT_KV = mock_kv

        ip = "198.51.100.88"
        for i in range(5):
            req = json_request(
                "/api/login",
                {"username": f"user{i}", "password": "WrongPassword1!"},
                headers={"CF-Connecting-IP": ip},
            )
            r = await worker._dispatch(req, env)
            assert r.status == 401

        blocked_req = json_request(
            "/api/login",
            {"username": "user5", "password": "WrongPassword1!"},
            headers={"CF-Connecting-IP": ip},
        )
        r_blocked = await worker._dispatch(blocked_req, env)
        assert r_blocked.status == 429
        assert "Retry-After" in r_blocked.headers
        assert any(k.startswith("rl:") for k in storage)

    async def test_username_hash_rate_limiting_across_different_ips(self):
        env = make_env(db=MockDB([make_stmt(first=None) for _ in range(12)]))
        username = "target_victim"

        for i in range(5):
            req = json_request(
                "/api/login",
                {"username": username, "password": "WrongPassword1!"},
                headers={"CF-Connecting-IP": f"203.0.113.{i+1}"},
            )
            r = await worker._dispatch(req, env)
            assert r.status == 401

        # 6th attempt from a fresh new IP targeting same user is blocked by username_hash
        blocked_req = json_request(
            "/api/login",
            {"username": username, "password": "WrongPassword1!"},
            headers={"CF-Connecting-IP": "203.0.113.99"},
        )
        r_blocked = await worker._dispatch(blocked_req, env)
        assert r_blocked.status == 429
        assert "Retry-After" in r_blocked.headers
        assert _parse(r_blocked).get("error") == "Too many requests"

    async def test_rate_limiter_do_sliding_window_expiry(self):
        do = worker.RateLimiterDO()
        key = "test:client:1"

        # 5 attempts at t = 1000
        for _ in range(5):
            res = await do.check_limit(key, max_attempts=5, window_seconds=60, now=1000)
            assert res["allowed"] is True

        # 6th attempt at t = 1000 is blocked
        blocked = await do.check_limit(key, max_attempts=5, window_seconds=60, now=1000)
        assert blocked["allowed"] is False
        assert blocked["retry_after"] == 60

        # Attempt after 61 seconds (t = 1061) is allowed because window slid
        allowed_later = await do.check_limit(key, max_attempts=5, window_seconds=60, now=1061)
        assert allowed_later["allowed"] is True

    async def test_rate_limiter_do_storage_error_falls_back_to_kv(self):
        mock_storage = MagicMock()
        mock_storage.get = AsyncMock(side_effect=RuntimeError("Storage connection failed"))
        mock_ctx = MagicMock()
        mock_ctx.storage = mock_storage
        do = worker.RateLimiterDO(ctx=mock_ctx)

        mock_binding = MagicMock()
        mock_binding.idFromName.return_value = "rate_limiter_id"
        mock_binding.get.return_value = do

        storage = {}
        mock_kv = MagicMock()
        async def mock_get(key):
            return storage.get(key)
        async def mock_put(key, val, expiration_ttl=None):
            storage[key] = val
        mock_kv.get = AsyncMock(side_effect=mock_get)
        mock_kv.put = AsyncMock(side_effect=mock_put)

        env = make_env(db=MockDB([make_stmt(first=None) for _ in range(12)]))
        env.RATE_LIMITER_DO = mock_binding
        env.RATE_LIMIT_KV = mock_kv

        ip = "198.51.100.99"
        for i in range(5):
            req = json_request(
                "/api/login",
                {"username": f"user{i}", "password": "WrongPassword1!"},
                headers={"CF-Connecting-IP": ip},
            )
            r = await worker._dispatch(req, env)
            assert r.status == 401

        blocked_req = json_request(
            "/api/login",
            {"username": "user5", "password": "WrongPassword1!"},
            headers={"CF-Connecting-IP": ip},
        )
        r_blocked = await worker._dispatch(blocked_req, env)
        assert r_blocked.status == 429
        assert "Retry-After" in r_blocked.headers
        assert any(k.startswith("rl:") for k in storage)

    async def test_missing_cf_connecting_ip_returns_429(self):
        env = make_env()
        req = MockRequest(method="POST", url="http://localhost/api/login", body=json.dumps({"username": "a", "password": "b"}))
        r = await worker._dispatch(req, env)
        assert r.status == 429
        assert "Retry-After" in r.headers
        assert _parse(r).get("error") == "Too many requests"
