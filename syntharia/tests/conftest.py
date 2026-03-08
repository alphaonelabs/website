"""
pytest conftest — mocks the Cloudflare ``workers`` Python package so that
handler modules can be imported and tested outside the Workers runtime.
"""

import sys
import json
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Build a lightweight mock of the ``workers`` package before any worker
# module is imported.
# ---------------------------------------------------------------------------


class MockResponse:
    """Minimal stand-in for the Cloudflare Workers ``Response`` class."""

    def __init__(self, body=b"", status=200, headers=None):
        # Normalise body to bytes for consistency in test assertions
        if isinstance(body, str):
            body = body.encode()
        self.body = body
        self.status = status
        self.headers = headers or {}

    @classmethod
    def json(cls, data, status=200):
        body = json.dumps(data).encode()
        return cls(body, status=status, headers={"content-type": "application/json"})

    def _json(self):
        return json.loads(self.body)

    def __repr__(self):
        return f"<MockResponse status={self.status} body={self.body[:80]!r}>"


class MockRequest:
    """Minimal stand-in for the Cloudflare Workers ``Request`` class."""

    def __init__(self, url="http://localhost/", method="GET", body=None):
        self.url = url
        self.method = method
        self._body = body or b""

    async def text(self):
        if isinstance(self._body, bytes):
            return self._body.decode()
        return self._body

    async def json(self):
        return json.loads(await self.text())


class MockWorkersModule(MagicMock):
    Response = MockResponse
    Request = MockRequest

    class WorkerEntrypoint:
        pass


workers_mock = MockWorkersModule()
workers_mock.Response = MockResponse
workers_mock.Request = MockRequest
workers_mock.WorkerEntrypoint = MockWorkersModule.WorkerEntrypoint

sys.modules["workers"] = workers_mock
