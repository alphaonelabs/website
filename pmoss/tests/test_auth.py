"""
Unit tests for pmoss/src/auth.py.
"""

import json
from unittest.mock import AsyncMock, patch
import pytest

from auth import handle_auth, handle_auth_callback, verify_session, get_auth_token
from helpers import MockEnv, MockRequest, MockDB, make_stmt
from js import Response


class TestHandleAuth:
    async def test_auth_not_configured_returns_503(self):
        env = MockEnv(client_id="")
        resp = await handle_auth(env)
        assert resp.status == 503
        assert "not configured" in await resp.text()

    async def test_auth_configured_redirects_to_github(self):
        env = MockEnv(client_id="my_client_id", redirect_uri="https://example.com/callback")
        resp = await handle_auth(env)
        assert resp.status == 302
        location = resp.headers.get("Location")
        assert location is not None
        assert location.startswith("https://github.com/login/oauth/authorize?")
        assert "client_id=my_client_id" in location
        assert "redirect_uri=https%3A%2F%2Fexample.com%2Fcallback" in location or "redirect_uri=https://example.com/callback" in location
        assert "scope=repo+read%3Auser" in location or "scope=repo read:user" in location
        assert "state=" in location


class TestHandleAuthCallback:
    async def test_callback_without_code_returns_400(self):
        req = MockRequest(url="https://example.com/auth/callback")
        env = MockEnv()
        resp = await handle_auth_callback(req, env)
        assert resp.status == 400
        assert "No code provided" in await resp.text()

    async def test_callback_not_configured_returns_503(self):
        req = MockRequest(url="https://example.com/auth/callback?code=mock_code")
        env = MockEnv(client_id="", client_secret="")
        resp = await handle_auth_callback(req, env)
        assert resp.status == 503
        assert "not configured" in await resp.text()

    async def test_callback_successful_session_creation(self):
        req = MockRequest(url="https://example.com/auth/callback?code=valid_code")
        insert_stmt = make_stmt()
        db = MockDB([insert_stmt])
        env = MockEnv(db=db)

        token_mock_resp = Response.new(json.dumps({"access_token": "gho_test_token_123"}), status=200)
        user_mock_resp = Response.new(json.dumps({"login": "octocat"}), status=200)

        async def fake_fetch(url, options=None):
            if "access_token" in str(url):
                return token_mock_resp
            return user_mock_resp

        with patch("auth.fetch", side_effect=fake_fetch):
            resp = await handle_auth_callback(req, env)

        assert resp.status == 302
        assert resp.headers.get("Location") == "/"
        cookie = resp.headers.get("Set-Cookie")
        assert cookie is not None
        assert "session=" in cookie
        assert "HttpOnly" in cookie
        assert "SameSite=Strict" in cookie
        # Verify DB insert
        assert len(db.queries) == 1
        assert "INSERT INTO sessions" in db.queries[0]
        # Check bind args
        bind_args = insert_stmt.bind.call_args[0]
        assert bind_args[1] == "octocat"
        assert bind_args[2] == "gho_test_token_123"

    async def test_callback_github_token_error_returns_500(self):
        req = MockRequest(url="https://example.com/auth/callback?code=bad_code")
        env = MockEnv()

        error_mock_resp = Response.new(
            json.dumps({"error": "bad_verification_code", "error_description": "The code passed is invalid."}),
            status=200,
        )

        with patch("auth.fetch", new=AsyncMock(return_value=error_mock_resp)):
            resp = await handle_auth_callback(req, env)

        assert resp.status == 500
        assert "Authentication failed" in await resp.text()


class TestVerifySession:
    async def test_no_cookie_returns_none(self):
        req = MockRequest(headers={})
        env = MockEnv()
        result = await verify_session(req, env)
        assert result is None

    async def test_cookie_without_session_returns_none(self):
        req = MockRequest(headers={"Cookie": "other_pref=dark; theme=blue"})
        env = MockEnv()
        result = await verify_session(req, env)
        assert result is None

    async def test_session_not_found_in_db_returns_none(self):
        req = MockRequest(headers={"Cookie": "session=invalid_session_id"})
        select_stmt = make_stmt(first=None)
        env = MockEnv(db=MockDB([select_stmt]))
        result = await verify_session(req, env)
        assert result is None

    async def test_valid_session_returns_user_dict(self):
        req = MockRequest(headers={"Cookie": "session=valid_session_123"})
        session_row = {
            "id": "valid_session_123",
            "username": "octocat",
            "access_token": "gho_secret_token",
            "expires_at": "2099-01-01T00:00:00",
        }
        select_stmt = make_stmt(first=session_row)
        env = MockEnv(db=MockDB([select_stmt]))
        result = await verify_session(req, env)
        assert result is not None
        assert result["id"] == "valid_session_123"
        assert result["username"] == "octocat"
        assert result["accessToken"] == "gho_secret_token"

    async def test_db_error_returns_none_safely(self):
        req = MockRequest(headers={"Cookie": "session=crash_session"})
        stmt = make_stmt()
        stmt.bind.return_value.first.side_effect = Exception("D1 connection lost")
        env = MockEnv(db=MockDB([stmt]))
        result = await verify_session(req, env)
        assert result is None


class TestGetAuthToken:
    def test_bearer_token_extracted(self):
        req = MockRequest(headers={"Authorization": "Bearer my_secret_token_abc"})
        assert get_auth_token(req) == "my_secret_token_abc"

    def test_no_auth_header_returns_none(self):
        req = MockRequest(headers={})
        assert get_auth_token(req) is None

    def test_basic_auth_returns_none(self):
        req = MockRequest(headers={"Authorization": "Basic dXNlcjpwYXNz"})
        assert get_auth_token(req) is None
