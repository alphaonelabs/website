"""
Pytest configuration: stubs out the Cloudflare Workers SDK so that
src/entry.py can be imported in a plain Python test environment.
"""
import json
import sys
from types import ModuleType


def _make_workers_stub() -> ModuleType:
    """Return a minimal 'workers' module stub."""
    mod = ModuleType("workers")

    class Response:
        """Stub for the Cloudflare Workers Response class."""

        def __init__(self, body="", status=200, headers=None):
            self.body = body
            self.status = status
            self.headers = headers or {}

        def json_body(self) -> dict:
            """Convenience helper used in tests to decode the JSON body."""
            return json.loads(self.body)

    class WorkerEntrypoint:
        """Stub for the Cloudflare Workers WorkerEntrypoint class."""

        async def fetch(self, request):  # pragma: no cover
            raise NotImplementedError("Use the Cloudflare Workers runtime")

    mod.Response = Response
    mod.WorkerEntrypoint = WorkerEntrypoint
    return mod


# Install stub before any test module imports src.entry
if "workers" not in sys.modules:
    sys.modules["workers"] = _make_workers_stub()
