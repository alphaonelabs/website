"""
Pytest configuration: stubs out the Cloudflare Workers SDK so that
src/entry.py can be imported in a plain Python test environment.
"""
import sys
from types import ModuleType
from unittest.mock import MagicMock


def _make_workers_stub() -> ModuleType:
    """Return a minimal 'workers' module stub with WorkerEntrypoint."""
    mod = ModuleType("workers")

    class WorkerEntrypoint:
        """Stub for the Cloudflare Workers SDK WorkerEntrypoint class."""

        async def fetch(self, request):  # pragma: no cover
            raise NotImplementedError("Use the Cloudflare Workers runtime")

    mod.WorkerEntrypoint = WorkerEntrypoint
    return mod


# Install stub before any test module imports src.entry
if "workers" not in sys.modules:
    sys.modules["workers"] = _make_workers_stub()
