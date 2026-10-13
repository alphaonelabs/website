"""
Tests for JWT-lite auth tokens: create_token(), verify_token().
"""

import base64
import json
from tests.helpers import load_worker

worker = load_worker()

SECRET = "test-jwt-secret"


class TestCreateToken:
    def test_returns_string(self):
        tok = worker.create_token("uid-1", "alice", "member", SECRET)
        assert isinstance(tok, str)

    def test_contains_dot_separator(self):
        tok = worker.create_token("uid-1", "alice", "member", SECRET)
        assert "." in tok

    def test_payload_is_valid_base64_json(self):
        tok = worker.create_token("uid-1", "alice", "member", SECRET)
        payload_b64 = tok.rsplit(".", 1)[0]
        padding = (4 - len(payload_b64) % 4) % 4
        data = json.loads(base64.b64decode(payload_b64 + "=" * padding))
        assert data["id"] == "uid-1"
        assert data["username"] == "alice"
        assert data["role"] == "member"

    def test_different_users_differ(self):
        t1 = worker.create_token("u1", "alice", "member", SECRET)
        t2 = worker.create_token("u2", "bob", "host", SECRET)
        assert t1 != t2

    def test_different_secrets_differ(self):
        t1 = worker.create_token("u1", "alice", "member", "secret1")
        t2 = worker.create_token("u1", "alice", "member", "secret2")
        assert t1 != t2

    def test_host_role_preserved(self):
        tok = worker.create_token("uid-2", "bob", "host", SECRET)
        payload_b64 = tok.rsplit(".", 1)[0]
        padding = (4 - len(payload_b64) % 4) % 4
        data = json.loads(base64.b64decode(payload_b64 + "=" * padding))
        assert data["role"] == "host"


class TestVerifyToken:
    def _make_token(self, uid="u1", username="alice", role="member"):
        return worker.create_token(uid, username, role, SECRET)

    def test_valid_token_returns_payload(self):
        tok = self._make_token()
        payload = worker.verify_token(tok, SECRET)
        assert payload is not None
        assert payload["id"] == "u1"
        assert payload["username"] == "alice"
        assert payload["role"] == "member"

    def test_bearer_prefix_accepted(self):
        tok = "Bearer " + self._make_token()
        payload = worker.verify_token(tok, SECRET)
        assert payload is not None
        assert payload["id"] == "u1"

    def test_none_returns_none(self):
        assert worker.verify_token(None, SECRET) is None

    def test_empty_string_returns_none(self):
        assert worker.verify_token("", SECRET) is None

    def test_wrong_secret_returns_none(self):
        tok = self._make_token()
        assert worker.verify_token(tok, "wrong-secret") is None

    def test_tampered_signature_returns_none(self):
        tok = self._make_token()
        parts = tok.rsplit(".", 1)
        tampered = parts[0] + ".invalidsignature"
        assert worker.verify_token(tampered, SECRET) is None

    def test_no_dot_returns_none(self):
        assert worker.verify_token("nodothere", SECRET) is None

    def test_tampered_payload_returns_none(self):
        tok = self._make_token()
        # Replace payload with something else, keeping same sig
        evil_payload = base64.b64encode(b'{"id":"evil","username":"hacker","role":"host"}').decode()
        sig = tok.rsplit(".", 1)[1]
        tampered = f"{evil_payload}.{sig}"
        assert worker.verify_token(tampered, SECRET) is None

    def test_garbage_string_returns_none(self):
        assert worker.verify_token("totally.garbage.here.with.many.dots", SECRET) is None

    def test_all_roles_accepted(self):
        for role in ("member", "host", "admin"):
            tok = worker.create_token("uid", "user", role, SECRET)
            payload = worker.verify_token(tok, SECRET)
            assert payload["role"] == role

    def test_payload_contains_iat_and_exp(self):
        tok = worker.create_token("uid-1", "alice", "member", SECRET)
        payload = worker.verify_token(tok, SECRET)
        assert "iat" in payload
        assert "exp" in payload
        assert isinstance(payload["iat"], int)
        assert isinstance(payload["exp"], int)
        assert payload["exp"] == payload["iat"] + worker.DEFAULT_JWT_TTL_SECONDS

    def test_custom_ttl_respected(self):
        tok = worker.create_token("uid-1", "alice", "member", SECRET, ttl_seconds=3600)
        payload = worker.verify_token(tok, SECRET)
        assert payload["exp"] == payload["iat"] + 3600

    def test_expired_token_returns_none(self):
        # Create token with past expiration
        tok = worker.create_token("uid-1", "alice", "member", SECRET, ttl_seconds=-10)
        assert worker.verify_token(tok, SECRET, leeway_seconds=0) is None

    def test_missing_exp_returns_none(self):
        # Tokens must have an exp claim
        payload_data = {"id": "uid-1", "username": "alice", "role": "member"}
        encoded = base64.b64encode(json.dumps(payload_data).encode("utf-8")).decode("ascii")
        sig = worker._hmac.new(SECRET.encode("utf-8"), encoded.encode("utf-8"), worker.hashlib.sha256).hexdigest()
        raw_token = f"{encoded}.{sig}"
        assert worker.verify_token(raw_token, SECRET) is None

    def test_invalid_exp_type_returns_none(self):
        payload_data = {"id": "uid-1", "username": "alice", "role": "member", "exp": "not-a-number"}
        encoded = base64.b64encode(json.dumps(payload_data).encode("utf-8")).decode("ascii")
        sig = worker._hmac.new(SECRET.encode("utf-8"), encoded.encode("utf-8"), worker.hashlib.sha256).hexdigest()
        raw_token = f"{encoded}.{sig}"
        assert worker.verify_token(raw_token, SECRET) is None

    def test_far_future_iat_returns_none(self):
        # Token issued in the distant future should be rejected
        payload_data = {
            "id": "uid-1",
            "username": "alice",
            "role": "member",
            "iat": 9999999999,
            "exp": 9999999999 + 3600,
        }
        encoded = base64.b64encode(json.dumps(payload_data).encode("utf-8")).decode("ascii")
        sig = worker._hmac.new(SECRET.encode("utf-8"), encoded.encode("utf-8"), worker.hashlib.sha256).hexdigest()
        raw_token = f"{encoded}.{sig}"
        assert worker.verify_token(raw_token, SECRET) is None

    def test_leeway_window_tolerates_minor_clock_skew(self):
        # Token expired 10s ago, but leeway is 60s
        tok = worker.create_token("uid-1", "alice", "member", SECRET, ttl_seconds=-10)
        assert worker.verify_token(tok, SECRET, leeway_seconds=60) is not None
        # Token expired 70s ago with 60s leeway -> rejected
        tok_old = worker.create_token("uid-1", "alice", "member", SECRET, ttl_seconds=-70)
        assert worker.verify_token(tok_old, SECRET, leeway_seconds=60) is None
