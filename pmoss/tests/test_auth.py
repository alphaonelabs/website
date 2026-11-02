from types import SimpleNamespace

from auth import get_auth_token


def test_returns_bearer_token():
    request = SimpleNamespace(headers={"Authorization": "Bearer github-token"})
    assert get_auth_token(request) == "github-token"


def test_missing_authorization_header_returns_none():
    request = SimpleNamespace(headers={})
    assert get_auth_token(request) is None


def test_malformed_authorization_header_returns_none():
    request = SimpleNamespace(headers={"Authorization": "Basic github-token"})
    assert get_auth_token(request) is None


def test_lowercase_bearer_scheme_is_rejected():
    request = SimpleNamespace(headers={"Authorization": "bearer github-token"})
    assert get_auth_token(request) is None


def test_bearer_without_token_returns_none():
    request = SimpleNamespace(headers={"Authorization": "Bearer "})
    assert get_auth_token(request) is None
