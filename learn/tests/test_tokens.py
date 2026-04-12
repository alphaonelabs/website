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
