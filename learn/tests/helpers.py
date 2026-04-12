"""
Shared test helpers: mock Request, mock Env, mock D1 database.
"""

import base64
import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock


# ---------------------------------------------------------------------------
# Worker module loader
# ---------------------------------------------------------------------------

_WORKER_PATH = Path(__file__).parent.parent / "src" / "worker.py"


def load_worker():
    """Load and return the worker module from the source tree."""
    spec = importlib.util.spec_from_file_location("worker", _WORKER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Mock Request
# ---------------------------------------------------------------------------

class MockRequest:
    """Minimal HTTP request stub."""

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
        return self._body

    def get(self, key, default=None):
        return self.headers.get(key, default)


# ---------------------------------------------------------------------------
# Mock D1 database
# ---------------------------------------------------------------------------

class MockRow:
    """A database row whose columns are accessible as attributes."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def make_stmt(*, first=None, all_results=None):
    """
    Return a mock D1 prepared statement.

    Supports both the ``stmt.bind(*args).first()`` pattern and the direct
    ``stmt.all()`` / ``stmt.first()`` / ``stmt.run()`` pattern (used by some
    handlers that omit the ``.bind()`` call when there are no parameters).
    """
    all_result = MagicMock()
    all_result.results = list(all_results or [])

    # ---- shared bound object (used when .bind() IS called) ----------------
    bound = MagicMock()
    bound.first = AsyncMock(return_value=first)
    bound.run = AsyncMock(return_value=None)
    bound.all = AsyncMock(return_value=all_result)

    # ---- top-level async methods (used when .bind() is NOT called) ---------
    stmt = MagicMock()
    stmt.bind.return_value = bound
    stmt.first = AsyncMock(return_value=first)
    stmt.run = AsyncMock(return_value=None)
    stmt.all = AsyncMock(return_value=all_result)
    return stmt


class MockDB:
    """
    Mock D1 database.

    Pass a list of mock statements that will be returned in order for each
    successive call to ``prepare()``.  If the list is exhausted a default
    no-op statement is returned.
    """

    def __init__(self, stmts=None):
        self._stmts = list(stmts or [])
        self._idx = 0

    def prepare(self, _sql):
        if self._idx < len(self._stmts):
            stmt = self._stmts[self._idx]
        else:
            stmt = make_stmt()
        self._idx += 1
        return stmt


# ---------------------------------------------------------------------------
# Mock Env
# ---------------------------------------------------------------------------

def make_env(db=None, enc_key="test-encryption-key", jwt_secret="test-jwt-secret",
             admin_user="admin", admin_pass="adminpass", admin_url="/admin"):
    """Return a minimal mock Cloudflare Worker environment binding."""
    env = MagicMock()
    env.ENCRYPTION_KEY = enc_key
    env.JWT_SECRET = jwt_secret
    env.ADMIN_BASIC_USER = admin_user
    env.ADMIN_BASIC_PASS = admin_pass
    env.ADMIN_URL = admin_url
    env.DB = db if db is not None else MockDB()
    # Use setattr to avoid Python name-mangling of __STATIC_CONTENT
    # when this function is called from inside a class method.
    sc = MagicMock()
    sc.get = AsyncMock(return_value=None)
    setattr(env, "__STATIC_CONTENT", sc)
    return env


def set_static_content(env, content):
    """
    Configure the mock ``__STATIC_CONTENT`` KV binding to return *content*.

    Always use this helper (never ``env.__STATIC_CONTENT.get = ...``) when
    writing tests that live inside a class – Python's name-mangling would
    otherwise silently mangle the attribute name.
    """
    sc = MagicMock()
    sc.get = AsyncMock(return_value=content)
    setattr(env, "__STATIC_CONTENT", sc)


# ---------------------------------------------------------------------------
# Helper: build a valid Basic-Auth header value
# ---------------------------------------------------------------------------

def basic_auth_header(user: str, password: str) -> str:
    raw = f"{user}:{password}"
    return "Basic " + base64.b64encode(raw.encode()).decode()


# ---------------------------------------------------------------------------
# Helper: build a minimal POST request with a JSON body
# ---------------------------------------------------------------------------

def json_request(path: str, payload: dict, headers=None, method="POST") -> MockRequest:
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    return MockRequest(method=method, url=f"http://localhost{path}", headers=h,
                       body=json.dumps(payload))
