"""
Tests for api_register() and api_login() handlers.
"""

import base64
import json
import pytest
from tests.helpers import load_worker, MockRequest, MockRow, MockDB, make_env, make_stmt, json_request

worker = load_worker()

SECRET = "test-encryption-key"
JWT = "test-jwt-secret"


@pytest.fixture(autouse=True)
def clear_auth_rate_limit_state():
    worker._AUTH_RATE_LIMIT_STATE.clear()
    yield
    worker._AUTH_RATE_LIMIT_STATE.clear()


def _parse(resp):
    return json.loads(resp.body)


def _enc(val: str) -> str:
    """
    Compute the mock-AES ciphertext synchronously.

    Our conftest stub makes ``encrypt_aes`` return:
    ``"v1:" + base64(iv=b"\\x00"*12 + plaintext_bytes)``

    We reproduce that here without touching asyncio.
    """
    iv = b"\x00" * 12
    return "v1:" + base64.b64encode(iv + val.encode("utf-8")).decode("ascii")


# ---------------------------------------------------------------------------
# api_register()
# ---------------------------------------------------------------------------

class TestApiRegister:
    def _req(self, payload):
        return json_request("/api/register", payload, headers={"CF-Connecting-IP": "127.0.0.1"})

    def _rate_limited_env(self):
        env = make_env(db=MockDB([make_stmt()]))
        env.AUTH_RATE_LIMIT_WINDOW_SECONDS = 60
        env.AUTH_RATE_LIMIT_MAX_ATTEMPTS = 2
        return env

    async def test_missing_username_returns_400(self):
        env = make_env()
        r = await worker.api_register(self._req({"email": "a@b.com", "password": "secret123"}), env)
        assert r.status == 400

    async def test_missing_email_returns_400(self):
        env = make_env()
        r = await worker.api_register(self._req({"username": "alice", "password": "secret123"}), env)
        assert r.status == 400

    async def test_missing_password_returns_400(self):
        env = make_env()
        r = await worker.api_register(self._req({"username": "alice", "email": "a@b.com"}), env)
        assert r.status == 400

    async def test_short_password_returns_400(self):
        env = make_env()
        r = await worker.api_register(
            self._req({"username": "alice", "email": "a@b.com", "password": "short"}), env
        )
        assert r.status == 400
        assert "8 characters" in _parse(r).get("error", "")

    async def test_successful_registration(self):
        # DB: prepare().bind().run() succeeds (default mock)
        env = make_env(db=MockDB([make_stmt()]))
        r = await worker.api_register(
            self._req({"username": "alice", "email": "alice@example.com", "password": "password123"}),
            env,
        )
        assert r.status == 200
        data = _parse(r)
        assert data["success"] is True
        assert "token" in data["data"]
        assert data["data"]["user"]["username"] == "alice"
        assert data["data"]["user"]["role"] == "member"

    async def test_name_defaults_to_username(self):
        env = make_env(db=MockDB([make_stmt()]))
        r = await worker.api_register(
            self._req({"username": "bob", "email": "bob@example.com", "password": "password123"}), env
        )
        data = _parse(r)
        assert data["data"]["user"]["name"] == "bob"

    async def test_custom_name_preserved(self):
        env = make_env(db=MockDB([make_stmt()]))
        r = await worker.api_register(
            self._req({"username": "bob", "email": "b@b.com", "password": "password123", "name": "Robert"}),
            env,
        )
        data = _parse(r)
        assert data["data"]["user"]["name"] == "Robert"

    async def test_duplicate_user_returns_409(self):
        # Simulate UNIQUE constraint violation from D1
        stmt = make_stmt()
        stmt.bind.return_value.run.side_effect = Exception("UNIQUE constraint failed")
        env = make_env(db=MockDB([stmt]))
        r = await worker.api_register(
            self._req({"username": "alice", "email": "alice@example.com", "password": "password123"}),
            env,
        )
        assert r.status == 409
        assert "already registered" in _parse(r).get("error", "")

    async def test_db_error_returns_500(self):
        stmt = make_stmt()
        stmt.bind.return_value.run.side_effect = Exception("some DB error")
        env = make_env(db=MockDB([stmt]))
        r = await worker.api_register(
            self._req({"username": "alice", "email": "a@b.com", "password": "password123"}), env
        )
        assert r.status == 500

    async def test_token_is_verifiable(self):
        env = make_env(db=MockDB([make_stmt()]))
        r = await worker.api_register(
            self._req({"username": "alice", "email": "a@b.com", "password": "password123"}), env
        )
        token = _parse(r)["data"]["token"]
        payload = worker.verify_token(token, JWT)
        assert payload is not None
        assert payload["username"] == "alice"

    async def test_invalid_json_returns_400(self):
        req = MockRequest(method="POST", url="http://localhost/api/register",
                          headers={"CF-Connecting-IP": "127.0.0.1"},
                          body="not-json")
        r = await worker.api_register(req, make_env())
        assert r.status == 400

    async def test_register_is_rate_limited_per_ip(self):
        env = self._rate_limited_env()
        ip = "203.0.113.10"

        first_req = self._req({"username": "alice1", "email": "alice1@example.com", "password": "password123"})
        first_req.headers["CF-Connecting-IP"] = ip
        second_req = self._req({"username": "alice2", "email": "alice2@example.com", "password": "password123"})
        second_req.headers["CF-Connecting-IP"] = ip
        third_req = self._req({"username": "alice3", "email": "alice3@example.com", "password": "password123"})
        third_req.headers["CF-Connecting-IP"] = ip

        first = await worker.api_register(first_req, env)
        second = await worker.api_register(second_req, env)
        third = await worker.api_register(third_req, env)

        assert first.status == 200
        assert second.status == 200
        assert third.status == 429
        assert "Retry-After" in third.headers
        retry_after = third.headers["Retry-After"]
        assert retry_after.isdigit()
        assert int(retry_after) > 0
        assert _parse(third).get("error") == "Too many requests"


# ---------------------------------------------------------------------------
# api_login()
# ---------------------------------------------------------------------------

class TestApiLogin:
    def _req(self, payload):
        return json_request("/api/login", payload, headers={"CF-Connecting-IP": "127.0.0.1"})

    def _rate_limited_env(self):
        env = make_env(db=MockDB([make_stmt(first=None)]))
        env.AUTH_RATE_LIMIT_WINDOW_SECONDS = 60
        env.AUTH_RATE_LIMIT_MAX_ATTEMPTS = 2
        return env

    def _make_user_row(self, username="alice", password="password123", role="member", name="Alice"):
        pw_hash = worker.hash_password(password, username)
        return MockRow(
            id="uid-alice",
            password_hash=pw_hash,
            role=_enc(role),
            name=_enc(name),
            username=_enc(username),
        )

    async def test_missing_username_returns_400(self):
        env = make_env()
        r = await worker.api_login(self._req({"password": "password123"}), env)
        assert r.status == 400

    async def test_missing_password_returns_400(self):
        env = make_env()
        r = await worker.api_login(self._req({"username": "alice"}), env)
        assert r.status == 400

    async def test_user_not_found_returns_401(self):
        env = make_env(db=MockDB([make_stmt(first=None)]))
        r = await worker.api_login(self._req({"username": "nobody", "password": "pass1234"}), env)
        assert r.status == 401

    async def test_wrong_password_returns_401(self):
        row = self._make_user_row()
        env = make_env(db=MockDB([make_stmt(first=row)]))
        r = await worker.api_login(self._req({"username": "alice", "password": "wrongpassword"}), env)
        assert r.status == 401

    async def test_successful_login(self):
        row = self._make_user_row()
        env = make_env(db=MockDB([make_stmt(first=row)]))
        r = await worker.api_login(
            self._req({"username": "alice", "password": "password123"}), env
        )
        assert r.status == 200
        data = _parse(r)
        assert data["success"] is True
        assert "token" in data["data"]
        assert data["data"]["user"]["username"] == "alice"
        assert data["data"]["user"]["role"] == "member"

    async def test_login_token_is_verifiable(self):
        row = self._make_user_row()
        env = make_env(db=MockDB([make_stmt(first=row)]))
        r = await worker.api_login(
            self._req({"username": "alice", "password": "password123"}), env
        )
        token = _parse(r)["data"]["token"]
        payload = worker.verify_token(token, JWT)
        assert payload is not None

    async def test_invalid_json_returns_400(self):
        req = MockRequest(method="POST", url="http://localhost/api/login", headers={"CF-Connecting-IP": "127.0.0.1"}, body="bad-json")
        r = await worker.api_login(req, make_env())
        assert r.status == 400

    async def test_login_is_rate_limited_per_ip(self):
        row = self._make_user_row()
        env = self._rate_limited_env()
        env.DB = MockDB([
            make_stmt(first=row),
            make_stmt(first=row),
            make_stmt(first=row),
        ])

        req1 = self._req({"username": "alice", "password": "password123"})
        req1.headers["CF-Connecting-IP"] = "203.0.113.10"
        req2 = self._req({"username": "alice", "password": "password123"})
        req2.headers["CF-Connecting-IP"] = "203.0.113.10"
        req3 = self._req({"username": "alice", "password": "password123"})
        req3.headers["CF-Connecting-IP"] = "203.0.113.10"

        first = await worker.api_login(req1, env)
        second = await worker.api_login(req2, env)
        third = await worker.api_login(req3, env)

        assert first.status == 200
        assert second.status == 200
        assert third.status == 429
        assert "Retry-After" in third.headers
        retry_after = third.headers["Retry-After"]
        assert retry_after.isdigit()
        assert int(retry_after) > 0
        assert _parse(third).get("error") == "Too many requests"

    async def test_login_rate_limit_resets_after_window(self, monkeypatch):
        row = self._make_user_row()
        env = self._rate_limited_env()
        env.DB = MockDB([
            make_stmt(first=row),
            make_stmt(first=row),
            make_stmt(first=row),
            make_stmt(first=row),
        ])

        worker._AUTH_RATE_LIMIT_STATE.clear()
        monkeypatch.setattr(worker.time, "time", lambda: 1000)

        req1 = self._req({"username": "alice", "password": "password123"})
        req1.headers["CF-Connecting-IP"] = "198.51.100.10"
        req2 = self._req({"username": "alice", "password": "password123"})
        req2.headers["CF-Connecting-IP"] = "198.51.100.10"

        assert (await worker.api_login(req1, env)).status == 200
        assert (await worker.api_login(req2, env)).status == 200

        monkeypatch.setattr(worker.time, "time", lambda: 1000 + 61)
        req3 = self._req({"username": "alice", "password": "password123"})
        req3.headers["CF-Connecting-IP"] = "198.51.100.10"
        assert (await worker.api_login(req3, env)).status == 200

        req4 = self._req({"username": "alice", "password": "password123"})
        req4.headers["CF-Connecting-IP"] = "198.51.100.10"
        assert (await worker.api_login(req4, env)).status == 200

        req5 = self._req({"username": "alice", "password": "password123"})
        req5.headers["CF-Connecting-IP"] = "198.51.100.10"
        limited = await worker.api_login(req5, env)
        assert limited.status == 429
        assert "Retry-After" in limited.headers
        limited_retry_after = limited.headers["Retry-After"]
        assert limited_retry_after.isdigit()
        assert int(limited_retry_after) > 0
        assert _parse(limited).get("error") == "Too many requests"
