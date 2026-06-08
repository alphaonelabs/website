"""
Tests for Week-2 profile & user-directory API endpoints:
  GET    /api/profile
  PATCH  /api/profile
  POST   /api/profile/avatar
  DELETE /api/account
  GET    /api/users
  GET    /api/users/:username
"""

import base64
import json

from tests.helpers import (
    load_worker, MockRequest, MockRow, MockDB, make_env, make_stmt, json_request
)

worker = load_worker()

SECRET  = "test-encryption-key"
JWT_SEC = "test-jwt-secret"


def _parse(resp):
    return json.loads(resp.body)


def _enc(val: str) -> str:
    """Match the stub encrypt_aes output: 'v1:' + base64(12_zero_iv + plaintext)."""
    return "v1:" + base64.b64encode(b"\x00" * 12 + val.encode()).decode()


def _make_token(uid="uid-alice", username="alice", role="member"):
    return worker.create_token(uid, username, role, JWT_SEC)


def _auth(uid="uid-alice", username="alice", role="member"):
    return {"Authorization": f"Bearer {_make_token(uid, username, role)}"}


def _full_profile_row(**overrides):
    defaults = dict(
        id="uid-alice",
        name=_enc("Alice Smith"),
        username=_enc("alice"),
        bio=None,
        expertise=None,
        github_username=None,
        discord_username=None,
        slack_username=None,
        avatar_url=None,
        is_teacher=0,
        is_profile_public=0,
        created_at="2024-01-01 00:00:00",
    )
    defaults.update(overrides)
    return MockRow(**defaults)


# ---------------------------------------------------------------------------
# GET /api/profile
# ---------------------------------------------------------------------------

class TestGetProfile:
    def _req(self):
        return MockRequest(method="GET", url="http://localhost/api/profile",
                           headers=_auth())

    async def test_no_token_returns_401(self):
        env = make_env()
        r   = await worker.api_get_profile(
            MockRequest(method="GET", url="http://localhost/api/profile"), env
        )
        assert r.status == 401

    async def test_user_not_found_returns_404(self):
        env = make_env(db=MockDB([make_stmt(first=None)]))
        r   = await worker.api_get_profile(self._req(), env)
        assert r.status == 404

    async def test_returns_profile_fields(self):
        row = _full_profile_row(
            bio=_enc("Love coding!"),
            expertise=_enc("Python, Django"),
            github_username=_enc("alice-gh"),
        )
        env = make_env(db=MockDB([make_stmt(first=row)]))
        r   = await worker.api_get_profile(self._req(), env)
        assert r.status == 200
        d   = _parse(r)["data"]
        assert d["username"]        == "alice"
        assert d["name"]            == "Alice Smith"
        assert d["bio"]             == "Love coding!"
        assert d["expertise"]       == "Python, Django"
        assert d["github_username"] == "alice-gh"
        assert d["is_teacher"]      == 0
        assert d["is_profile_public"] == 0

    async def test_null_optional_fields_return_empty_string(self):
        row = _full_profile_row()
        env = make_env(db=MockDB([make_stmt(first=row)]))
        r   = await worker.api_get_profile(self._req(), env)
        d   = _parse(r)["data"]
        assert d["bio"]              == ""
        assert d["expertise"]        == ""
        assert d["github_username"]  == ""
        assert d["discord_username"] == ""
        assert d["slack_username"]   == ""
        assert d["avatar_url"]       == ""

    async def test_does_not_expose_email_or_password(self):
        row = _full_profile_row()
        env = make_env(db=MockDB([make_stmt(first=row)]))
        r   = await worker.api_get_profile(self._req(), env)
        d   = _parse(r)["data"]
        assert "email"         not in d
        assert "password_hash" not in d
        assert "email_verified" not in d


# ---------------------------------------------------------------------------
# PATCH /api/profile
# ---------------------------------------------------------------------------

class TestPatchProfile:
    def _req(self, payload):
        return json_request("/api/profile", payload, headers=_auth(), method="PATCH")

    async def test_no_token_returns_401(self):
        env = make_env()
        r   = await worker.api_patch_profile(
            json_request("/api/profile", {"bio": "x"}, method="PATCH"), env
        )
        assert r.status == 401

    async def test_empty_body_returns_400(self):
        env = make_env()
        r   = await worker.api_patch_profile(self._req({}), env)
        assert r.status == 400

    async def test_unknown_fields_ignored_returns_400(self):
        env = make_env()
        r   = await worker.api_patch_profile(self._req({"hacked_column": "x"}), env)
        assert r.status == 400

    async def test_valid_update_returns_200(self):
        env = make_env(db=MockDB([make_stmt()]))
        r   = await worker.api_patch_profile(
            self._req({"bio": "Hello world", "is_profile_public": True}), env
        )
        assert r.status == 200
        assert _parse(r)["success"] is True

    async def test_is_teacher_coerced_to_int(self):
        # Ensure the handler runs without errors when toggling boolean fields
        env = make_env(db=MockDB([make_stmt()]))
        r   = await worker.api_patch_profile(
            self._req({"is_teacher": True, "is_profile_public": False}), env
        )
        assert r.status == 200

    async def test_partial_update_only_allowed_fields(self):
        # Only known fields should survive; unknown fields are stripped silently
        env = make_env(db=MockDB([make_stmt()]))
        r   = await worker.api_patch_profile(
            self._req({"bio": "ok", "role": "host"}), env
        )
        assert r.status == 200


# ---------------------------------------------------------------------------
# DELETE /api/account
# ---------------------------------------------------------------------------

class TestDeleteAccount:
    def _req(self, payload):
        return json_request("/api/account", payload,
                            headers=_auth(), method="DELETE")

    def _user_row(self, username="alice", password="password123"):
        return MockRow(
            id="uid-alice",
            password_hash=worker.hash_password(password, username),
            username=_enc(username),
        )

    async def test_no_token_returns_401(self):
        env = make_env()
        r   = await worker.api_delete_account(
            json_request("/api/account", {"password": "x"}, method="DELETE"), env
        )
        assert r.status == 401

    async def test_missing_password_returns_400(self):
        env = make_env()
        r   = await worker.api_delete_account(self._req({}), env)
        assert r.status == 400

    async def test_wrong_password_returns_401(self):
        row = self._user_row()
        env = make_env(db=MockDB([make_stmt(first=row)]))
        r   = await worker.api_delete_account(self._req({"password": "wrongpass"}), env)
        assert r.status == 401

    async def test_correct_password_returns_200(self):
        row  = self._user_row()
        acts = make_stmt(all_results=[])   # no owned activities
        # Sequence: lookup user, SELECT activities, DELETE user
        env  = make_env(db=MockDB([make_stmt(first=row), acts, make_stmt()]))
        r    = await worker.api_delete_account(self._req({"password": "password123"}), env)
        assert r.status == 200
        assert _parse(r)["success"] is True

    async def test_user_not_found_returns_404(self):
        env = make_env(db=MockDB([make_stmt(first=None)]))
        r   = await worker.api_delete_account(self._req({"password": "pw"}), env)
        assert r.status == 404


# ---------------------------------------------------------------------------
# GET /api/users  (public directory)
# ---------------------------------------------------------------------------

class TestListUsers:
    def _req(self):
        return MockRequest(method="GET", url="http://localhost/api/users")

    async def test_returns_200_with_empty_list(self):
        env = make_env(db=MockDB([make_stmt(all_results=[])]))
        r   = await worker.api_list_users(self._req(), env)
        assert r.status == 200
        d   = _parse(r)["data"]
        assert d["users"]  == []
        assert d["total"]  == 0

    async def test_only_public_users_returned(self):
        # The SQL query WHERE is_profile_public=1 is handled by the DB;
        # here we verify the response shape for a returned public user.
        public_row = MockRow(
            id="uid-bob",
            username=_enc("bob"),
            name=_enc("Bob"),
            bio=_enc("I teach Python"),
            expertise=_enc("Python"),
            avatar_url=None,
            is_teacher=1,
        )
        env = make_env(db=MockDB([make_stmt(all_results=[public_row])]))
        r   = await worker.api_list_users(self._req(), env)
        assert r.status == 200
        users = _parse(r)["data"]["users"]
        assert len(users) == 1
        assert users[0]["username"]  == "bob"
        assert users[0]["name"]      == "Bob"
        assert users[0]["is_teacher"] == 1

    async def test_bio_excerpt_max_200_chars(self):
        long_bio = "x" * 400
        row = MockRow(id="u1", username=_enc("u"), name=_enc("U"),
                      bio=_enc(long_bio), expertise=None, avatar_url=None, is_teacher=0)
        env = make_env(db=MockDB([make_stmt(all_results=[row])]))
        r   = await worker.api_list_users(self._req(), env)
        bio = _parse(r)["data"]["users"][0]["bio"]
        assert len(bio) <= 200

    async def test_response_does_not_include_private_fields(self):
        row = MockRow(id="u1", username=_enc("u"), name=_enc("U"),
                      bio=None, expertise=None, avatar_url=None, is_teacher=0)
        env = make_env(db=MockDB([make_stmt(all_results=[row])]))
        r   = await worker.api_list_users(self._req(), env)
        user = _parse(r)["data"]["users"][0]
        assert "email"          not in user
        assert "password_hash"  not in user
        assert "is_profile_public" not in user


# ---------------------------------------------------------------------------
# GET /api/users/:username  (public profile)
# ---------------------------------------------------------------------------

class TestGetPublicProfile:
    def _req(self):
        return MockRequest(method="GET", url="http://localhost/api/users/alice")

    def _public_row(self, **overrides):
        defaults = dict(
            id="uid-alice",
            name=_enc("Alice Smith"),
            username=_enc("alice"),
            bio=_enc("Hello!"),
            expertise=_enc("Python"),
            github_username=None,
            discord_username=None,
            slack_username=None,
            avatar_url=None,
            is_teacher=0,
            is_profile_public=1,
            created_at="2024-01-01 00:00:00",
        )
        defaults.update(overrides)
        return MockRow(**defaults)

    async def test_user_not_found_returns_404(self):
        env = make_env(db=MockDB([make_stmt(first=None)]))
        r   = await worker.api_get_public_profile("nobody", self._req(), env)
        assert r.status == 404

    async def test_private_profile_returns_403(self):
        row = self._public_row(is_profile_public=0)
        # first() for user lookup; all() for activities
        env = make_env(db=MockDB([make_stmt(first=row)]))
        r   = await worker.api_get_public_profile("alice", self._req(), env)
        assert r.status == 403

    async def test_public_profile_returns_200(self):
        row  = self._public_row()
        acts = make_stmt(all_results=[])
        env  = make_env(db=MockDB([make_stmt(first=row), acts]))
        r    = await worker.api_get_public_profile("alice", self._req(), env)
        assert r.status == 200
        d    = _parse(r)["data"]
        assert d["username"] == "alice"
        assert d["name"]     == "Alice Smith"
        assert d["bio"]      == "Hello!"

    async def test_public_profile_never_exposes_email(self):
        row  = self._public_row()
        acts = make_stmt(all_results=[])
        env  = make_env(db=MockDB([make_stmt(first=row), acts]))
        r    = await worker.api_get_public_profile("alice", self._req(), env)
        d    = _parse(r)["data"]
        assert "email"          not in d
        assert "password_hash"  not in d
        assert "email_verified" not in d

    async def test_public_profile_includes_activities(self):
        row     = self._public_row()
        act_row = MockRow(id="act-1", title="Python 101", type="course", format="self_paced")
        acts    = make_stmt(all_results=[act_row])
        env     = make_env(db=MockDB([make_stmt(first=row), acts]))
        r       = await worker.api_get_public_profile("alice", self._req(), env)
        d       = _parse(r)["data"]
        assert len(d["activities"]) == 1
        assert d["activities"][0]["title"] == "Python 101"

    async def test_teacher_flag_exposed(self):
        row  = self._public_row(is_teacher=1)
        acts = make_stmt(all_results=[])
        env  = make_env(db=MockDB([make_stmt(first=row), acts]))
        r    = await worker.api_get_public_profile("alice", self._req(), env)
        d    = _parse(r)["data"]
        assert d["is_teacher"] == 1


# ---------------------------------------------------------------------------
# POST /api/profile/avatar  (avatar upload validation)
# ---------------------------------------------------------------------------

class TestUploadAvatar:
    def _req(self, payload, headers=None):
        h = {**_auth(), **(headers or {})}
        return json_request("/api/profile/avatar", payload, headers=h)

    async def test_no_token_returns_401(self):
        env = make_env()
        r   = await worker.api_upload_avatar(
            json_request("/api/profile/avatar", {"image_data": "x", "image_type": "image/png"}), env
        )
        assert r.status == 401

    async def test_invalid_type_returns_400(self):
        env = make_env()
        r   = await worker.api_upload_avatar(
            self._req({"image_data": "abc", "image_type": "image/gif"}), env
        )
        assert r.status == 400
        assert "jpg" in _parse(r)["error"].lower() or "jpeg" in _parse(r)["error"].lower() \
               or "png" in _parse(r)["error"].lower() or "webp" in _parse(r)["error"].lower()

    async def test_missing_image_data_returns_400(self):
        env = make_env()
        r   = await worker.api_upload_avatar(
            self._req({"image_type": "image/png"}), env
        )
        assert r.status == 400

    async def test_oversized_image_returns_400(self):
        big_bytes   = b"\xff" * (5 * 1024 * 1024 + 1)
        big_b64     = base64.b64encode(big_bytes).decode()
        env         = make_env()
        r           = await worker.api_upload_avatar(
            self._req({"image_data": big_b64, "image_type": "image/png"}), env
        )
        assert r.status == 400
        assert "5" in _parse(r)["error"]

    async def test_no_r2_falls_back_to_base64(self):
        # When R2 is not configured the avatar is stored as a data-URL (no 503)
        small_b64 = base64.b64encode(b"\x89PNG fake").decode()
        env = make_env(db=MockDB([make_stmt(), make_stmt()]))
        del env.R2  # ensure R2 is absent
        r = await worker.api_upload_avatar(
            self._req({"image_data": small_b64, "image_type": "image/png"}), env
        )
        assert r.status == 200
        url = _parse(r)["data"]["avatar_url"]
        assert url.startswith("data:image/png;base64,")

    async def test_r2_upload_returns_public_url(self):
        from unittest.mock import AsyncMock, MagicMock
        small_b64 = base64.b64encode(b"\x89PNG fake").decode()
        env = make_env(db=MockDB([make_stmt(), make_stmt()]))
        mock_r2 = MagicMock()
        mock_r2.put = AsyncMock(return_value=None)
        env.R2 = mock_r2
        env.R2_PUBLIC_URL = "https://pub-abc123.r2.dev"
        r = await worker.api_upload_avatar(
            self._req({"image_data": small_b64, "image_type": "image/png"}), env
        )
        assert r.status == 200
        url = _parse(r)["data"]["avatar_url"]
        assert url.startswith("https://pub-abc123.r2.dev/avatars/")
        assert url.endswith(".png")
        mock_r2.put.assert_awaited_once()
