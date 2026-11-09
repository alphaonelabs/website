"""Tests for how the in-memory per-IP limiter makes room when its key store is full."""

import pytest

from tests.helpers import load_worker, make_env, json_request

worker = load_worker()

MAX_KEYS = 5


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch):
    """Start every test with an empty store and a frozen clock."""
    worker._AUTH_RATE_LIMIT_STATE.clear()
    monkeypatch.setattr(worker.time, "time", lambda: 1_000_000)
    yield
    worker._AUTH_RATE_LIMIT_STATE.clear()


def _env():
    """Env with a tiny key cap so the store fills up quickly."""
    env = make_env()
    env.AUTH_RATE_LIMIT_WINDOW_SECONDS = 60
    env.AUTH_RATE_LIMIT_MAX_ATTEMPTS = 2
    env.AUTH_RATE_LIMIT_MAX_KEYS = MAX_KEYS
    return env


def _hit(env, route, ip):
    """Make one limiter check for this route and IP; return the 429 response or None."""
    req = json_request("/api/x", {}, headers={"CF-Connecting-IP": ip})
    return worker._check_auth_rate_limit(req, env, route)


def _route_keys(route):
    """Keys currently stored for one route."""
    return [k for k in worker._AUTH_RATE_LIMIT_STATE if k.startswith(f"{route}:")]


class TestRateLimitEviction:
    """Eviction never locks visitors out and never frees a blocked visitor first."""

    def test_new_visitor_is_never_locked_out_when_full(self):
        """A full store still admits a brand-new IP and stays within its cap."""
        env = _env()
        for i in range(MAX_KEYS * 3):
            assert _hit(env, "login", f"10.0.0.{i}") is None
        assert len(_route_keys("login")) == MAX_KEYS

    def test_blocked_visitor_stays_blocked_under_ip_flood(self):
        """Cycling through many fresh IPs cannot evict a counter that is blocking someone."""
        env = _env()
        _hit(env, "login", "203.0.113.9")
        _hit(env, "login", "203.0.113.9")
        assert _hit(env, "login", "203.0.113.9") is not None  # now blocked

        for i in range(MAX_KEYS * 10):
            _hit(env, "login", f"10.0.{i // 250}.{i % 250}")

        assert _hit(env, "login", "203.0.113.9") is not None

    def test_one_route_cannot_evict_another(self):
        """Filling the chat store leaves login counters untouched."""
        env = _env()
        _hit(env, "login", "203.0.113.9")
        _hit(env, "login", "203.0.113.9")

        for i in range(MAX_KEYS * 10):
            _hit(env, "chat", f"10.1.{i // 250}.{i % 250}")

        assert worker._AUTH_RATE_LIMIT_STATE["login:203.0.113.9"]["count"] == 2
        assert _hit(env, "login", "203.0.113.9") is not None
        assert len(_route_keys("chat")) == MAX_KEYS

    def test_lowest_count_is_evicted_before_higher_counts(self):
        """Among unblocked counters, the one with the fewest attempts goes first."""
        env = _env()
        env.AUTH_RATE_LIMIT_MAX_ATTEMPTS = 5
        for i in range(MAX_KEYS):
            ip = f"10.2.0.{i}"
            for _ in range(i + 1):  # 10.2.0.0 has 1 attempt, 10.2.0.4 has 5 (blocked at the next one)
                _hit(env, "register", ip)

        _hit(env, "register", "198.51.100.1")

        assert "register:10.2.0.0" not in worker._AUTH_RATE_LIMIT_STATE
        assert all(f"register:10.2.0.{i}" in worker._AUTH_RATE_LIMIT_STATE for i in range(1, MAX_KEYS))

    def test_similar_route_names_do_not_share_a_cap(self):
        """'change_password' keys are not counted as 'confirm_password_change' keys, or vice versa."""
        env = _env()
        for i in range(MAX_KEYS):
            _hit(env, "confirm_password_change", f"10.3.0.{i}")
        for i in range(MAX_KEYS):
            _hit(env, "change_password", f"10.4.0.{i}")
        assert len(_route_keys("confirm_password_change")) == MAX_KEYS
        assert len(_route_keys("change_password")) == MAX_KEYS
