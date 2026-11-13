"""
Tests for device authentication and rate limiting in EarthMind.
"""
import sys
import os
import hashlib
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from services.device_auth import (
    generate_api_key,
    authenticate_device,
    check_rate_limit,
    register_device,
    update_device_last_seen,
    RATE_LIMIT_MAX_REQUESTS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db_result(row_dict):
    """Build a mock D1 result that returns row_dict from .first()."""
    mock_result = MagicMock()
    mock_result.to_py.return_value = row_dict
    return mock_result


def _make_env(first_return=None, run_return=None):
    """Build a mock env.DB."""
    mock_stmt = MagicMock()
    mock_stmt.bind.return_value = mock_stmt
    mock_stmt.first = AsyncMock(return_value=first_return)
    mock_stmt.run = AsyncMock(return_value=run_return)
    mock_stmt.all = AsyncMock(return_value=MagicMock(results=[]))

    mock_db = MagicMock()
    mock_db.prepare.return_value = mock_stmt

    mock_env = MagicMock()
    mock_env.DB = mock_db
    return mock_env, mock_stmt


# ---------------------------------------------------------------------------
# generate_api_key
# ---------------------------------------------------------------------------

class TestGenerateApiKey:
    def test_returns_tuple_of_strings(self):
        raw, hashed = generate_api_key()
        assert isinstance(raw, str)
        assert isinstance(hashed, str)

    def test_hash_is_sha256_hex_digest(self):
        raw, hashed = generate_api_key()
        assert len(hashed) == 64
        assert all(c in "0123456789abcdef" for c in hashed)

    def test_hash_matches_raw(self):
        raw, hashed = generate_api_key()
        expected = hashlib.sha256(raw.encode()).hexdigest()
        assert hashed == expected

    def test_unique_keys(self):
        key1, _ = generate_api_key()
        key2, _ = generate_api_key()
        assert key1 != key2


# ---------------------------------------------------------------------------
# authenticate_device
# ---------------------------------------------------------------------------

class TestAuthenticateDevice:
    def test_valid_key_returns_true(self):
        raw, hashed = generate_api_key()
        row = {"api_key_hash": hashed, "is_active": 1}
        mock_result = _make_db_result(row)
        env, stmt = _make_env(first_return=mock_result)

        result = asyncio.run(authenticate_device(env, "sensor-01", raw))
        assert result is True

    def test_wrong_key_returns_false(self):
        _, hashed = generate_api_key()
        row = {"api_key_hash": hashed, "is_active": 1}
        mock_result = _make_db_result(row)
        env, stmt = _make_env(first_return=mock_result)

        result = asyncio.run(authenticate_device(env, "sensor-01", "wrong-key"))
        assert result is False

    def test_inactive_device_returns_false(self):
        raw, hashed = generate_api_key()
        row = {"api_key_hash": hashed, "is_active": 0}
        mock_result = _make_db_result(row)
        env, stmt = _make_env(first_return=mock_result)

        result = asyncio.run(authenticate_device(env, "sensor-01", raw))
        assert result is False

    def test_nonexistent_device_returns_false(self):
        env, stmt = _make_env(first_return=None)
        result = asyncio.run(authenticate_device(env, "no-device", "any-key"))
        assert result is False


# ---------------------------------------------------------------------------
# check_rate_limit
# ---------------------------------------------------------------------------

class TestCheckRateLimit:
    def test_first_request_is_allowed(self):
        env, stmt = _make_env(first_return=None)
        allowed, info = asyncio.run(check_rate_limit(env, "sensor-01"))
        assert allowed is True
        assert info["count"] == 1

    def test_within_limit_is_allowed(self):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        window_start = now.replace(second=0, microsecond=0).isoformat()
        row = {"window_start": window_start, "request_count": 5}
        mock_result = _make_db_result(row)
        env, stmt = _make_env(first_return=mock_result)

        allowed, info = asyncio.run(check_rate_limit(env, "sensor-01"))
        assert allowed is True

    def test_at_limit_is_rejected(self):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        window_start = now.replace(second=0, microsecond=0).isoformat()
        row = {"window_start": window_start, "request_count": RATE_LIMIT_MAX_REQUESTS}
        mock_result = _make_db_result(row)
        env, stmt = _make_env(first_return=mock_result)

        allowed, info = asyncio.run(check_rate_limit(env, "sensor-01"))
        assert allowed is False
        assert info["count"] == RATE_LIMIT_MAX_REQUESTS

    def test_expired_window_resets(self):
        old_window = "2020-01-01T00:00:00+00:00"
        row = {"window_start": old_window, "request_count": RATE_LIMIT_MAX_REQUESTS}
        mock_result = _make_db_result(row)
        env, stmt = _make_env(first_return=mock_result)

        allowed, info = asyncio.run(check_rate_limit(env, "sensor-01"))
        assert allowed is True
        assert info["count"] == 1


# ---------------------------------------------------------------------------
# register_device (integration-style with mocked DB)
# ---------------------------------------------------------------------------

class TestRegisterDevice:
    def test_returns_api_key(self):
        env, stmt = _make_env()
        result = asyncio.run(register_device(env, "sensor-new", owner_name="Alice"))
        assert "api_key" in result
        assert result["device_id"] == "sensor-new"
        assert "message" in result

    def test_api_key_is_string(self):
        env, stmt = _make_env()
        result = asyncio.run(register_device(env, "sensor-new"))
        assert isinstance(result["api_key"], str)
        assert len(result["api_key"]) > 0
