"""
Shared test helpers for pmoss unit tests.
"""

import json
from unittest.mock import AsyncMock, MagicMock


class MockRequest:
    """Mock Cloudflare Worker HTTP Request."""

    def __init__(self, method="GET", url="http://localhost/", headers=None, body=None):
        self.method = method
        self.url = url
        self.headers = dict(headers or {})
        self._body = body

    async def text(self):
        if self._body is None:
            return ""
        if isinstance(self._body, bytes):
            return self._body.decode("utf-8")
        if isinstance(self._body, (dict, list)):
            return json.dumps(self._body)
        return str(self._body)

    def clone(self):
        return MockRequest(
            method=self.method,
            url=self.url,
            headers=dict(self.headers),
            body=self._body,
        )


def make_stmt(*, first=None, all_results=None):
    """
    Return a mock D1 prepared statement.
    D1 .all() returns {'results': [...]}.
    D1 .first() returns a dict or None.
    """
    if all_results is None:
        all_val = {"results": []}
    elif isinstance(all_results, dict) and "results" in all_results:
        all_val = all_results
    else:
        all_val = {"results": list(all_results)}

    bound = MagicMock()
    bound.first = AsyncMock(return_value=first)
    bound.all = AsyncMock(return_value=all_val)
    bound.run = AsyncMock(return_value={"success": True})

    stmt = MagicMock()
    stmt.bind = MagicMock(return_value=bound)
    stmt.first = AsyncMock(return_value=first)
    stmt.all = AsyncMock(return_value=all_val)
    stmt.run = AsyncMock(return_value={"success": True})
    return stmt


class MockDB:
    """
    Mock D1 Database supporting sequential prepared statements or fallback.
    """

    def __init__(self, stmts=None):
        self._stmts = list(stmts or [])
        self._idx = 0
        self.queries = []

    def prepare(self, sql):
        self.queries.append(sql)
        if self._idx < len(self._stmts):
            stmt = self._stmts[self._idx]
        else:
            stmt = make_stmt()
        self._idx += 1
        return stmt


class MockEnv:
    """Mock environment bindings for Cloudflare Workers."""

    def __init__(
        self,
        db=None,
        client_id="mock_client_id",
        client_secret="mock_client_secret",
        redirect_uri="https://example.com/auth/callback",
        webhook_secret="mock_webhook_secret",
    ):
        self.DB = db if db is not None else MockDB()
        self.GITHUB_CLIENT_ID = client_id
        self.GITHUB_CLIENT_SECRET = client_secret
        self.GITHUB_REDIRECT_URI = redirect_uri
        self.GITHUB_WEBHOOK_SECRET = webhook_secret
