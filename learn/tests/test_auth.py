"""
Tests for HTTP auth helpers: _is_basic_auth_valid(), parse_json_object().
"""

import base64
import json

from tests.helpers import MockRequest, basic_auth_header, load_worker, make_env

worker = load_worker()


# ---------------------------------------------------------------------------
# _is_basic_auth_valid()
# ---------------------------------------------------------------------------

class TestIsBasicAuthValid:
    def _req(self, user="admin", password="adminpass"):
        return MockRequest(headers={"Authorization": basic_auth_header(user, password)})

    def _env(self, user="admin", password="adminpass"):
        return make_env(admin_user=user, admin_pass=password)

    def test_valid_credentials_returns_true(self):
        assert worker._is_basic_auth_valid(self._req(), self._env()) is True

    def test_wrong_password_returns_false(self):
        assert worker._is_basic_auth_valid(self._req(password="wrong"), self._env()) is False

    def test_wrong_username_returns_false(self):
        assert worker._is_basic_auth_valid(self._req(user="hacker"), self._env()) is False

    def test_no_auth_header_returns_false(self):
        req = MockRequest()  # no Authorization header
        assert worker._is_basic_auth_valid(req, self._env()) is False

    def test_bearer_token_not_basic_returns_false(self):
        req = MockRequest(headers={"Authorization": "Bearer sometoken"})
        assert worker._is_basic_auth_valid(req, self._env()) is False

    def test_empty_env_user_returns_false(self):
        env = make_env(admin_user="", admin_pass="pass")
        assert worker._is_basic_auth_valid(self._req(), env) is False

    def test_empty_env_pass_returns_false(self):
        env = make_env(admin_user="admin", admin_pass="")
        assert worker._is_basic_auth_valid(self._req(), env) is False

    def test_malformed_base64_returns_false(self):
        req = MockRequest(headers={"Authorization": "Basic !!! not base64 !!!"})
        assert worker._is_basic_auth_valid(req, self._env()) is False

    def test_no_colon_in_decoded_returns_false(self):
        encoded = base64.b64encode(b"adminpassnocolon").decode()
        req = MockRequest(headers={"Authorization": f"Basic {encoded}"})
        assert worker._is_basic_auth_valid(req, self._env()) is False

    def test_case_insensitive_basic_prefix(self):
        # "basic " (lowercase) should also be accepted
        encoded = base64.b64encode(b"admin:adminpass").decode()
        req = MockRequest(headers={"Authorization": f"basic {encoded}"})
        assert worker._is_basic_auth_valid(req, self._env()) is True

    def test_colon_in_password_still_works(self):
        env = make_env(admin_user="admin", admin_pass="pass:with:colons")
        encoded = base64.b64encode(b"admin:pass:with:colons").decode()
        req = MockRequest(headers={"Authorization": f"Basic {encoded}"})
        assert worker._is_basic_auth_valid(req, env) is True


# ---------------------------------------------------------------------------
# parse_json_object()
# ---------------------------------------------------------------------------

class TestParseJsonObject:
    async def test_valid_object_returns_body(self):
        req = MockRequest(body=json.dumps({"username": "alice"}))
        body, err = await worker.parse_json_object(req)
        assert err is None
        assert body == {"username": "alice"}

    async def test_empty_body_returns_error(self):
        req = MockRequest(body="")
        body, err = await worker.parse_json_object(req)
        assert body is None
        assert err is not None
        assert err.status == 400

    async def test_invalid_json_returns_error(self):
        req = MockRequest(body="not json")
        body, err = await worker.parse_json_object(req)
        assert body is None
        assert err is not None

    async def test_json_array_returns_error(self):
        req = MockRequest(body=json.dumps([1, 2, 3]))
        body, err = await worker.parse_json_object(req)
        assert body is None
        assert err is not None

    async def test_json_null_returns_error(self):
        req = MockRequest(body="null")
        body, err = await worker.parse_json_object(req)
        assert body is None
        assert err is not None

    async def test_nested_object_returns_body(self):
        payload = {"a": {"b": [1, 2, 3]}}
        req = MockRequest(body=json.dumps(payload))
        body, err = await worker.parse_json_object(req)
        assert err is None
        assert body == payload

    async def test_empty_object_returns_body(self):
        req = MockRequest(body="{}")
        body, err = await worker.parse_json_object(req)
        assert err is None
        assert body == {}


# ---------------------------------------------------------------------------
# Dynamic password pepper injection (Issue #3)
# ---------------------------------------------------------------------------

class TestDynamicPasswordPepper:
    def teardown_method(self):
        worker.reset_pepper()

    def test_explicit_pepper_alters_hash(self):
        h_default = worker.hash_password("SecretPass123!", "user1")
        h_pepper_a = worker.hash_password("SecretPass123!", "user1", pepper=b"custom-pepper-A")
        h_pepper_b = worker.hash_password("SecretPass123!", "user1", pepper=b"custom-pepper-B")

        assert h_pepper_a != h_pepper_b
        assert h_pepper_a != h_default
        assert h_pepper_b != h_default

    def test_verify_password_with_matching_and_mismatched_pepper(self):
        stored = worker.hash_password("SecretPass123!", "user1", pepper=b"test-pepper")
        assert worker.verify_password("SecretPass123!", stored, "user1", pepper=b"test-pepper") is True
        assert worker.verify_password("SecretPass123!", stored, "user1", pepper=b"wrong-pepper") is False
        assert worker.verify_password("SecretPass123!", stored, "user1") is False

    def test_pepper_injection_from_env_binding(self):
        env = make_env(password_pepper="env-injected-pepper-12345")
        h = worker.hash_password("SecretPass123!", "user1", env=env)
        assert worker.verify_password("SecretPass123!", h, "user1", env=env) is True
        assert worker.verify_password("SecretPass123!", h, "user1") is False

    def test_pepper_alias_support(self):
        env = make_env()
        env.PASSWORD_PEPPER = None
        env.PEPPER = "legacy-alias-pepper"
        h = worker.hash_password("SecretPass123!", "user1", env=env)
        assert worker.verify_password("SecretPass123!", h, "user1", env=env) is True

    def test_pepper_injection_from_os_environ(self, monkeypatch):
        monkeypatch.setenv("PASSWORD_PEPPER", "os-env-pepper-999")
        h = worker.hash_password("SecretPass123!", "user1")
        assert worker.verify_password("SecretPass123!", h, "user1") is True

    def test_production_fails_closed_when_pepper_missing(self, monkeypatch):
        import pytest
        monkeypatch.delenv("PASSWORD_PEPPER", raising=False)
        monkeypatch.delenv("PEPPER", raising=False)
        env = make_env()
        env.ENVIRONMENT = "production"
        env.PASSWORD_PEPPER = None
        env.PEPPER = None

        with pytest.raises(RuntimeError, match="Missing required environment secret: PASSWORD_PEPPER"):
            worker.get_pepper(env)

    async def test_worker_startup_on_fetch_fails_closed_in_production_without_pepper(self, monkeypatch):
        monkeypatch.delenv("PASSWORD_PEPPER", raising=False)
        monkeypatch.delenv("PEPPER", raising=False)
        monkeypatch.setattr(worker, "_SENTRY_INITIALIZED", False)
        monkeypatch.setattr(worker, "_SENTRY_DSN", "")
        env = make_env()
        env.SENTRY_DSN = ""
        env.ENVIRONMENT = "production"
        env.PASSWORD_PEPPER = None
        env.PEPPER = None
        req = MockRequest(method="GET", url="http://localhost/api/activities")

        r = await worker.on_fetch(req, env)
        assert r.status == 500

    def test_unconfigured_deployment_fails_closed_without_dev_signal(self, monkeypatch):
        import pytest
        monkeypatch.delenv("PASSWORD_PEPPER", raising=False)
        monkeypatch.delenv("PEPPER", raising=False)
        monkeypatch.delenv("IS_TEST_HARNESS", raising=False)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        env = make_env()
        env.ENVIRONMENT = ""
        env.SENTRY_ENVIRONMENT = ""
        with pytest.raises(RuntimeError, match="Missing required environment secret: PASSWORD_PEPPER"):
            worker.get_pepper(env)

    def test_production_succeeds_when_pepper_is_present(self):
        env = make_env()
        env.ENVIRONMENT = "production"
        env.PASSWORD_PEPPER = "production-secure-pepper-abc"
        assert worker.get_pepper(env) == b"production-secure-pepper-abc"

    def test_init_pepper_caches_active_pepper(self):
        test_pepper = "cached-active-pepper-val"
        env = make_env(password_pepper=test_pepper)
        worker.init_pepper(env)
        h = worker.hash_password("SecretPass123!", "user1")
        assert h == worker.hash_password("SecretPass123!", "user1", pepper=test_pepper.encode("utf-8"))
        assert h != worker.hash_password("SecretPass123!", "user1", pepper=worker._DEFAULT_PEPPER)
        assert worker.verify_password("SecretPass123!", h, "user1") is True

    def test_legacy_default_pepper_hash_verifies_with_custom_pepper(self):
        legacy_hash = worker.hash_password("SecretPass123!", "user1", pepper=worker._DEFAULT_PEPPER)
        custom_env = make_env(password_pepper="custom-active-pepper-987")
        worker.init_pepper(custom_env)
        assert worker.verify_password("SecretPass123!", legacy_hash, "user1", env=custom_env) is True

