"""
Tests for HTTP auth helpers: _is_basic_auth_valid(), parse_json_object().
"""

import base64
import json
from tests.helpers import load_worker, MockRequest, make_env, basic_auth_header

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
