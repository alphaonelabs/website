"""
Shared test helpers: mock Request, mock Env, mock D1 database.
"""

import base64
import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
import re
from types import SimpleNamespace


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
    env.AUTH_RATE_LIMIT_WINDOW_SECONDS = 60
    env.AUTH_RATE_LIMIT_MAX_ATTEMPTS = 5
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
    h = {
        "Content-Type": "application/json",
        "CF-Connecting-IP": "127.0.0.1",
    }
    if headers:
        h.update(headers)
    return MockRequest(method=method, url=f"http://localhost{path}", headers=h,
                       body=json.dumps(payload))


# ---------------------------------------------------------------------------
# Helper: dynamically count statements executed by init_db
# ---------------------------------------------------------------------------

_INIT_DB_STMT_COUNT = None


async def get_init_db_statement_count(worker_mod) -> int:
    """Return the total number of SQL statements prepared during worker.init_db().

    Cached across test invocations so schema evolution never desyncs MockDB
    statement sequences in retry-after-missing-table tests.
    """
    global _INIT_DB_STMT_COUNT
    if _INIT_DB_STMT_COUNT is None:
        count = 0

        class _CounterDB:
            def prepare(self, _sql):
                nonlocal count
                count += 1
                return make_stmt()

        env = make_env(db=_CounterDB())
        await worker_mod.init_db(env)
        _INIT_DB_STMT_COUNT = count
    return _INIT_DB_STMT_COUNT


async def make_init_db_stmts(worker_mod):
    """Return a list of dummy statements sized to match worker.init_db()."""
    cnt = await get_init_db_statement_count(worker_mod)
    return [make_stmt() for _ in range(cnt)]

# ---------------------------------------------------------------------------
# Strict D1 fake: rejects what real D1 rejects (None binds, wrong arg count)
# ---------------------------------------------------------------------------

class _StrictStmt:
    def __init__(self, db, sql):
        self.db = db
        self.sql = sql
        self.args = ()

    def bind(self, *args):
        for i, value in enumerate(args):
            if value is None:
                raise Exception(
                    "D1_TYPE_ERROR: Type 'undefined' not supported for value 'undefined'"
                    f" (bind argument {i + 1} of: {self.sql})"
                )
        placeholders = self.sql.count("?")
        if placeholders != len(args):
            raise Exception(
                f"D1_ERROR: {placeholders} placeholders but {len(args)} values bound: {self.sql}"
            )
        self.args = args
        return self

    async def first(self):
        return self.db._first(self.sql, self.args)

    async def all(self):
        return SimpleNamespace(results=list(self.db._all(self.sql, self.args)))

    async def run(self):
        if self.db.run_error:
            raise self.db.run_error
        self.db.writes.append((self.sql, self.args))
        return None
    
    async def run(self):
        if self.db.run_error_once:
            exc, self.db.run_error_once = self.db.run_error_once, None
            raise exc
        if self.db.run_error:
            raise self.db.run_error
        self.db.writes.append((self.sql, self.args))
        return None


class StrictD1:
    """
    D1 stand-in. Reads are answered by the `first(sql, args)` / `all_(sql, args)`
    callables; writes are recorded in `.writes` (from .run()) and `.batches`
    (from .batch()).
    """

    def __init__(self, first=None, all_=None, run_error=None, batch_error=None, run_error_once=None):
        self._first = first or (lambda sql, args: None)
        self._all = all_ or (lambda sql, args: [])
        self.run_error = run_error
        self.batch_error = batch_error
        self.run_error_once = run_error_once
        self.writes = []
        self.batches = []

    def prepare(self, sql):
        return _StrictStmt(self, sql)

    async def batch(self, stmts):
        if self.batch_error:
            raise self.batch_error
        self.batches.append([(s.sql, s.args) for s in stmts])


def row_as_dict(sql, args):
    """Map an INSERT's columns to the values it saves (NULL literal -> None)."""
    cols_m = re.search(r"\(([^)]*)\)\s*VALUES", sql)
    vals_m = re.search(r"VALUES\s*\(([^)]*)\)", sql)
    if not cols_m or not vals_m:
        raise ValueError(f"Not a simple INSERT ... VALUES statement: {sql}")
    cols = cols_m.group(1).split(",")
    vals = vals_m.group(1).split(",")
    it = iter(args)
    return {
        col.strip(): (None if val.strip().upper() == "NULL" else next(it))
        for col, val in zip(cols, vals, strict=True)
    }