"""
Tests for the referral program.

Covers ``api_get_referral``, ``api_referral_leaderboard``, the ``/ref/<code>``
redirect in ``_dispatch`` and referral attribution in ``api_register``.

These tests run the worker's real SQL against an in-memory SQLite database
(D1 is SQLite), with the schema created by the worker's own ``init_db``.
That way the referral queries themselves are exercised, not just mocked.
"""

import json
import sqlite3
from types import SimpleNamespace
from typing import Any, Iterator, Optional
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import parse_qs, urlparse

import pytest

from tests.helpers import MockRequest, json_request, load_worker, make_env

worker = load_worker()

ENC = "test-encryption-key"
JWT = "test-jwt-secret"
STRONG_PASSWORD = "Str0ng!Passw0rd#2026"


# ---------------------------------------------------------------------------
# SQLite-backed D1 stand-in
# ---------------------------------------------------------------------------

class _SqliteStatement:
    """A D1-style prepared statement that runs against a sqlite3 connection."""

    def __init__(self, conn: sqlite3.Connection, sql: str, args: tuple[Any, ...] = ()) -> None:
        """Store the connection, SQL text and bound arguments."""
        self._conn = conn
        self._sql = sql
        self._args = tuple(args)

    def bind(self, *args: Any) -> "_SqliteStatement":
        """Return a new statement with *args* bound, like D1's ``bind``."""
        return _SqliteStatement(self._conn, self._sql, args)

    def _execute(self) -> sqlite3.Cursor:
        """Run the statement, commit, and return the cursor."""
        cur = self._conn.execute(self._sql, self._args)
        self._conn.commit()
        return cur

    @staticmethod
    def _row(row: Optional[sqlite3.Row]) -> Optional[SimpleNamespace]:
        """Convert a sqlite3.Row into an object with attribute access."""
        return SimpleNamespace(**dict(row)) if row is not None else None

    async def first(self) -> Optional[SimpleNamespace]:
        """Return the first row, or ``None`` when there are no rows."""
        return self._row(self._execute().fetchone())

    async def all(self) -> SimpleNamespace:
        """Return an object whose ``results`` list holds every row."""
        return SimpleNamespace(results=[self._row(r) for r in self._execute().fetchall()])

    async def run(self) -> SimpleNamespace:
        """Execute the statement for its side effects."""
        self._execute()
        return SimpleNamespace(success=True)


class SqliteD1:
    """Minimal D1 binding backed by an in-memory SQLite database."""

    def __init__(self) -> None:
        """Open a fresh in-memory database."""
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row

    def prepare(self, sql: str) -> _SqliteStatement:
        """Return a prepared statement for *sql*."""
        return _SqliteStatement(self.conn, sql)

    def scalar(self, sql: str, *args: Any) -> Any:
        """Run *sql* directly and return the first column of the first row."""
        row = self.conn.execute(sql, args).fetchone()
        return row[0] if row else None


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_auth_rate_limit_state() -> Iterator[None]:
    """Reset the in-memory auth rate limiter so register tests don't interfere."""
    worker._AUTH_RATE_LIMIT_STATE.clear()
    yield
    worker._AUTH_RATE_LIMIT_STATE.clear()


@pytest.fixture
async def db() -> SqliteD1:
    """Return a SqliteD1 with the full schema created by ``init_db``."""
    database = SqliteD1()
    await worker.init_db(make_env(db=database))
    return database


@pytest.fixture
def env(db: SqliteD1) -> MagicMock:
    """Return a mock Worker env bound to the SQLite database."""
    return make_env(db=db)


def _parse(resp: Any) -> dict[str, Any]:
    """Decode a JSON response body."""
    return json.loads(resp.body)


def _auth(uid: str, username: str = "alice") -> dict[str, str]:
    """Return an Authorization header for a member token."""
    return {"Authorization": "Bearer " + worker.create_token(uid, username, "member", JWT)}


async def _add_user(db: SqliteD1, uid: str, name: str = "Alice") -> None:
    """Insert a minimal verified user with an encrypted display name."""
    await db.prepare(
        "INSERT INTO users (id,username_hash,email_hash,name,username,email,password_hash,role,email_verified)"
        " VALUES (?,?,?,?,?,?,?,?,1)"
    ).bind(
        uid,
        "uh-" + uid,
        "eh-" + uid,
        await worker.encrypt_aes(name, ENC) if name else "",
        await worker.encrypt_aes(uid, ENC),
        await worker.encrypt_aes(uid + "@example.com", ENC),
        "x",
        await worker.encrypt_aes("member", ENC),
    ).run()


async def _add_profile(
    db: SqliteD1, uid: str, code: Optional[str] = None, referred_by: str = "", earnings: int = 0
) -> None:
    """Insert a user_profiles row with a known referral code (or none)."""
    await db.prepare(
        "INSERT INTO user_profiles (user_id,referral_code,referral_code_hash,referred_by_user_id,referral_earnings_cents)"
        " VALUES (?,?,?,?,?)"
    ).bind(
        uid,
        await worker.encrypt_aes(code, ENC) if code else None,
        worker._referral_code_hash(code, ENC) if code else None,
        referred_by,
        earnings,
    ).run()


async def _add_member(
    db: SqliteD1, uid: str, *, name: str = "Member", code: Optional[str] = None,
    referred_by: str = "", earnings: int = 0,
) -> None:
    """Insert a user together with their profile."""
    await _add_user(db, uid, name)
    await _add_profile(db, uid, code=code, referred_by=referred_by, earnings=earnings)


async def _enroll(db: SqliteD1, uid: str, status: str, activity_id: str = "act-1") -> None:
    """Insert an enrollment for *uid* with the given status."""
    await db.prepare(
        "INSERT INTO enrollments (id,activity_id,user_id,status) VALUES (?,?,?,?)"
    ).bind(f"enr-{uid}-{activity_id}-{status}", activity_id, uid, status).run()


async def _get_referral(
    env: MagicMock, uid: str, url: str = "http://localhost/api/referral"
) -> tuple[int, dict[str, Any]]:
    """Call ``api_get_referral`` as *uid* and return (status, body)."""
    req = MockRequest(method="GET", url=url, headers=_auth(uid))
    resp = await worker.api_get_referral(req, env)
    return resp.status, _parse(resp)


async def _leaderboard(env: MagicMock, query: str = "") -> list[dict[str, Any]]:
    """Call ``api_referral_leaderboard`` and return the list of leaders."""
    req = MockRequest(method="GET", url="http://localhost/api/referral/leaderboard" + query)
    resp = await worker.api_referral_leaderboard(req, env)
    assert resp.status == 200
    return _parse(resp)["leaders"]


# ---------------------------------------------------------------------------
# GET /api/referral
# ---------------------------------------------------------------------------

class TestGetReferral:
    """``api_get_referral`` returns the caller's code, link and counts."""

    async def test_missing_token_returns_401(self, env):
        """A request without an Authorization header is rejected."""
        req = MockRequest(method="GET", url="http://localhost/api/referral")
        resp = await worker.api_get_referral(req, env)
        assert resp.status == 401

    async def test_invalid_token_returns_401(self, env):
        """A token signed with the wrong secret is rejected."""
        bad = worker.create_token("u-1", "alice", "member", "wrong-secret")
        req = MockRequest(method="GET", url="http://localhost/api/referral",
                          headers={"Authorization": "Bearer " + bad})
        resp = await worker.api_get_referral(req, env)
        assert resp.status == 401

    async def test_first_call_creates_profile_with_code(self, db, env):
        """A user without a profile gets one, with an encrypted code and its blind index."""
        await _add_user(db, "u-1")
        status, body = await _get_referral(env, "u-1")
        assert status == 200
        data = body["data"]
        code = data["referral_code"]
        assert code and code.isalnum()
        assert data["referral_earnings_cents"] == 0
        assert data["referred_count"] == 0
        assert data["referred_enrollment_count"] == 0
        assert data["referred_by_user_id"] == ""

        stored_code = db.scalar("SELECT referral_code FROM user_profiles WHERE user_id=?", "u-1")
        stored_hash = db.scalar("SELECT referral_code_hash FROM user_profiles WHERE user_id=?", "u-1")
        assert stored_code != code, "the code must be stored encrypted"
        assert await worker.decrypt_aes(stored_code, ENC) == code
        assert stored_hash == worker._referral_code_hash(code, ENC)

    async def test_code_is_stable_across_calls(self, db, env):
        """Calling the endpoint again returns the same code and keeps one profile row."""
        await _add_user(db, "u-1")
        _, first = await _get_referral(env, "u-1")
        _, second = await _get_referral(env, "u-1")
        assert first["data"]["referral_code"] == second["data"]["referral_code"]
        assert db.scalar("SELECT COUNT(*) FROM user_profiles WHERE user_id=?", "u-1") == 1

    async def test_existing_code_is_returned(self, db, env):
        """A profile that already has a code keeps it."""
        await _add_member(db, "u-1", code="KNOWN123")
        _, body = await _get_referral(env, "u-1")
        assert body["data"]["referral_code"] == "KNOWN123"

    async def test_profile_without_code_gets_one_and_keeps_referrer(self, db, env):
        """A legacy profile with no code is given one; its referrer is not lost."""
        await _add_member(db, "u-ref", code="REFCODE1")
        await _add_member(db, "u-1", code=None, referred_by="u-ref")
        _, body = await _get_referral(env, "u-1")
        data = body["data"]
        assert data["referral_code"]
        assert data["referred_by_user_id"] == "u-ref"
        assert db.scalar("SELECT referral_code_hash FROM user_profiles WHERE user_id=?", "u-1") == \
            worker._referral_code_hash(data["referral_code"], ENC)

    async def test_link_uses_request_origin(self, db, env):
        """The referral link is built from the request's scheme and host."""
        await _add_member(db, "u-1", code="ABCD2345")
        _, body = await _get_referral(env, "u-1", url="https://learn.example.org/api/referral")
        assert body["data"]["referral_link"] == "https://learn.example.org/ref/ABCD2345"

    async def test_counts_referred_users_and_their_enrollments(self, db, env):
        """Referred users are counted, and only their active/approved/completed enrollments count."""
        await _add_member(db, "u-1", code="ABCD2345", earnings=1500)
        await _add_member(db, "kid-1", referred_by="u-1")
        await _add_member(db, "kid-2", referred_by="u-1")
        await _add_member(db, "other", referred_by="someone-else")
        await _enroll(db, "kid-1", "active", "act-1")
        await _enroll(db, "kid-1", "completed", "act-2")
        await _enroll(db, "kid-2", "approved", "act-1")
        await _enroll(db, "kid-2", "pending", "act-2")
        await _enroll(db, "kid-2", "cancelled", "act-3")
        await _enroll(db, "other", "active", "act-1")

        _, body = await _get_referral(env, "u-1")
        data = body["data"]
        assert data["referred_count"] == 2
        assert data["referred_enrollment_count"] == 3
        assert data["referral_earnings_cents"] == 1500


# ---------------------------------------------------------------------------
# GET /api/referral/leaderboard
# ---------------------------------------------------------------------------

class TestLeaderboard:
    """``api_referral_leaderboard`` ranks members who referred someone."""

    async def test_empty_when_nobody_has_referred(self, db, env):
        """With no referrals at all, the leaderboard is empty."""
        await _add_member(db, "u-1", code="AAAA1111")
        assert await _leaderboard(env) == []

    async def test_members_without_referrals_are_excluded(self, db, env):
        """Only members with referrals, referred enrollments or earnings are listed."""
        await _add_member(db, "u-1", name="Alice", code="AAAA1111")
        await _add_member(db, "u-2", name="Bob", code="BBBB2222")
        await _add_member(db, "kid", referred_by="u-1")
        leaders = await _leaderboard(env)
        assert [l["user_id"] for l in leaders] == ["u-1"]
        assert leaders[0] == {
            "rank": 1,
            "user_id": "u-1",
            "name": "Alice",
            "referred_count": 1,
            "referred_enrollment_count": 0,
            "referral_earnings_cents": 0,
        }

    async def test_earnings_alone_qualify(self, db, env):
        """A member with earnings but no current referrals is still listed."""
        await _add_member(db, "u-1", code="AAAA1111", earnings=500)
        leaders = await _leaderboard(env)
        assert [l["user_id"] for l in leaders] == ["u-1"]

    async def test_ordering_uses_referrals_then_enrollments_then_earnings(self, db, env):
        """Ties on referred count fall back to enrollments, then earnings."""
        # most-referrals: 3 referrals.
        await _add_member(db, "most-referrals", code="AAAA0001")
        for i in range(3):
            await _add_member(db, f"m-kid-{i}", referred_by="most-referrals")
        # more-enrollments: 1 referral with 2 counted enrollments.
        await _add_member(db, "more-enrollments", code="AAAA0002")
        await _add_member(db, "e-kid", referred_by="more-enrollments")
        await _enroll(db, "e-kid", "active", "act-1")
        await _enroll(db, "e-kid", "completed", "act-2")
        # poorer / richer: 1 referral, 0 enrollments, different earnings.
        # poorer is inserted first so only the earnings tie-break can put richer ahead.
        await _add_member(db, "poorer", code="AAAA0004", earnings=100)
        await _add_member(db, "p-kid", referred_by="poorer")
        await _add_member(db, "richer", code="AAAA0003", earnings=900)
        await _add_member(db, "r-kid", referred_by="richer")

        leaders = await _leaderboard(env)
        assert [l["user_id"] for l in leaders] == ["most-referrals", "more-enrollments", "richer", "poorer"]
        assert [l["rank"] for l in leaders] == [1, 2, 3, 4]

    async def test_undecryptable_name_falls_back(self, db, env):
        """A name that can't be decrypted is shown as a generic member name."""
        await _add_user(db, "u-1", name="Alice")
        await db.prepare("UPDATE users SET name='v1:%%%' WHERE id='u-1'").run()
        await _add_profile(db, "u-1", code="AAAA1111", earnings=100)
        leaders = await _leaderboard(env)
        assert leaders[0]["name"] == "Alpha One Labs member"

    async def test_no_contact_details_are_exposed(self, db, env):
        """Leaderboard entries only carry the public fields."""
        await _add_member(db, "u-1", code="AAAA1111", earnings=100)
        leaders = await _leaderboard(env)
        assert set(leaders[0]) == {
            "rank", "user_id", "name", "referred_count",
            "referred_enrollment_count", "referral_earnings_cents",
        }

    @pytest.mark.parametrize("query, expected", [
        ("", 10),
        ("?limit=3", 3),
        ("?limit=0", 1),
        ("?limit=-5", 1),
        ("?limit=abc", 10),
        ("?limit=999", 50),
    ])
    async def test_limit_is_clamped(self, db, env, query, expected):
        """``limit`` defaults to 10 and is clamped to 1..50."""
        for i in range(55):
            await _add_member(db, f"u-{i:02d}", earnings=i + 1)
        assert len(await _leaderboard(env, query)) == expected


# ---------------------------------------------------------------------------
# /ref/<code> redirect and API routing
# ---------------------------------------------------------------------------

class TestReferralRoutes:
    """Routing for the referral link and the referral APIs."""

    @pytest.mark.parametrize("path", ["/ref/ABCD2345", "/ref/ABCD2345/"])
    async def test_ref_link_redirects_to_registration(self, env, path):
        """``/ref/<code>`` redirects to the register tab with the code prefilled."""
        resp = await worker._dispatch(MockRequest(method="GET", url="http://localhost" + path), env)
        assert resp.status == 302
        location = urlparse(resp.headers["Location"])
        assert location.path == "/login"
        assert parse_qs(location.query) == {"tab": ["register"], "referral_code": ["ABCD2345"]}

    async def test_ref_link_with_invalid_characters_does_not_redirect(self, env):
        """Codes outside ``[A-Za-z0-9_-]`` never reach the redirect."""
        resp = await worker._dispatch(
            MockRequest(method="GET", url="http://localhost/ref/%3Cscript%3E"), env
        )
        assert resp.status != 302
        assert "Location" not in resp.headers

    async def test_ref_link_ignores_post(self, env):
        """Only GET requests are redirected."""
        resp = await worker._dispatch(MockRequest(method="POST", url="http://localhost/ref/ABCD2345"), env)
        assert resp.status != 302

    async def test_api_referral_is_routed(self, db, env):
        """``GET /api/referral`` reaches ``api_get_referral``."""
        await _add_member(db, "u-1", code="ABCD2345")
        req = MockRequest(method="GET", url="http://localhost/api/referral", headers=_auth("u-1"))
        resp = await worker._dispatch(req, env)
        assert resp.status == 200
        assert _parse(resp)["data"]["referral_code"] == "ABCD2345"

    async def test_api_leaderboard_is_routed(self, env):
        """``GET /api/referral/leaderboard`` reaches the leaderboard handler."""
        resp = await worker._dispatch(
            MockRequest(method="GET", url="http://localhost/api/referral/leaderboard"), env
        )
        assert resp.status == 200
        assert _parse(resp) == {"leaders": []}


# ---------------------------------------------------------------------------
# Referral attribution in POST /api/register
# ---------------------------------------------------------------------------

class TestRegisterAttribution:
    """``api_register`` links a new account to the member whose code was used."""

    @pytest.fixture(autouse=True)
    def no_email(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Stop registration from sending a real verification email."""
        monkeypatch.setattr(worker, "send_verification_email", AsyncMock(return_value=True))

    async def _register(self, env: MagicMock, username: str, referral_code: Optional[str] = None) -> Any:
        """Register *username*, optionally with a referral code, and return the response."""
        payload = {"username": username, "email": f"{username}@example.com", "password": STRONG_PASSWORD}
        if referral_code is not None:
            payload["referral_code"] = referral_code
        req = json_request("/api/register", payload, headers={"CF-Connecting-IP": "127.0.0.1"})
        return await worker.api_register(req, env)

    def _new_user_id(self, db: SqliteD1, username: str) -> Optional[str]:
        """Return the id of the user registered as *username*."""
        return db.scalar("SELECT id FROM users WHERE username_hash=?", worker.blind_index(username, ENC))

    async def test_valid_code_attributes_new_user(self, db, env):
        """Registering with a valid code records the referrer on the new profile."""
        await _add_member(db, "referrer", code="ABCD2345")
        resp = await self._register(env, "newbie", "ABCD2345")
        assert resp.status == 200, resp.body
        uid = self._new_user_id(db, "newbie")
        assert db.scalar("SELECT referred_by_user_id FROM user_profiles WHERE user_id=?", uid) == "referrer"

    async def test_attribution_shows_up_for_referrer(self, db, env):
        """After a referred sign-up, the referrer's count and the leaderboard reflect it."""
        await _add_member(db, "referrer", name="Rita", code="ABCD2345")
        await self._register(env, "newbie", "ABCD2345")
        _, body = await _get_referral(env, "referrer")
        assert body["data"]["referred_count"] == 1
        leaders = await _leaderboard(env)
        assert [(l["user_id"], l["name"], l["referred_count"]) for l in leaders] == [("referrer", "Rita", 1)]

    async def test_new_user_gets_own_code(self, db, env):
        """A referred user gets a referral code of their own, different from the referrer's."""
        await _add_member(db, "referrer", code="ABCD2345")
        await self._register(env, "newbie", "ABCD2345")
        uid = self._new_user_id(db, "newbie")
        stored = db.scalar("SELECT referral_code FROM user_profiles WHERE user_id=?", uid)
        own_code = await worker.decrypt_aes(stored, ENC)
        assert own_code and own_code != "ABCD2345"

    async def test_surrounding_whitespace_is_ignored(self, db, env):
        """A code pasted with spaces around it still matches."""
        await _add_member(db, "referrer", code="ABCD2345")
        resp = await self._register(env, "newbie", "  ABCD2345  ")
        assert resp.status == 200
        uid = self._new_user_id(db, "newbie")
        assert db.scalar("SELECT referred_by_user_id FROM user_profiles WHERE user_id=?", uid) == "referrer"

    async def test_unknown_code_is_rejected_without_creating_user(self, db, env):
        """An unknown code returns 400 and no account is created."""
        await _add_member(db, "referrer", code="ABCD2345")
        resp = await self._register(env, "newbie", "NOPE0000")
        assert resp.status == 400
        assert "referral code" in _parse(resp)["error"].lower()
        assert self._new_user_id(db, "newbie") is None

    @pytest.mark.parametrize("code", [None, "", "   "])
    async def test_no_code_means_no_referrer(self, db, env, code):
        """Without a code (or with a blank one) the new profile has no referrer."""
        resp = await self._register(env, "newbie", code)
        assert resp.status == 200
        uid = self._new_user_id(db, "newbie")
        assert db.scalar("SELECT referred_by_user_id FROM user_profiles WHERE user_id=?", uid) == ""

    async def test_referrer_earnings_are_not_changed_by_sign_up(self, db, env):
        """A sign-up alone doesn't credit the referrer with earnings."""
        await _add_member(db, "referrer", code="ABCD2345", earnings=250)
        await self._register(env, "newbie", "ABCD2345")
        assert db.scalar("SELECT referral_earnings_cents FROM user_profiles WHERE user_id='referrer'") == 250
