"""
Tests for Google OAuth / Identity Services authentication:
- api_auth_config()
- api_auth_google()
- verify_google_id_token()
- Account linking and auto-registration
- Rate limiting and security checks
"""

import base64
import json
import time
import pytest
from unittest.mock import AsyncMock, MagicMock
from tests.helpers import (
    load_worker,
    MockRequest,
    MockRow,
    MockDB,
    make_env,
    make_stmt,
    json_request,
)

worker = load_worker()

CLIENT_ID = "test-google-client-id.apps.googleusercontent.com"
SECRET = "test-encryption-key"
JWT = "test-jwt-secret"


@pytest.fixture(autouse=True)
def clear_auth_rate_limit_state():
    worker._AUTH_RATE_LIMIT_STATE.clear()
    yield
    worker._AUTH_RATE_LIMIT_STATE.clear()


def _parse(resp):
    return json.loads(resp.body)


def make_mock_google_token(
    sub="100200300400500",
    email="googleuser@gmail.com",
    name="Google User",
    picture="https://lh3.googleusercontent.com/avatar.jpg",
    aud=CLIENT_ID,
    iss="https://accounts.google.com",
    exp=None,
    email_verified=True,
    alg="RS256",
    kid="test-kid",
    signature="valid_signature",
    hd=None,
):
    if exp is None:
        exp = int(time.time()) + 3600
    header = {"alg": alg, "kid": kid, "typ": "JWT"}
    payload = {
        "sub": sub,
        "email": email,
        "name": name,
        "picture": picture,
        "aud": aud,
        "iss": iss,
        "exp": exp,
        "email_verified": email_verified,
    }
    if hd:
        payload["hd"] = hd

    def b64url(b: bytes) -> str:
        return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")

    h_b64 = b64url(json.dumps(header).encode("utf-8"))
    p_b64 = b64url(json.dumps(payload).encode("utf-8"))
    sig_raw = signature.encode("utf-8") if isinstance(signature, str) else signature
    s_b64 = b64url(sig_raw)
    return f"{h_b64}.{p_b64}.{s_b64}"


def _make_google_env(db=None, client_id=CLIENT_ID):
    env = make_env(db=db)
    env.GOOGLE_CLIENT_ID = client_id
    return env


# ---------------------------------------------------------------------------
# Test api_auth_config
# ---------------------------------------------------------------------------

class TestApiAuthConfig:
    async def test_returns_configured_google_client_id(self):
        env = _make_google_env(client_id="my-google-client-id.apps.google.com")
        req = MockRequest(method="GET", url="http://localhost/api/auth/config")
        resp = await worker.api_auth_config(req, env)
        assert resp.status == 200
        data = _parse(resp)
        assert data["success"] is True
        assert data["data"]["google_client_id"] == "my-google-client-id.apps.google.com"

    async def test_returns_empty_when_not_configured(self):
        env = make_env()
        delattr(env, "GOOGLE_CLIENT_ID")
        req = MockRequest(method="GET", url="http://localhost/api/auth/config")
        resp = await worker.api_auth_config(req, env)
        assert resp.status == 200
        data = _parse(resp)
        assert data["success"] is True
        assert data["data"]["google_client_id"] == ""


# ---------------------------------------------------------------------------
# Test verify_google_id_token
# ---------------------------------------------------------------------------

class TestVerifyGoogleIdToken:
    async def test_invalid_token_string(self):
        env = _make_google_env()
        payload, err = await worker.verify_google_id_token("", CLIENT_ID, env)
        assert payload is None
        assert "Invalid" in err

    async def test_malformed_token_segments(self):
        env = _make_google_env()
        payload, err = await worker.verify_google_id_token("header.payload", CLIENT_ID, env)
        assert payload is None
        assert "format" in err

    async def test_unsupported_algorithm(self):
        env = _make_google_env()
        tok = make_mock_google_token(alg="HS256")
        payload, err = await worker.verify_google_id_token(tok, CLIENT_ID, env)
        assert payload is None
        assert "algorithm" in err

    async def test_missing_kid(self):
        env = _make_google_env()
        tok = make_mock_google_token(kid="")
        payload, err = await worker.verify_google_id_token(tok, CLIENT_ID, env)
        assert payload is None
        assert "kid" in err

    async def test_invalid_issuer(self):
        env = _make_google_env()
        tok = make_mock_google_token(iss="https://malicious-issuer.com")
        payload, err = await worker.verify_google_id_token(tok, CLIENT_ID, env)
        assert payload is None
        assert "issuer" in err

    async def test_audience_mismatch(self):
        env = _make_google_env()
        tok = make_mock_google_token(aud="other-client-id")
        payload, err = await worker.verify_google_id_token(tok, CLIENT_ID, env)
        assert payload is None
        assert "audience" in err

    async def test_expired_token(self):
        env = _make_google_env()
        tok = make_mock_google_token(exp=int(time.time()) - 100)
        payload, err = await worker.verify_google_id_token(tok, CLIENT_ID, env)
        assert payload is None
        assert "expired" in err

    async def test_unverified_email(self):
        env = _make_google_env()
        tok = make_mock_google_token(email_verified=False)
        payload, err = await worker.verify_google_id_token(tok, CLIENT_ID, env)
        assert payload is None
        assert "not verified" in err

    async def test_missing_email_or_sub(self):
        env = _make_google_env()
        tok = make_mock_google_token(email="")
        payload, err = await worker.verify_google_id_token(tok, CLIENT_ID, env)
        assert payload is None
        assert "claims" in err

    async def test_invalid_signature_rejected(self):
        env = _make_google_env()
        tok = make_mock_google_token(signature="invalid_signature")
        payload, err = await worker.verify_google_id_token(tok, CLIENT_ID, env)
        assert payload is None
        assert "signature" in err

    async def test_valid_token_succeeds(self):
        env = _make_google_env()
        tok = make_mock_google_token()
        payload, err = await worker.verify_google_id_token(tok, CLIENT_ID, env)
        assert err is None
        assert payload["sub"] == "100200300400500"
        assert payload["email"] == "googleuser@gmail.com"


# ---------------------------------------------------------------------------
# Test api_auth_google
# ---------------------------------------------------------------------------

class TestApiAuthGoogle:
    def _req(self, payload):
        return json_request("/api/auth/google", payload, headers={"CF-Connecting-IP": "127.0.0.1"})

    async def test_unconfigured_server_returns_500(self):
        env = make_env()
        delattr(env, "GOOGLE_CLIENT_ID")
        r = await worker.api_auth_google(self._req({"credential": "dummy"}), env)
        assert r.status == 500
        assert "not configured" in _parse(r).get("error", "")

    async def test_missing_credential_returns_400(self):
        env = _make_google_env()
        r = await worker.api_auth_google(self._req({}), env)
        assert r.status == 400
        assert "credential is required" in _parse(r).get("error", "")

    async def test_invalid_token_returns_401(self):
        env = _make_google_env()
        r = await worker.api_auth_google(self._req({"credential": "invalid.jwt.token"}), env)
        assert r.status == 401

    async def test_rate_limiting_enforced(self):
        env = _make_google_env()
        env.AUTH_RATE_LIMIT_WINDOW_SECONDS = 60
        env.AUTH_RATE_LIMIT_MAX_ATTEMPTS = 2
        ip = "198.51.100.5"

        req1 = self._req({"credential": "dummy"})
        req1.headers["CF-Connecting-IP"] = ip
        req2 = self._req({"credential": "dummy"})
        req2.headers["CF-Connecting-IP"] = ip
        req3 = self._req({"credential": "dummy"})
        req3.headers["CF-Connecting-IP"] = ip

        r1 = await worker.api_auth_google(req1, env)
        r2 = await worker.api_auth_google(req2, env)
        r3 = await worker.api_auth_google(req3, env)

        assert r1.status in (400, 401)
        assert r2.status in (400, 401)
        assert r3.status == 429
        assert "Retry-After" in r3.headers

    async def test_successful_login_existing_oauth_identity(self):
        user_id = "usr-google-existing"
        enc = SECRET
        user_row = MockRow(
            id=user_id,
            username=await worker.encrypt_aes("google_user", enc),
            name=await worker.encrypt_aes("Google User", enc),
            role=await worker.encrypt_aes("member", enc),
            email_verified=1,
        )
        profile_row = MockRow(avatar_url="https://lh3.googleusercontent.com/avatar.jpg")

        # Mock DB calls:
        # 1. SELECT user_id FROM oauth_identities WHERE provider=? AND provider_user_id=? -> returns user_id
        stmt_oauth = make_stmt(first=MockRow(user_id=user_id))
        # 2. SELECT ... FROM users WHERE id=? -> returns user_row
        stmt_user = make_stmt(first=user_row)
        # 3. UPDATE oauth_identities SET updated_at=...
        stmt_update_oauth = make_stmt()
        # 4. SELECT avatar_url FROM user_profiles WHERE user_id=? -> returns profile_row
        stmt_profile = make_stmt(first=profile_row)

        env = _make_google_env(db=MockDB([stmt_oauth, stmt_user, stmt_update_oauth, stmt_profile]))
        token_str = make_mock_google_token()
        r = await worker.api_auth_google(self._req({"credential": token_str}), env)
        assert r.status == 200
        data = _parse(r)
        assert data["success"] is True
        assert "token" in data["data"]
        assert data["data"]["user"]["id"] == user_id
        assert data["data"]["user"]["username"] == "google_user"

    async def test_successful_login_links_to_existing_email_account(self):
        user_id = "usr-email-match"
        enc = SECRET
        user_row = MockRow(
            id=user_id,
            username=await worker.encrypt_aes("original_user", enc),
            name=await worker.encrypt_aes("Original Name", enc),
            role=await worker.encrypt_aes("member", enc),
            email_verified=0,  # will be verified by Google
        )
        profile_row = MockRow(avatar_url="")

        # Mock DB calls:
        # 1. SELECT user_id FROM oauth_identities -> None
        stmt_oauth_miss = make_stmt(first=None)
        # 2. SELECT id FROM users WHERE email_hash=? -> returns existing user
        stmt_email_hit = make_stmt(first=MockRow(id=user_id))
        # 3. INSERT INTO oauth_identities
        stmt_insert_oauth = make_stmt()
        # 4. SELECT ... FROM users WHERE id=?
        stmt_user = make_stmt(first=user_row)
        # 5. UPDATE users SET email_verified=1
        stmt_verify_user = make_stmt()
        # 6. UPDATE oauth_identities SET updated_at
        stmt_update_oauth = make_stmt()
        # 7. SELECT avatar_url FROM user_profiles
        stmt_profile = make_stmt(first=profile_row)
        # 8. UPDATE user_profiles SET avatar_url
        stmt_update_profile = make_stmt()

        env = _make_google_env(db=MockDB([
            stmt_oauth_miss,
            stmt_email_hit,
            stmt_insert_oauth,
            stmt_user,
            stmt_verify_user,
            stmt_update_oauth,
            stmt_profile,
            stmt_update_profile,
        ]))

        token_str = make_mock_google_token()
        r = await worker.api_auth_google(self._req({"credential": token_str}), env)
        assert r.status == 200
        data = _parse(r)
        assert data["success"] is True
        assert data["data"]["user"]["id"] == user_id
        assert data["data"]["user"]["username"] == "original_user"

    async def test_successful_registration_new_user(self):
        enc = SECRET
        user_id = "usr-new-google"
        new_user_row = MockRow(
            id=user_id,
            username=await worker.encrypt_aes("googleuser", enc),
            name=await worker.encrypt_aes("Google User", enc),
            role=await worker.encrypt_aes("member", enc),
            email_verified=1,
        )

        class DynamicRegisterDB:
            def prepare(self, sql):
                stmt = MagicMock()
                bound = MagicMock()

                async def mock_first(*args):
                    if "FROM oauth_identities" in sql:
                        return None
                    if "FROM users WHERE email_hash" in sql:
                        return None
                    if "FROM users WHERE username_hash" in sql:
                        return None
                    if "FROM user_profiles WHERE referral_code_hash" in sql:
                        return None
                    if "FROM user_profiles WHERE user_id" in sql:
                        return MockRow(avatar_url="")
                    if "FROM users WHERE id=" in sql:
                        return new_user_row
                    return None

                async def mock_run(*args):
                    return None

                bound.first = AsyncMock(side_effect=mock_first)
                bound.run = AsyncMock(side_effect=mock_run)
                bound.all = AsyncMock(return_value=MagicMock(results=[]))
                stmt.bind.return_value = bound
                stmt.first = bound.first
                stmt.run = bound.run
                stmt.all = bound.all
                return stmt

        env = _make_google_env(db=DynamicRegisterDB())
        token_str = make_mock_google_token()
        r = await worker.api_auth_google(self._req({"credential": token_str}), env)
        assert r.status == 200
        data = _parse(r)
        assert data["success"] is True
        assert data["data"]["user"]["username"] == "googleuser"
        assert "token" in data["data"]


# ---------------------------------------------------------------------------
# Test COOP Header and Dispatcher Routes
# ---------------------------------------------------------------------------

class TestGoogleAuthRoutingAndHeaders:
    async def test_coop_header_allows_popups(self):
        assert worker._SECURITY_HEADERS.get("Cross-Origin-Opener-Policy") == "same-origin-allow-popups"

    async def test_dispatch_get_auth_config(self):
        env = _make_google_env(client_id="test-cid")
        req = MockRequest(method="GET", url="http://localhost/api/auth/config")
        resp = await worker._dispatch(req, env)
        assert resp.status == 200
        data = _parse(resp)
        assert data["data"]["google_client_id"] == "test-cid"

    async def test_dispatch_post_auth_google(self):
        env = _make_google_env()
        req = json_request("/api/auth/google", {"credential": ""})
        resp = await worker._dispatch(req, env)
        assert resp.status == 400


# ---------------------------------------------------------------------------
# Test Account Deletion Cleans Up oauth_identities
# ---------------------------------------------------------------------------

class TestAccountDeletionCleanup:
    async def test_delete_account_includes_oauth_identities_cleanup(self):
        enc = SECRET
        user_id = "user-to-delete"
        token = worker.create_token(user_id, "user_del", "member", JWT)

        cleaned_sqls = []

        class RecordingDB:
            def prepare(self, sql):
                cleaned_sqls.append(sql)
                return make_stmt()

        env = make_env(db=RecordingDB())
        req = json_request(
            "/api/profile",
            {"confirmation": "DELETE"},
            headers={"Authorization": f"Bearer {token}"},
            method="DELETE",
        )
        resp = await worker.api_delete_account(req, env)
        assert resp.status == 200
        assert any("DELETE FROM oauth_identities WHERE user_id=?" in s for s in cleaned_sqls)

    async def test_delete_account_fails_if_oauth_cleanup_fails(self):
        enc = SECRET
        user_id = "user-to-delete-fail"
        token = worker.create_token(user_id, "user_del_fail", "member", JWT)

        class FailingOAuthDB:
            def prepare(self, sql):
                if "DELETE FROM oauth_identities" in sql:
                    raise RuntimeError("DB disk I/O error on oauth delete")
                return make_stmt()

        env = make_env(db=FailingOAuthDB())
        req = json_request(
            "/api/profile",
            {"confirmation": "DELETE"},
            headers={"Authorization": f"Bearer {token}"},
            method="DELETE",
        )
        resp = await worker.api_delete_account(req, env)
        assert resp.status == 500
        assert "Could not delete account" in _parse(resp).get("error", "")


# ---------------------------------------------------------------------------
# Test Hardened Security and Edge Cases
# ---------------------------------------------------------------------------

class TestHardenedGoogleSecurity:
    def _req(self, body):
        return json_request("/api/auth/google", body)

    async def test_missing_matching_key_fails_closed(self):
        env = _make_google_env()
        # Token has kid='unknown-kid' not in JWKS
        token_str = make_mock_google_token(kid="unknown-kid")
        payload, err = await worker.verify_google_id_token(token_str, CLIENT_ID, env)
        assert payload is None
        assert "No matching public key" in err

    async def test_non_authoritative_email_linking_rejected(self):
        user_id = "usr-yahoo-match"
        enc = SECRET
        user_row = MockRow(
            id=user_id,
            username=await worker.encrypt_aes("yahoo_user", enc),
            name=await worker.encrypt_aes("Yahoo User", enc),
            role=await worker.encrypt_aes("member", enc),
            email_verified=1,
        )
        # Mock DB returns existing user for non-gmail domain without hd
        stmt_oauth_miss = make_stmt(first=None)
        stmt_email_hit = make_stmt(first=user_row)
        env = _make_google_env(db=MockDB([stmt_oauth_miss, stmt_email_hit]))

        token_str = make_mock_google_token(email="victim@yahoo.com")
        r = await worker.api_auth_google(self._req({"credential": token_str}), env)
        assert r.status == 409
        assert "Please log in with your password" in _parse(r).get("error", "")

    async def test_authoritative_email_linking_allowed_with_hd_claim(self):
        user_id = "usr-corp-match"
        enc = SECRET
        user_row = MockRow(
            id=user_id,
            username=await worker.encrypt_aes("corp_user", enc),
            name=await worker.encrypt_aes("Corp User", enc),
            role=await worker.encrypt_aes("member", enc),
            email_verified=1,
        )
        stmt_oauth_miss = make_stmt(first=None)
        stmt_email_hit = make_stmt(first=user_row)
        stmt_insert_oauth = make_stmt()
        stmt_user = make_stmt(first=user_row)
        stmt_update_oauth = make_stmt()
        stmt_profile = make_stmt(first=MockRow(avatar_url=""))

        env = _make_google_env(db=MockDB([
            stmt_oauth_miss,
            stmt_email_hit,
            stmt_insert_oauth,
            stmt_user,
            stmt_update_oauth,
            stmt_profile,
        ]))

        token_str = make_mock_google_token(email="employee@company.com", hd="company.com")
        r = await worker.api_auth_google(self._req({"credential": token_str}), env)
        assert r.status == 200
        assert _parse(r)["success"] is True

    async def test_unverified_account_invalidates_pre_registered_password(self):
        user_id = "usr-unverified"
        enc = SECRET
        user_row = MockRow(
            id=user_id,
            username=await worker.encrypt_aes("unverified_user", enc),
            name=await worker.encrypt_aes("Unverified User", enc),
            role=await worker.encrypt_aes("member", enc),
            email_verified=0,  # unverified account with pre-registered password
        )

        update_sqls = []

        class TestDB:
            def prepare(self, sql):
                stmt = MagicMock()
                bound = MagicMock()

                async def mock_first(*args):
                    if "FROM oauth_identities" in sql:
                        return None
                    if "FROM users WHERE email_hash" in sql:
                        return user_row
                    if "FROM users WHERE id=" in sql:
                        return user_row
                    if "FROM user_profiles" in sql:
                        return MockRow(avatar_url="")
                    return None

                async def mock_run(*args):
                    update_sqls.append((sql, args))
                    return None

                bound.first = AsyncMock(side_effect=mock_first)
                bound.run = AsyncMock(side_effect=mock_run)
                stmt.bind.return_value = bound
                stmt.first = bound.first
                stmt.run = bound.run
                return stmt

        env = _make_google_env(db=TestDB())
        token_str = make_mock_google_token(email="unverified@gmail.com")
        r = await worker.api_auth_google(self._req({"credential": token_str}), env)
        assert r.status == 200
        # Assert password_hash was invalidated in the UPDATE query
        pw_reset_query = any("UPDATE users SET email_verified=1, password_hash=?" in sql for sql, _ in update_sqls)
        assert pw_reset_query is True

    async def test_deleted_account_cannot_sign_in_or_link(self):
        user_id = "usr-deleted"
        enc = SECRET
        deleted_user_row = MockRow(
            id=user_id,
            username=await worker.encrypt_aes("del_user", enc),
            name=await worker.encrypt_aes("Deleted", enc),
            role=await worker.encrypt_aes("deleted", enc),
            email_verified=0,
        )
        stmt_oauth = make_stmt(first=MockRow(user_id=user_id))
        stmt_user = make_stmt(first=deleted_user_row)

        env = _make_google_env(db=MockDB([stmt_oauth, stmt_user]))
        token_str = make_mock_google_token()
        r = await worker.api_auth_google(self._req({"credential": token_str}), env)
        assert r.status == 403
        assert "deleted" in _parse(r).get("error", "")

    async def test_oauth_insert_failure_fails_closed(self):
        user_id = "usr-db-fail"
        enc = SECRET
        user_row = MockRow(
            id=user_id,
            username=await worker.encrypt_aes("user", enc),
            name=await worker.encrypt_aes("User", enc),
            role=await worker.encrypt_aes("member", enc),
            email_verified=1,
        )
        stmt_oauth_miss = make_stmt(first=None)
        stmt_email_hit = make_stmt(first=user_row)
        stmt_insert_fail = make_stmt()
        stmt_insert_fail.bind.return_value.run = AsyncMock(side_effect=RuntimeError("Disk full"))

        env = _make_google_env(db=MockDB([stmt_oauth_miss, stmt_email_hit, stmt_insert_fail]))
        token_str = make_mock_google_token(email="user@gmail.com")
        r = await worker.api_auth_google(self._req({"credential": token_str}), env)
        assert r.status == 500
        assert "Failed to record OAuth identity" in _parse(r).get("error", "")

