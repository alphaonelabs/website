"""
Alpha One Labs – Cloudflare Python Worker (Activities Model)
=========================================================
API Routes
  POST /api/init              – initialise DB schema
  POST /api/seed              – seed sample data
  POST /api/register          – register a new user
  POST /api/login             – authenticate -> signed token
  GET  /api/activities        – list activities (?type=&format=&q=&tag=)
  POST /api/activities        – create activity              [host]
  GET  /api/activities/:id    – activity + sessions + state
  POST /api/join              – join an activity
  GET  /api/dashboard         – personal dashboard
  POST /api/sessions          – add a session to activity    [host]
  GET  /api/tags              – list all tags
  POST /api/activity-tags     – add tags to an activity      [host]

Security model
  * ALL user PII (username, email, display name, role) is encrypted with
    AES-256-GCM (via js.crypto.subtle) before storage.
  * HMAC-SHA256 blind indexes (username_hash, email_hash) allow O(1) row
    lookups without ever storing plaintext PII in an indexed column.
  * Activity descriptions and session locations/descriptions are encrypted.
  * Passwords: PBKDF2-SHA256, per-user derived salt (username + global pepper).
  * Auth tokens: HMAC-SHA256 signed, stateless (JWT-lite).
  AES-256-GCM authenticated encryption via js.crypto.subtle.
    96-bit random IV generated per encryption call.
    128-bit GCM auth tag provides tamper detection.
    Backward compatible: existing XOR-encrypted data decrypted transparently.
    Legacy _encrypt_xor/_decrypt_xor retained for reading old stored data.

Static HTML pages (public/) are served via Workers Sites (KV binding).
"""

import base64
import hashlib
import hmac as _hmac
import json
import os
import re
import traceback
from types import SimpleNamespace
from typing import Any, Dict
from urllib.parse import urlparse, parse_qs

from workers import Response, DurableObject

import js
from pyodide.ffi import to_js
from js import WebSocketPair, WebSocketRequestResponsePair
import uuid

_SENTRY_INITIALIZED = False
_SENTRY_DSN: str = ""


def init_sentry(env):
    """Cache the Sentry DSN once per worker isolate."""
    global _SENTRY_INITIALIZED, _SENTRY_DSN
    if _SENTRY_INITIALIZED:
        return
    _SENTRY_INITIALIZED = True
    _SENTRY_DSN = getattr(env, "SENTRY_DSN", "") or ""

def _redact_url(raw_url: str) -> str:
    """Remove secrets from URLs before logging or sending to Sentry."""
    try:
        parsed = urlparse(raw_url)
        query = re.sub(r"([?&](?:token|access_token)=)[^&]+", r"\1[redacted]", "?" + parsed.query)
        safe_query = query[1:] if parsed.query else ""
        return parsed._replace(query=safe_query).geturl()
    except Exception:
        return "[redacted-url]"

async def _post_to_sentry(exc: Exception, dsn: str, where: str, req=None):
    """Send an exception to Sentry via the HTTP Store API using js.fetch."""
    try:
        parsed     = urlparse(dsn)
        public_key = parsed.username
        host       = parsed.hostname
        project_id = parsed.path.strip("/")
        endpoint   = f"https://{host}/api/{project_id}/store/"

        tb_frames = []
        if exc.__traceback__:
            for fi in traceback.extract_tb(exc.__traceback__):
                tb_frames.append({
                    "filename":     fi.filename,
                    "function":     fi.name,
                    "lineno":       fi.lineno,
                    "context_line": fi.line or "",
                })

        event: Dict[str, Any] = {
            "event_id":  os.urandom(16).hex(),
            "level":     "error",
            "logger":    where or "worker",
            "tags":      {"where": where or "unknown"},
            "exception": {
                "values": [{
                    "type":       type(exc).__name__,
                    "value":      str(exc),
                    "stacktrace": {"frames": tb_frames},
                }]
            },
        }
        if req:
            event["request"] = {"url": _redact_url(req.url), "method": req.method}

        auth = (
            f"Sentry sentry_version=7, sentry_key={public_key},"
            f" sentry_client=cf-worker/1.0"
        )
        options = to_js(
            {
                "method":  "POST",
                "headers": {"Content-Type": "application/json", "X-Sentry-Auth": auth},
                "body":    json.dumps(event),
            },
            dict_converter=js.Object.fromEntries,
        )
        await js.fetch(endpoint, options)
    except Exception as post_exc:
        print(json.dumps({"level": "warn", "where": "sentry_http_post", "error": str(post_exc)}))


async def capture_exception(exc: Exception, req=None, _env=None, where: str = ""):
    """Best-effort exception logging via print + Sentry HTTP Store API."""
    try:
        payload: Dict[str, Any] = {
            "level":      "error",
            "where":      where or "unknown",
            "error_type": type(exc).__name__,
            "error":      str(exc),
            "traceback":  "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        }
        if req:
            payload["request"] = {
                "method": req.method,
                "url":    _redact_url(req.url),
                "path":   urlparse(req.url).path,
            }
        print(json.dumps(payload))

        dsn = _SENTRY_DSN or (getattr(_env, "SENTRY_DSN", "") if _env else "")
        if dsn:
            await _post_to_sentry(exc, dsn, where, req)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------

def new_id() -> str:
    """Generate a random UUID v4 using os.urandom."""
    b = bytearray(os.urandom(16))
    b[6] = (b[6] & 0x0F) | 0x40   # version 4
    b[8] = (b[8] & 0x3F) | 0x80   # RFC 4122 variant
    h = b.hex()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


# ---------------------------------------------------------------------------
# Encryption helpers - AES-256-GCM via Web Crypto API (js.crypto.subtle)
# ---------------------------------------------------------------------------

def _derive_key(secret: str) -> bytes:
    """Derive a 32-byte key from an arbitrary secret string via SHA-256."""
    return hashlib.sha256(secret.encode("utf-8")).digest()


def _derive_aes_key_bytes(secret: str) -> bytes:
    """Derive a 32-byte AES-256 key via PBKDF2-SHA256 with a fixed domain salt.

    Note: 100k iterations are intentional for key hardening. For high-throughput
    paths, callers can cache the derived key bytes for the duration of a request.
    """
    salt = hashlib.sha256(b"aol-edu-aes-salt-v1" + secret.encode()).digest()
    return hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, 100_000)


async def _import_aes_key(key_bytes: bytes) -> object:
    """Import raw bytes as a Web Crypto AES-GCM CryptoKey."""
    key_buf = to_js(key_bytes, create_pyproxies=False)
    algo    = to_js({"name": "AES-GCM"}, dict_converter=js.Object.fromEntries)
    usages  = to_js(["encrypt", "decrypt"])
    return await js.crypto.subtle.importKey("raw", key_buf, algo, False, usages)


async def encrypt_aes(plaintext: str, secret: str) -> str:
    """
    AES-256-GCM encryption using js.crypto.subtle (Web Crypto API).
    Returns "v1:" + base64(iv || ciphertext+tag).
    Raises RuntimeError on encryption failure — no silent XOR fallback.
    """
    if not plaintext:
        return ""
    try:
        key_bytes  = _derive_aes_key_bytes(secret)
        crypto_key = await _import_aes_key(key_bytes)

        iv_array   = js.Uint8Array.new(12)
        js.crypto.getRandomValues(iv_array)
        iv         = bytes(iv_array)

        # Pass algo as a plain dict; Web Crypto accepts both JS objects and plain dicts
        algo       = to_js({"name": "AES-GCM", "iv": iv_array}, dict_converter=js.Object.fromEntries)
        data       = to_js(plaintext.encode("utf-8"), create_pyproxies=False)
        ct_buf     = await js.crypto.subtle.encrypt(algo, crypto_key, data)
        ct         = bytes(js.Uint8Array.new(ct_buf))
        return "v1:" + base64.b64encode(iv + ct).decode("ascii")
    except Exception as exc:
        await capture_exception(exc, where="encrypt_aes")
        raise RuntimeError(f"AES-256-GCM encryption failed: {exc}") from exc


async def decrypt_aes(ciphertext: str, secret: str) -> str:
    """
    AES-256-GCM decryption. Handles both v1 (AES-GCM) and legacy (XOR) ciphertext.
    """
    if not ciphertext:
        return ""
    if not ciphertext.startswith("v1:"):
        return _decrypt_xor(ciphertext, secret)
    try:
        raw        = base64.b64decode(ciphertext[3:])
        iv, ct     = raw[:12], raw[12:]
    except Exception as exc:
        await capture_exception(exc, where="decrypt_aes.decode")
        return "[decryption error]"
    try:
        key_bytes  = _derive_aes_key_bytes(secret)
        crypto_key = await _import_aes_key(key_bytes)
        iv_array   = to_js(iv, create_pyproxies=False)
        algo       = to_js({"name": "AES-GCM", "iv": iv_array}, dict_converter=js.Object.fromEntries)
        data       = to_js(ct, create_pyproxies=False)
        pt_buf     = await js.crypto.subtle.decrypt(algo, crypto_key, data)
        return bytes(js.Uint8Array.new(pt_buf)).decode("utf-8")
    except Exception as exc:
        await capture_exception(exc, where="decrypt_aes.auth")
        return "[decryption error]"


def _encrypt_xor(plaintext: str, secret: str) -> str:
    """Legacy XOR stream cipher — kept for backward compatibility only."""
    if not plaintext:
        return ""
    key  = _derive_key(secret)
    data = plaintext.encode("utf-8")
    ks   = (key * (len(data) // len(key) + 1))[: len(data)]
    return base64.b64encode(bytes(a ^ b for a, b in zip(data, ks))).decode("ascii")


def _decrypt_xor(ciphertext: str, secret: str) -> str:
    """Legacy XOR stream cipher decryption — kept for backward compatibility."""
    if not ciphertext:
        return ""
    try:
        key = _derive_key(secret)
        raw = base64.b64decode(ciphertext)
        ks  = (key * (len(raw) // len(key) + 1))[: len(raw)]
        return bytes(a ^ b for a, b in zip(raw, ks)).decode("utf-8")
    except Exception:
        return "[decryption error]"


# Synchronous shims — raise errors to force migration to async variants.
def encrypt(plaintext: str, secret: str) -> str:
    """Deprecated sync shim — raises to force migration to await encrypt_aes()."""
    raise RuntimeError("encrypt() is deprecated — use await encrypt_aes() instead")


def decrypt(ciphertext: str, secret: str) -> str:
    """Deprecated sync shim — raises to force migration to await decrypt_aes()."""
    raise RuntimeError("decrypt() is deprecated — use await decrypt_aes() instead")

def blind_index(value: str, secret: str) -> str:
    """
    HMAC-SHA256 deterministic hash of value used as a blind index.

    Allows finding a row by plaintext value without decrypting every row.
    The value is lower-cased before hashing so lookups are case-insensitive.
    """
    return _hmac.new(
        secret.encode("utf-8"), value.lower().encode("utf-8"), hashlib.sha256
    ).hexdigest()


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

# ⚠️  For production, derive the pepper from a secret stored via
#     `wrangler secret put PEPPER` and pass it to _user_salt() at runtime.
#     Rotating the pepper requires re-hashing all stored passwords.
_PEPPER    = b"edu-platform-cf-pepper-2024"
_PBKDF2_IT = 100_000


def _user_salt(username: str) -> bytes:
    """Per-user PBKDF2 salt = SHA-256(pepper || username)."""
    return hashlib.sha256(_PEPPER + username.encode("utf-8")).digest()


def hash_password(password: str, username: str) -> str:
    """PBKDF2-SHA256 with per-user derived salt."""
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), _user_salt(username), _PBKDF2_IT
    )
    return base64.b64encode(dk).decode("ascii")


def verify_password(password: str, stored: str, username: str) -> bool:
    return hash_password(password, username) == stored


# ---------------------------------------------------------------------------
# Auth tokens (HMAC-SHA256 signed, stateless JWT-lite)
# ---------------------------------------------------------------------------

def create_token(uid: str, username: str, role: str, secret: str) -> str:
    payload = base64.b64encode(
        json.dumps({"id": uid, "username": username, "role": role}).encode()
    ).decode("ascii")
    sig = _hmac.new(
        secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return f"{payload}.{sig}"


def verify_token(raw: str, secret: str):
    """Return decoded payload dict or None if invalid/missing."""
    if not raw:
        return None
    try:
        token = raw.removeprefix("Bearer ").strip()
        dot   = token.rfind(".")
        if dot == -1:
            return None
        p, sig = token[:dot], token[dot + 1:]
        exp = _hmac.new(
            secret.encode("utf-8"), p.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        if not _hmac.compare_digest(sig, exp):
            return None
        padding = (4 - len(p) % 4) % 4
        return json.loads(base64.b64decode(p + "=" * padding).decode("utf-8"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

_CORS = {
    "Access-Control-Allow-Origin":  "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
}


def json_resp(data, status: int = 200):
    return Response(
        json.dumps(data),
        status=status,
        headers={"Content-Type": "application/json", **_CORS},
    )


def ok(data=None, msg: str = "OK"):
    body = {"success": True, "message": msg}
    if data is not None:
        body["data"] = data
    return json_resp(body, 200)


def err(msg: str, status: int = 400):
    return json_resp({"error": msg}, status)


async def parse_json_object(req):
    """Parse request JSON and ensure payload is an object/dict."""
    try:
        text = await req.text()
        body = json.loads(text)
    except Exception:
        return None, err("Invalid JSON body")

    if not isinstance(body, dict):
        return None, err("JSON body must be an object", 400)

    return body, None


def _clean_path(value: str, default: str = "/admin") -> str:
    """Normalize an env-provided path into a safe absolute URL path."""
    raw = (value or "").strip()
    if not raw:
        return default
    parsed = urlparse(raw)
    path = (parsed.path or raw).strip()
    if not path.startswith("/"):
        path = "/" + path
    path = re.sub(r"/+", "/", path)
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path or default


def _unauthorized_basic(realm: str = "Alpha One Labs Admin"):
    return Response(
        "Authentication required",
        status=401,
        headers={"WWW-Authenticate": f'Basic realm="{realm}"', **_CORS},
    )


def _is_basic_auth_valid(req, env) -> bool:
    username = (getattr(env, "ADMIN_BASIC_USER", "") or "").strip()
    password = (getattr(env, "ADMIN_BASIC_PASS", "") or "").strip()
    if not username or not password:
        return False

    auth = req.headers.get("Authorization") or ""
    if not auth.lower().startswith("basic "):
        return False

    try:
        raw = auth.split(" ", 1)[1].strip()
        decoded = base64.b64decode(raw).decode("utf-8")
        user, pwd = decoded.split(":", 1)
    except Exception:
        return False

    return _hmac.compare_digest(user, username) and _hmac.compare_digest(pwd, password)


# ---------------------------------------------------------------------------
# DDL - full schema (mirrors schema.sql)
# ---------------------------------------------------------------------------

_DDL = [
    # Users - all PII encrypted; HMAC blind indexes for O(1) lookups
    """CREATE TABLE IF NOT EXISTS users (
        id            TEXT PRIMARY KEY,
        username_hash TEXT NOT NULL UNIQUE,
        email_hash    TEXT NOT NULL UNIQUE,
        name          TEXT NOT NULL,
        username      TEXT NOT NULL,
        email         TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        role          TEXT NOT NULL,
        created_at    TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    # Activities
    """CREATE TABLE IF NOT EXISTS activities (
        id            TEXT PRIMARY KEY,
        title         TEXT NOT NULL,
        description   TEXT,
        type          TEXT NOT NULL DEFAULT 'course',
        format        TEXT NOT NULL DEFAULT 'self_paced',
        schedule_type TEXT NOT NULL DEFAULT 'ongoing',
        host_id       TEXT NOT NULL,
        created_at    TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (host_id) REFERENCES users(id)
    )""",
    # Sessions
    """CREATE TABLE IF NOT EXISTS sessions (
        id          TEXT PRIMARY KEY,
        activity_id TEXT NOT NULL,
        title       TEXT,
        description TEXT,
        start_time  TEXT,
        end_time    TEXT,
        location    TEXT,
        created_at  TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (activity_id) REFERENCES activities(id)
    )""",
    # Enrollments
    """CREATE TABLE IF NOT EXISTS enrollments (
        id          TEXT PRIMARY KEY,
        activity_id TEXT NOT NULL,
        user_id     TEXT NOT NULL,
        role        TEXT NOT NULL DEFAULT 'participant',
        status      TEXT NOT NULL DEFAULT 'active',
        created_at  TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE (activity_id, user_id),
        FOREIGN KEY (activity_id) REFERENCES activities(id),
        FOREIGN KEY (user_id)     REFERENCES users(id)
    )""",
    # Session attendance
    """CREATE TABLE IF NOT EXISTS session_attendance (
        id         TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        user_id    TEXT NOT NULL,
        status     TEXT NOT NULL DEFAULT 'registered',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE (session_id, user_id),
        FOREIGN KEY (session_id) REFERENCES sessions(id),
        FOREIGN KEY (user_id)    REFERENCES users(id)
    )""",
    # Tags
    """CREATE TABLE IF NOT EXISTS tags (
        id   TEXT PRIMARY KEY,
        name TEXT UNIQUE NOT NULL
    )""",
    # Activity-tag junction
    """CREATE TABLE IF NOT EXISTS activity_tags (
        activity_id TEXT NOT NULL,
        tag_id      TEXT NOT NULL,
        PRIMARY KEY (activity_id, tag_id),
        FOREIGN KEY (activity_id) REFERENCES activities(id),
        FOREIGN KEY (tag_id)      REFERENCES tags(id)
    )""",
    # Indexes
    "CREATE INDEX IF NOT EXISTS idx_activities_host      ON activities(host_id)",
    "CREATE INDEX IF NOT EXISTS idx_enrollments_activity ON enrollments(activity_id)",
    "CREATE INDEX IF NOT EXISTS idx_enrollments_user     ON enrollments(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_sessions_activity    ON sessions(activity_id)",
    "CREATE INDEX IF NOT EXISTS idx_sa_session           ON session_attendance(session_id)",
    "CREATE INDEX IF NOT EXISTS idx_sa_user              ON session_attendance(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_at_activity          ON activity_tags(activity_id)",
]


async def init_db(env):
    for sql in _DDL:
        await env.DB.prepare(sql).run()


_NO_SUCH_TABLE_RE = re.compile(r"\bno such table\b", re.IGNORECASE)


def _is_no_such_table_error(exc: Exception) -> bool:
    """Return True when an exception chain indicates a SQLite/D1 missing-table error."""
    if _NO_SUCH_TABLE_RE.search(str(exc) or ""):
        return True
    cause = getattr(exc, "__cause__", None)
    return bool(cause and _NO_SUCH_TABLE_RE.search(str(cause) or ""))


def _empty_d1_result():
    """Return a minimal D1-style result object with an empty `results` collection."""
    return SimpleNamespace(results=[])


# ---------------------------------------------------------------------------
# Sample-data seeding
# ---------------------------------------------------------------------------

async def seed_db(env, enc_key: str):
    # ---- users ---------------------------------------------------------------
    seed_users = [
        ("alice",   "alice@example.com",   "password123", "host",   "Alice Chen"),
        ("bob",     "bob@example.com",     "password123", "host",   "Bob Martinez"),
        ("charlie", "charlie@example.com", "password123", "member", "Charlie Kim"),
        ("diana",   "diana@example.com",   "password123", "member", "Diana Patel"),
    ]
    uid_map = {}
    for uname, email, pw, role, display in seed_users:
        uid = f"usr-{uname}"
        uid_map[uname] = uid
        try:
            await env.DB.prepare(
                "INSERT INTO users "
                "(id,username_hash,email_hash,name,username,email,password_hash,role)"
                " VALUES (?,?,?,?,?,?,?,?)"
            ).bind(
                uid,
                blind_index(uname, enc_key),
                blind_index(email, enc_key),
                await encrypt_aes(display,  enc_key),
                await encrypt_aes(uname,    enc_key),
                await encrypt_aes(email,    enc_key),
                hash_password(pw, uname),
                await encrypt_aes(role,     enc_key),
            ).run()
        except Exception:
            pass

    aid = uid_map["alice"]
    bid = uid_map["bob"]
    cid = uid_map["charlie"]
    did = uid_map["diana"]

    tag_rows = [
        ("tag-python", "Python"),
        ("tag-js",     "JavaScript"),
        ("tag-data",   "Data Science"),
        ("tag-ml",     "Machine Learning"),
        ("tag-webdev", "Web Development"),
        ("tag-db",     "Databases"),
        ("tag-cloud",  "Cloud"),
    ]
    for tid, tname in tag_rows:
        try:
            await env.DB.prepare(
                "INSERT INTO tags (id,name) VALUES (?,?)"
            ).bind(tid, tname).run()
        except Exception:
            pass

    act_rows = [
        (
            "act-py-begin", "Python for Beginners",
            "Learn Python programming from scratch. Master variables, loops, "
            "functions, and object-oriented design in this hands-on course.",
            "course", "self_paced", "ongoing", aid,
            ["tag-python"],
        ),
        (
            "act-js-meetup", "JavaScript Developers Meetup",
            "Monthly meetup for JavaScript enthusiasts. Share projects, "
            "discuss new frameworks, and network with fellow devs.",
            "meetup", "live", "recurring", bid,
            ["tag-js", "tag-webdev"],
        ),
        (
            "act-ds-workshop", "Data Science Workshop",
            "Hands-on workshop covering data wrangling with pandas, "
            "visualisation with matplotlib, and intro to machine learning.",
            "workshop", "live", "multi_session", aid,
            ["tag-data", "tag-python"],
        ),
        (
            "act-ml-study", "Machine Learning Study Group",
            "Collaborative study group working through ML concepts, "
            "reading papers, and implementing algorithms together.",
            "course", "hybrid", "recurring", bid,
            ["tag-ml", "tag-python"],
        ),
        (
            "act-webdev", "Web Dev Fundamentals",
            "Build modern responsive websites with HTML5, CSS3, and JavaScript. "
            "Covers Flexbox, Grid, fetch API, and accessible design.",
            "course", "self_paced", "ongoing", aid,
            ["tag-webdev", "tag-js"],
        ),
        (
            "act-db-design", "Database Design & SQL",
            "Design normalised relational schemas, write complex SQL queries, "
            "use indexes for speed, and understand transactions.",
            "workshop", "live", "one_time", bid,
            ["tag-db"],
        ),
    ]
    for act_id, title, desc, atype, fmt, sched, host_id, tags in act_rows:
        try:
            await env.DB.prepare(
                "INSERT INTO activities "
                "(id,title,description,type,format,schedule_type,host_id)"
                " VALUES (?,?,?,?,?,?,?)"
            ).bind(
                act_id, title, await encrypt_aes(desc, enc_key),
                atype, fmt, sched, host_id
            ).run()
        except Exception:
            pass
        for tag_id in tags:
            try:
                await env.DB.prepare(
                    "INSERT OR IGNORE INTO activity_tags (activity_id,tag_id)"
                    " VALUES (?,?)"
                ).bind(act_id, tag_id).run()
            except Exception:
                pass

    ses_rows = [
        ("ses-js-1", "act-js-meetup",
         "April Meetup", "Q1 retro and React 19 deep-dive",
         "2024-04-15 18:00", "2024-04-15 21:00", "Tech Hub, 123 Main St, SF"),
        ("ses-js-2", "act-js-meetup",
         "May Meetup", "TypeScript 5.4 and what's new in Node 22",
         "2024-05-20 18:00", "2024-05-20 21:00", "Tech Hub, 123 Main St, SF"),
        ("ses-ds-1", "act-ds-workshop",
         "Session 1 - Data Wrangling",
         "Introduction to pandas DataFrames and data cleaning",
         "2024-06-01 10:00", "2024-06-01 14:00", "Online via Zoom"),
        ("ses-ds-2", "act-ds-workshop",
         "Session 2 - Visualisation",
         "matplotlib, seaborn, and plotly for data storytelling",
         "2024-06-08 10:00", "2024-06-08 14:00", "Online via Zoom"),
        ("ses-ds-3", "act-ds-workshop",
         "Session 3 - Intro to ML",
         "scikit-learn: regression, classification, evaluation",
         "2024-06-15 10:00", "2024-06-15 14:00", "Online via Zoom"),
    ]
    for sid, act_id, title, desc, start, end, loc in ses_rows:
        try:
            await env.DB.prepare(
                "INSERT INTO sessions "
                "(id,activity_id,title,description,start_time,end_time,location)"
                " VALUES (?,?,?,?,?,?,?)"
            ).bind(
                sid, act_id, title,
                await encrypt_aes(desc, enc_key),
                start, end,
                await encrypt_aes(loc, enc_key),
            ).run()
        except Exception:
            pass

    enr_rows = [
        ("enr-c-py",     "act-py-begin",    cid, "participant"),
        ("enr-c-js",     "act-js-meetup",   cid, "participant"),
        ("enr-c-ds",     "act-ds-workshop", cid, "participant"),
        ("enr-d-py",     "act-py-begin",    did, "participant"),
        ("enr-d-webdev", "act-webdev",      did, "participant"),
        ("enr-b-py",     "act-py-begin",    bid, "instructor"),
    ]
    for eid, act_id, uid, role in enr_rows:
        try:
            await env.DB.prepare(
                "INSERT OR IGNORE INTO enrollments (id,activity_id,user_id,role)"
                " VALUES (?,?,?,?)"
            ).bind(eid, act_id, uid, role).run()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# API handlers
# ---------------------------------------------------------------------------

async def api_register(req, env):
    body, bad_resp = await parse_json_object(req)
    if bad_resp:
        return bad_resp

    username = (body.get("username") or "").strip()
    email    = (body.get("email")    or "").strip()
    password = (body.get("password") or "")
    name     = (body.get("name")     or username).strip()

    if not username or not email or not password:
        return err("username, email, and password are required")
    if len(password) < 8:
        return err("Password must be at least 8 characters")

    role = "member"

    enc = env.ENCRYPTION_KEY
    uid = new_id()
    try:
        await env.DB.prepare(
            "INSERT INTO users "
            "(id,username_hash,email_hash,name,username,email,password_hash,role)"
            " VALUES (?,?,?,?,?,?,?,?)"
        ).bind(
            uid,
            blind_index(username, enc),
            blind_index(email,    enc),
            await encrypt_aes(name,     enc),
            await encrypt_aes(username, enc),
            await encrypt_aes(email,    enc),
            hash_password(password, username),
            await encrypt_aes(role, enc),
        ).run()
    except Exception as e:
        if "UNIQUE" in str(e):
            return err("Username or email already registered", 409)
        await capture_exception(e, req, env, "api_register.insert_user")
        return err("Registration failed — please try again", 500)

    token = create_token(uid, username, role, env.JWT_SECRET)
    return ok(
        {"token": token,
         "user": {"id": uid, "username": username, "name": name, "role": role}},
        "Registration successful",
    )


async def api_login(req, env):
    body, bad_resp = await parse_json_object(req)
    if bad_resp:
        return bad_resp

    username = (body.get("username") or "").strip()
    password = (body.get("password") or "")

    if not username or not password:
        return err("username and password are required")

    enc    = env.ENCRYPTION_KEY
    u_hash = blind_index(username, enc)
    row    = await env.DB.prepare(
        "SELECT id,password_hash,role,name,username FROM users WHERE username_hash=?"
    ).bind(u_hash).first()

    if not row:
        return err("Invalid username or password", 401)

    password_hash = row.password_hash
    user_id = row.id
    role_enc = row.role
    name_enc = row.name
    username_enc = row.username
    stored_username = await decrypt_aes(username_enc, enc)
    if not stored_username or stored_username == "[decryption error]":
        return err("Invalid username or password", 401)

    if not verify_password(password, password_hash, stored_username):
        return err("Invalid username or password", 401)

    real_role = await decrypt_aes(role_enc, enc)
    real_name = await decrypt_aes(name_enc, enc)
    if not real_role or real_role == "[decryption error]":
        return err("Account data corrupted — please contact support", 500)
    token     = create_token(user_id, stored_username, real_role, env.JWT_SECRET)
    return ok(
        {"token": token,
         "user": {"id": user_id, "username": stored_username,
                  "name": real_name, "role": real_role}},
        "Login successful",
    )


async def api_list_activities(req, env):
    parsed = urlparse(req.url)
    params = parse_qs(parsed.query)
    atype  = (params.get("type")   or [None])[0]
    fmt    = (params.get("format") or [None])[0]
    search = (params.get("q")      or [None])[0]
    tag    = (params.get("tag")    or [None])[0]
    enc    = env.ENCRYPTION_KEY

    base_q = (
        "SELECT a.id,a.title,a.description,a.type,a.format,a.schedule_type,"
        "a.created_at,u.name AS host_name_enc,"
        "(SELECT COUNT(*) FROM enrollments WHERE activity_id=a.id AND status='active')"
        " AS participant_count,"
        "(SELECT COUNT(*) FROM sessions WHERE activity_id=a.id) AS session_count"
        " FROM activities a JOIN users u ON a.host_id=u.id"
    )

    async def fetch_activities():
        if tag:
            tag_row = await env.DB.prepare(
                "SELECT id FROM tags WHERE name=?"
            ).bind(tag).first()
            if not tag_row:
                return _empty_d1_result()
            return await env.DB.prepare(
                base_q
                + " JOIN activity_tags at2 ON at2.activity_id=a.id"
                  " WHERE at2.tag_id=? ORDER BY a.created_at DESC"
            ).bind(tag_row.id).all()
        if atype and fmt:
            return await env.DB.prepare(
                base_q + " WHERE a.type=? AND a.format=? ORDER BY a.created_at DESC"
            ).bind(atype, fmt).all()
        if atype:
            return await env.DB.prepare(
                base_q + " WHERE a.type=? ORDER BY a.created_at DESC"
            ).bind(atype).all()
        if fmt:
            return await env.DB.prepare(
                base_q + " WHERE a.format=? ORDER BY a.created_at DESC"
            ).bind(fmt).all()
        return await env.DB.prepare(
            base_q + " ORDER BY a.created_at DESC"
        ).all()

    try:
        res = await fetch_activities()
    except Exception as e:
        if not _is_no_such_table_error(e):
            raise
        await init_db(env)
        res = await fetch_activities()

    activities = []
    for row in res.results or []:
        desc      = await decrypt_aes(row.description or "", enc)
        host_name = await decrypt_aes(row.host_name_enc or "", enc)
        if search and (
            search.lower() not in row.title.lower()
            and search.lower() not in desc.lower()
        ):
            continue

        t_res = await env.DB.prepare(
            "SELECT t.name FROM tags t"
            " JOIN activity_tags at2 ON at2.tag_id=t.id"
            " WHERE at2.activity_id=?"
        ).bind(row.id).all()

        activities.append({
            "id":                row.id,
            "title":             row.title,
            "description":       desc,
            "type":              row.type,
            "format":            row.format,
            "schedule_type":     row.schedule_type,
            "host_name":         host_name,
            "participant_count": row.participant_count,
            "session_count":     row.session_count,
            "tags":              [t.name for t in (t_res.results or [])],
            "created_at":        row.created_at,
        })

    return json_resp({"activities": activities})


async def api_create_activity(req, env):
    user = verify_token(req.headers.get("Authorization"), env.JWT_SECRET)
    if not user:
        return err("Authentication required", 401)

    body, bad_resp = await parse_json_object(req)
    if bad_resp:
        return bad_resp

    title         = (body.get("title")         or "").strip()
    description   = (body.get("description")   or "").strip()
    atype         = (body.get("type")          or "course").strip()
    fmt           = (body.get("format")        or "self_paced").strip()
    schedule_type = (body.get("schedule_type") or "ongoing").strip()

    if not title:
        return err("title is required")
    if atype not in ("course", "meetup", "workshop", "seminar", "other"):
        atype = "course"
    if fmt not in ("live", "self_paced", "hybrid"):
        fmt = "self_paced"
    if schedule_type not in ("one_time", "multi_session", "recurring", "ongoing"):
        schedule_type = "ongoing"

    enc    = env.ENCRYPTION_KEY
    act_id = new_id()
    try:
        await env.DB.prepare(
            "INSERT INTO activities "
            "(id,title,description,type,format,schedule_type,host_id)"
            " VALUES (?,?,?,?,?,?,?)"
        ).bind(
            act_id, title,
            await encrypt_aes(description, enc) if description else "",
            atype, fmt, schedule_type, user["id"]
        ).run()
    except Exception as e:
        await capture_exception(e, req, env, "api_create_activity.insert_activity")
        return err("Failed to create activity — please try again", 500)

    for tag_name in (body.get("tags") or []):
        tag_name = tag_name.strip()
        if not tag_name:
            continue
        t_row = await env.DB.prepare(
            "SELECT id FROM tags WHERE name=?"
        ).bind(tag_name).first()
        if t_row:
            tag_id = t_row.id
        else:
            tag_id = new_id()
            try:
                await env.DB.prepare(
                    "INSERT INTO tags (id,name) VALUES (?,?)"
                ).bind(tag_id, tag_name).run()
            except Exception as e:
                await capture_exception(e, req, env, f"api_create_activity.insert_tag: tag_name={tag_name}, tag_id={tag_id}, act_id={act_id}")
                continue
        try:
            await env.DB.prepare(
                "INSERT OR IGNORE INTO activity_tags (activity_id,tag_id) VALUES (?,?)"
            ).bind(act_id, tag_id).run()
        except Exception as e:
            await capture_exception(e, req, env, f"api_create_activity.insert_activity_tags: tag_name={tag_name}, tag_id={tag_id}, act_id={act_id}")
            pass

    return ok({"id": act_id, "title": title}, "Activity created")


async def api_get_activity(act_id: str, req, env):
    user    = verify_token(req.headers.get("Authorization") or "", env.JWT_SECRET)
    enc     = env.ENCRYPTION_KEY

    act = await env.DB.prepare(
        "SELECT a.*,u.name AS host_name_enc,u.id AS host_uid"
        " FROM activities a JOIN users u ON a.host_id=u.id"
        " WHERE a.id=?"
    ).bind(act_id).first()
    if not act:
        return err("Activity not found", 404)

    enrollment  = None
    is_enrolled = False
    if user:
        enrollment  = await env.DB.prepare(
            "SELECT id,role,status FROM enrollments"
            " WHERE activity_id=? AND user_id=?"
        ).bind(act_id, user["id"]).first()
        is_enrolled = enrollment is not None

    is_host = bool(user and act.host_uid == user["id"])

    ses_res = await env.DB.prepare(
        "SELECT id,title,description,start_time,end_time,location,created_at"
        " FROM sessions WHERE activity_id=? ORDER BY start_time"
    ).bind(act_id).all()

    sessions = []
    for s in ses_res.results or []:
        sessions.append({
            "id":          s.id,
            "title":       s.title,
            "description": await decrypt_aes(s.description or "", enc) if (is_enrolled or is_host) else None,
            "start_time":  s.start_time,
            "end_time":    s.end_time,
            "location":    await decrypt_aes(s.location or "", enc) if (is_enrolled or is_host) else None,
        })

    t_res = await env.DB.prepare(
        "SELECT t.name FROM tags t"
        " JOIN activity_tags at2 ON at2.tag_id=t.id"
        " WHERE at2.activity_id=?"
    ).bind(act_id).all()

    count_row = await env.DB.prepare(
        "SELECT COUNT(*) AS cnt FROM enrollments WHERE activity_id=? AND status='active'"
    ).bind(act_id).first()

    return json_resp({
        "activity": {
            "id":                act.id,
            "title":             act.title,
            "description":       await decrypt_aes(act.description or "", enc),
            "type":              act.type,
            "format":            act.format,
            "schedule_type":     act.schedule_type,
            "host_name":         await decrypt_aes(act.host_name_enc or "", enc),
            "participant_count": count_row.cnt if count_row else 0,
            "tags":              [t.name for t in (t_res.results or [])],
            "created_at":        act.created_at,
        },
        "sessions":    sessions,
        "is_enrolled": is_enrolled,
        "is_host":     is_host,
        "enrollment":  {
            "role":   enrollment.role,
            "status": enrollment.status,
        } if enrollment else None,
    })


async def api_join(req, env):
    user = verify_token(req.headers.get("Authorization"), env.JWT_SECRET)
    if not user:
        return err("Authentication required", 401)

    body, bad_resp = await parse_json_object(req)
    if bad_resp:
        return bad_resp

    act_id = body.get("activity_id")
    role   = (body.get("role") or "participant").strip()

    if not act_id:
        return err("activity_id is required")
    if role not in ("participant", "instructor", "organizer"):
        role = "participant"

    act = await env.DB.prepare(
        "SELECT id FROM activities WHERE id=?"
    ).bind(act_id).first()
    if not act:
        return err("Activity not found", 404)

    enr_id = new_id()
    try:
        await env.DB.prepare(
            "INSERT OR IGNORE INTO enrollments (id,activity_id,user_id,role)"
            " VALUES (?,?,?,?)"
        ).bind(enr_id, act_id, user["id"], role).run()
    except Exception as e:
        await capture_exception(e, req, env, "api_join.insert_enrollment")
        return err("Failed to join activity — please try again", 500)

    return ok(None, "Joined activity successfully")


async def api_dashboard(req, env):
    user = verify_token(req.headers.get("Authorization"), env.JWT_SECRET)
    if not user:
        return err("Authentication required", 401)

    enc = env.ENCRYPTION_KEY

    res = await env.DB.prepare(
        "SELECT a.id,a.title,a.type,a.format,a.schedule_type,a.created_at,"
        "(SELECT COUNT(*) FROM enrollments WHERE activity_id=a.id AND status='active')"
        " AS participant_count,"
        "(SELECT COUNT(*) FROM sessions WHERE activity_id=a.id) AS session_count"
        " FROM activities a WHERE a.host_id=? ORDER BY a.created_at DESC"
    ).bind(user["id"]).all()

    hosted = []
    for r in res.results or []:
        t_res = await env.DB.prepare(
            "SELECT t.name FROM tags t JOIN activity_tags at2 ON at2.tag_id=t.id"
            " WHERE at2.activity_id=?"
        ).bind(r.id).all()
        hosted.append({
            "id":                r.id,
            "title":             r.title,
            "type":              r.type,
            "format":            r.format,
            "schedule_type":     r.schedule_type,
            "participant_count": r.participant_count,
            "session_count":     r.session_count,
            "tags":              [t.name for t in (t_res.results or [])],
            "created_at":        r.created_at,
        })

    res2 = await env.DB.prepare(
        "SELECT a.id,a.title,a.type,a.format,a.schedule_type,"
        "e.role AS enr_role,e.status AS enr_status,e.created_at AS joined_at,"
        "u.name AS host_name_enc"
        " FROM enrollments e"
        " JOIN activities a ON e.activity_id=a.id"
        " JOIN users u ON a.host_id=u.id"
        " WHERE e.user_id=? ORDER BY e.created_at DESC"
    ).bind(user["id"]).all()

    joined = []
    for r in res2.results or []:
        t_res = await env.DB.prepare(
            "SELECT t.name FROM tags t JOIN activity_tags at2 ON at2.tag_id=t.id"
            " WHERE at2.activity_id=?"
        ).bind(r.id).all()
        joined.append({
            "id":            r.id,
            "title":         r.title,
            "type":          r.type,
            "format":        r.format,
            "schedule_type": r.schedule_type,
            "enr_role":      r.enr_role,
            "enr_status":    r.enr_status,
            "host_name":     await decrypt_aes(r.host_name_enc or "", enc),
            "tags":          [t.name for t in (t_res.results or [])],
            "joined_at":     r.joined_at,
        })

    return json_resp({"user": user, "hosted_activities": hosted, "joined_activities": joined})


async def api_create_session(req, env):
    user = verify_token(req.headers.get("Authorization"), env.JWT_SECRET)
    if not user:
        return err("Authentication required", 401)

    body, bad_resp = await parse_json_object(req)
    if bad_resp:
        return bad_resp

    act_id      = body.get("activity_id")
    title       = (body.get("title")       or "").strip()
    description = (body.get("description") or "").strip()
    start_time  = (body.get("start_time")  or "").strip()
    end_time    = (body.get("end_time")    or "").strip()
    location    = (body.get("location")    or "").strip()

    if not act_id or not title:
        return err("activity_id and title are required")

    owned = await env.DB.prepare(
        "SELECT id FROM activities WHERE id=? AND host_id=?"
    ).bind(act_id, user["id"]).first()
    if not owned:
        return err("Activity not found or access denied", 404)

    enc = env.ENCRYPTION_KEY
    sid = new_id()
    try:
        await env.DB.prepare(
            "INSERT INTO sessions "
            "(id,activity_id,title,description,start_time,end_time,location)"
            " VALUES (?,?,?,?,?,?,?)"
        ).bind(
            sid, act_id, title,
            await encrypt_aes(description, enc) if description else "",
            start_time, end_time,
            await encrypt_aes(location, enc) if location else "",
        ).run()
    except Exception as e:
        await capture_exception(e, req, env, "api_create_session.insert_session")
        return err("Failed to create session — please try again", 500)

    return ok({"id": sid}, "Session created")


async def api_list_tags(_req, env):
    res  = await env.DB.prepare("SELECT id,name FROM tags ORDER BY name").all()
    tags = [{"id": r.id, "name": r.name} for r in (res.results or [])]
    return json_resp({"tags": tags})


async def api_add_activity_tags(req, env):
    user = verify_token(req.headers.get("Authorization"), env.JWT_SECRET)
    if not user:
        return err("Authentication required", 401)

    body, bad_resp = await parse_json_object(req)
    if bad_resp:
        return bad_resp

    act_id = body.get("activity_id")
    tags   = body.get("tags") or []

    if not act_id:
        return err("activity_id is required")

    owned = await env.DB.prepare(
        "SELECT id FROM activities WHERE id=? AND host_id=?"
    ).bind(act_id, user["id"]).first()
    if not owned:
        return err("Activity not found or access denied", 404)

    for tag_name in tags:
        tag_name = tag_name.strip()
        if not tag_name:
            continue
        t_row = await env.DB.prepare(
            "SELECT id FROM tags WHERE name=?"
        ).bind(tag_name).first()
        if t_row:
            tag_id = t_row.id
        else:
            tag_id = new_id()
            try:
                await env.DB.prepare(
                    "INSERT INTO tags (id,name) VALUES (?,?)"
                ).bind(tag_id, tag_name).run()
            except Exception as e:
                await capture_exception(e, req, env, f"api_add_activity_tags.insert_tag: tag_name={tag_name}, tag_id={tag_id}, act_id={act_id}")
                continue
        try:
            await env.DB.prepare(
                "INSERT OR IGNORE INTO activity_tags (activity_id,tag_id) VALUES (?,?)"
            ).bind(act_id, tag_id).run()
        except Exception as e:
            await capture_exception(e, req, env, f"api_add_activity_tags.insert_activity_tags: tag_name={tag_name}, tag_id={tag_id}, act_id={act_id}")
            pass

    return ok(None, "Tags updated")


async def api_admin_table_counts(req, env):
    if not _is_basic_auth_valid(req, env):
        return _unauthorized_basic()

    async def fetch_counts():
        tables_res = await env.DB.prepare(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).all()

        counts = []
        for row in tables_res.results or []:
            table_name = row.name
            count_row = await env.DB.prepare(
                f'SELECT COUNT(*) AS cnt FROM "{table_name.replace(chr(34), chr(34) + chr(34))}"'
            ).first()
            counts.append({"table": table_name, "count": count_row.cnt if count_row else 0})
        return counts

    try:
        counts = await fetch_counts()
    except Exception as e:
        if not _is_no_such_table_error(e):
            raise
        await init_db(env)
        counts = await fetch_counts()

    return json_resp({"tables": counts})


# ---------------------------------------------------------------------------
# Static-asset serving  (Workers Sites / __STATIC_CONTENT KV)
# ---------------------------------------------------------------------------

_MIME = {
    "html": "text/html; charset=utf-8",
    "css":  "text/css; charset=utf-8",
    "js":   "application/javascript; charset=utf-8",
    "json": "application/json",
    "png":  "image/png",
    "jpg":  "image/jpeg",
    "svg":  "image/svg+xml",
    "ico":  "image/x-icon",
}


async def serve_static(path: str, env):
    if path in ("/", ""):
        key = "index.html"
    else:
        key = path.lstrip("/")
        if "." not in key.split("/")[-1]:
            key += ".html"

    try:
        content = await env.__STATIC_CONTENT.get(key, "text")
    except Exception:
        content = None

    if content is None:
        try:
            content = await env.__STATIC_CONTENT.get("index.html", "text")
        except Exception:
            content = None

    if content is None:
        return Response(
            "<h1>404 - Not Found</h1>",
            status=404,
            headers={"Content-Type": "text/html"},
        )

    ext  = key.rsplit(".", 1)[-1] if "." in key else "html"
    mime = _MIME.get(ext, "text/plain")
    return Response(content, headers={"Content-Type": mime, **_CORS})

class ClassroomDO(DurableObject):
    """WebSocket based virtual classroom Durable Object.

    Each room_id maps to one DO instance.  Connected clients share:
      - room_state   (participant list, broadcast on join/leave)
      - position_update (x/y movement relay)
      - chat_message  (basic text relay)
      - seat mgmt     (update_seat / leave_seat)
    """

    def __init__(self, ctx, env):
        super().__init__(ctx, env)
        # sessions: session_id -> {ws, participant_id, display_name, position, direction, is_moving, seat_id}
        self.sessions = {}

        # Restore hibernated WebSocket connections
        for ws in self.ctx.getWebSockets():
            try:
                attachment = ws.deserializeAttachment()
                if not attachment:
                    continue
                data = json.loads(attachment) if isinstance(attachment, str) else attachment
                sid = data.get("session_id", str(uuid.uuid4()))
                self.sessions[sid] = {
                    "ws":             ws,
                    "participant_id": data.get("participant_id", "unknown"),
                    "display_name":   data.get("display_name", "Unknown"),
                    "position":       data.get("position", {"x": 0.5, "y": 0.5}),
                    "direction":      data.get("direction", "down"),
                    "is_moving":      False,
                    "seat_id":        data.get("seat_id", ""),
                }
            except Exception as exc:
                print(f"[ClassroomDO.__init__.restore] error={exc!r}")

        self.ctx.setWebSocketAutoResponse(
            WebSocketRequestResponsePair.new("ping", "pong")
        )

    async def on_fetch(self, request):
        upgrade = request.headers.get("Upgrade") or ""
        if upgrade.lower() != "websocket":
            return Response(
                json.dumps({"error": "Expected WebSocket upgrade"}),
                status=426,
                headers={"Content-Type": "application/json"},
            )

        parsed = urlparse(request.url)
        qs = parse_qs(parsed.query)

        token_param = (qs.get("token") or [None])[0]
        participant_param = (qs.get("participant_id") or [None])[0]
        display_name_param = (qs.get("display_name") or [None])[0]

        authenticated_user = verify_token(token_param or "", self.env.JWT_SECRET) if token_param else None
        allow_anonymous_poc = (
            str(getattr(self.env, "ALLOW_ANON_CLASSROOM_POC", "")).lower()
            in {"1", "true", "yes"}
        )

        if authenticated_user:
            # Derive identity from the verified token, not from untrusted query params.
            participant_id = authenticated_user["id"]
            display_name = authenticated_user.get("username") or participant_id
        else:
            # Allow anonymous POC joins only when explicitly enabled.
            if token_param or not allow_anonymous_poc or not participant_param:
                return Response(
                    json.dumps({"error": "Authentication required"}),
                    status=401,
                    headers={"Content-Type": "application/json"},
                )
            participant_id = participant_param
            display_name = display_name_param or participant_id

        # Sanitise inputs
        participant_id = participant_id[:64]
        display_name   = display_name[:64]

        # Create WebSocket pair
        client, server = WebSocketPair.new().object_values()
        self.ctx.acceptWebSocket(server)

        session_id = str(uuid.uuid4())

        # Re-use the last known position/seat if the same participant reconnects
        # (e.g. page refresh or network blip).
        existing = next(
            (s for s in self.sessions.values()
             if s["participant_id"] == participant_id),
            None,
        )
        already_connected = existing is not None
        initial_position  = dict(existing["position"])       if existing else {"x": 0.5, "y": 0.5}
        initial_direction = existing["direction"]             if existing else "down"
        initial_seat_id   = existing.get("seat_id", "")      if existing else ""

        attachment = json.dumps({
            "session_id":     session_id,
            "participant_id": participant_id,
            "display_name":   display_name,
            "position":       initial_position,
            "direction":      initial_direction,
            "seat_id":        initial_seat_id,
        })
        server.serializeAttachment(attachment)

        self.sessions[session_id] = {
            "ws":             server,
            "participant_id": participant_id,
            "display_name":   display_name,
            "position":       initial_position,
            "direction":      initial_direction,
            "is_moving":      False,
            "seat_id":        initial_seat_id,
        }

        try:
            server.send(json.dumps({
                "type":           "user_info",
                "session_id":     session_id,
                "participant_id": participant_id,
                "display_name":   display_name,
            }))
        except Exception as exc:
            await capture_exception(exc, request, self.env, "classroom_on_fetch.send_user_info")

        self._broadcast_room_state()

        if not already_connected:
            self._broadcast(json.dumps({
                "type":           "participant_joined",
                "participant_id": participant_id,
                "display_name":   display_name,
            }), exclude_session_id=session_id)

        return Response(None, status=101, web_socket=client)

    async def on_webSocketMessage(self, ws, message):
        try:
            raw_message = message if isinstance(message, str) else message.decode("utf-8")
            if len(raw_message) > 4096:
                return
            data = json.loads(raw_message)
        except Exception as exc:
            await capture_exception(exc, None, self.env, "classroom_on_webSocketMessage.parse")
            return
        if not isinstance(data, dict):
            return

        msg_type = data.get("type", "")
        session  = self._session_for_ws(ws)
        if not session:
            return

        sid, info = session

        def _valid_norm_position(value):
            """Accept normalized (0-1) position dicts; reject anything else."""
            if not isinstance(value, dict):
                return None
            try:
                x = float(value.get("x", 0.5))
                y = float(value.get("y", 0.5))
            except (TypeError, ValueError):
                return None
            # Clamp to [0, 1] — normalized coordinate space
            return {"x": max(0.0, min(1.0, x)), "y": max(0.0, min(1.0, y))}

        if msg_type == "position_update":
            position = _valid_norm_position(data.get("position"))
            if position is None:
                return
            direction = data.get("direction", info["direction"])
            if not isinstance(direction, str) or direction not in {"up", "down", "left", "right"}:
                direction = info["direction"]
            is_moving = data.get("isMoving", False)
            if not isinstance(is_moving, bool):
                is_moving = False
            info["position"]  = position
            info["direction"] = direction
            info["is_moving"] = is_moving
            for s_id, s_info in self.sessions.items():
                if s_info["participant_id"] == info["participant_id"]:
                    s_info["position"]  = position
                    s_info["direction"] = direction
                    s_info["is_moving"] = info["is_moving"]
                    self._persist_attachment(s_id, s_info)

            self._broadcast(json.dumps({
                "type":           "position_update",
                "participant_id": info["participant_id"],
                "display_name":   info["display_name"],
                "position":       info["position"],
                "direction":      info["direction"],
                "isMoving":       info["is_moving"],
            }), exclude_session_id=sid)

        elif msg_type == "chat_message":
            raw_text = data.get("text", "")
            if not isinstance(raw_text, str):
                return
            text = raw_text.strip()[:500]
            if not text:
                return
            raw_timestamp = data.get("timestamp", "")
            timestamp = raw_timestamp[:64] if isinstance(raw_timestamp, str) else ""
            self._broadcast(json.dumps({
                "type":           "chat_message",
                "participant_id": info["participant_id"],
                "display_name":   info["display_name"],
                "text":           text,
                "timestamp":      timestamp,
            }))

        
        elif msg_type == "update_seat":
            # Classroom layout, keep in sync with DESK_ROWS/DESK_COLS in classroom_poc.html
            DESK_ROWS = 3
            DESK_COLS = 5
            MAX_SEATS = DESK_ROWS * DESK_COLS

            seat_id = data.get("seat_id", "")
            # Validate seat_id: must be "seat-N" where N is 1..DESK_ROWS*DESK_COLS
            if not isinstance(seat_id, str) or not re.fullmatch(r"seat-\d+", seat_id):
                return
            seat_num = int(seat_id.split("-", 1)[1])
            if not (1 <= seat_num <= MAX_SEATS):
                return

            for other_info in self.sessions.values():
                if (other_info["seat_id"] == seat_id
                        and other_info["participant_id"] != info["participant_id"]):
                    try:
                        ws.send(json.dumps({
                            "type":    "seat_occupied",
                            "message": "This seat is already taken by another student.",
                            "seat_id": seat_id,
                        }))
                    except Exception as exc:
                        await capture_exception(exc, None, self.env,
                            f"classroom.seat_occupied_send pid={info['participant_id']} seat={seat_id}")
                    return

            for s_id, s_info in self.sessions.items():
                if s_info["participant_id"] == info["participant_id"]:
                    s_info["seat_id"] = seat_id
                    self._persist_attachment(s_id, s_info)

            self._broadcast(json.dumps({
                "type":           "seat_updated",
                "participant_id": info["participant_id"],
                "display_name":   info["display_name"],
                "seat_id":        seat_id,
            }))
            self._broadcast_room_state()

        elif msg_type == "leave_seat":
            old_seat = info["seat_id"]
            if not old_seat:
                return
            for s_id, s_info in self.sessions.items():
                if s_info["participant_id"] == info["participant_id"]:
                    s_info["seat_id"] = ""
                    self._persist_attachment(s_id, s_info)

            self._broadcast(json.dumps({
                "type":           "seat_left",
                "participant_id": info["participant_id"],
                "display_name":   info["display_name"],
                "seat_id":        old_seat,
            }))
            self._broadcast_room_state()

    async def on_webSocketClose(self, ws, code, reason, wasClean):
        session = self._session_for_ws(ws)
        if not session:
            return

        sid, info  = session
        pid        = info["participant_id"]
        dname      = info["display_name"]

        self.sessions.pop(sid, None)

        still_connected = any(
            s["participant_id"] == pid for s in self.sessions.values()
        )

        if not still_connected:
            self._broadcast(json.dumps({
                "type":           "participant_left",
                "participant_id": pid,
                "display_name":   dname,
            }))

        self._broadcast_room_state()

    async def on_webSocketError(self, ws, error):
        # Log for visibility; the runtime will invoke on_webSocketClose separately
        # which performs the actual session cleanup and broadcasts.
        print(f"[ClassroomDO.on_webSocketError] error={error!r}")

    # HELPERS:

    def _session_for_ws(self, ws):
        try:
            raw = ws.deserializeAttachment()
            if raw:
                data = json.loads(raw) if isinstance(raw, str) else raw
                sid  = data.get("session_id", "")
                if sid and sid in self.sessions:
                    return (sid, self.sessions[sid])
        except Exception as exc:
            print(f"[ClassroomDO._session_for_ws.deserialize] error={exc!r}")

        for sid, info in self.sessions.items():
            try:
                if info["ws"] == ws:
                    return (sid, info)
            except Exception as exc:
                print(f"[ClassroomDO._session_for_ws.fallback] sid={sid} error={exc!r}")
        return None

    def _broadcast(self, msg, exclude_session_id=None):
        for sid, info in self.sessions.items():
            if sid == exclude_session_id:
                continue
            try:
                info["ws"].send(msg)
            except Exception as exc:
                print(f"[ClassroomDO._broadcast] sid={sid} pid={info.get('participant_id')} error={exc!r}")
                # Do not pop here - rely on on_webSocketClose to run the full
                # cleanup + participant_left broadcast. Transient send errors
                # shouldn't silently evict a session.

    def _broadcast_room_state(self):
        seen = {}
        for info in self.sessions.values():
            pid = info["participant_id"]
            if pid not in seen:
                seen[pid] = {
                    "participant_id": pid,
                    "display_name":   info["display_name"],
                    "position":       info["position"],
                    "direction":      info["direction"],
                    "is_moving":      info.get("is_moving", False),
                    "seat_id":        info.get("seat_id", ""),
                }

        self._broadcast(json.dumps({
            "type":         "room_state",
            "participants": list(seen.values()),
            "count":        len(seen),
        }))

    def _persist_attachment(self, session_id, info):
        ws = self.sessions.get(session_id, {}).get("ws")
        if not ws:
            return
        try:
            ws.serializeAttachment(json.dumps({
                "session_id":     session_id,
                "participant_id": info["participant_id"],
                "display_name":   info["display_name"],
                "position":       info["position"],
                "direction":      info["direction"],
                "seat_id":        info.get("seat_id", ""),
            }))
        except Exception as exc:
            print(f"[ClassroomDO._persist_attachment] sid={session_id} pid={info.get('participant_id')} error={exc!r}")


class PresenceDO(DurableObject):
    """Room-scoped real-time user presence Durable Object."""

    def __init__(self, ctx, env):
        super().__init__(ctx, env)
        # session_id -> {ws, user_id, display_name}
        self.sessions = {}
        # user_id -> {x, y, emoji, hand_raised, display_name}
        self.presence = {}

        for ws in self.ctx.getWebSockets():
            try:
                attachment = ws.deserializeAttachment()
                if not attachment:
                    continue
                data = json.loads(attachment) if isinstance(attachment, str) else attachment
                session_id = data.get("session_id", str(uuid.uuid4()))
                user_id = str(data.get("user_id", ""))[:64]
                display_name = str(data.get("display_name", user_id or "Unknown"))[:64]
                if not user_id:
                    continue

                self.sessions[session_id] = {
                    "ws": ws,
                    "user_id": user_id,
                    "display_name": display_name,
                }
                if user_id not in self.presence:
                    self.presence[user_id] = {
                        "x": self._clamp_01(data.get("x", 0.5)),
                        "y": self._clamp_01(data.get("y", 0.5)),
                        "emoji": data.get("emoji", "") if isinstance(data.get("emoji", ""), str) else "",
                        "hand_raised": data.get("hand_raised", False) is True,
                        "display_name": display_name,
                    }
            except Exception as exc:
                print(f"[PresenceDO.__init__.restore] error={exc!r}")

        self.ctx.setWebSocketAutoResponse(
            WebSocketRequestResponsePair.new("ping", "pong")
        )

    async def on_fetch(self, request):
        upgrade = request.headers.get("Upgrade") or ""
        if upgrade.lower() != "websocket":
            return Response(
                json.dumps({"error": "Expected WebSocket upgrade"}),
                status=426,
                headers={"Content-Type": "application/json"},
            )

        parsed = urlparse(request.url)
        qs = parse_qs(parsed.query)
        token_param = (qs.get("token") or [None])[0]
        user_param = (qs.get("user_id") or [None])[0]
        display_param = (qs.get("display_name") or [None])[0]

        allow_presence_setting = getattr(self.env, "ALLOW_ANON_PRESENCE", None)
        if allow_presence_setting is None:
            allow_presence_setting = getattr(self.env, "ALLOW_ANON_CLASSROOM_POC", "")
        allow_anonymous = str(allow_presence_setting).lower() in {"1", "true", "yes"}
        authenticated_user = verify_token(token_param or "", self.env.JWT_SECRET) if token_param else None

        if authenticated_user:
            user_id = str(authenticated_user.get("id", ""))
            display_name = str(authenticated_user.get("username") or user_id)
        else:
            if token_param or not allow_anonymous or not user_param:
                return Response(
                    json.dumps({"error": "Authentication required"}),
                    status=401,
                    headers={"Content-Type": "application/json"},
                )
            user_id = str(user_param)
            display_name = str(display_param or user_id)

        user_id = user_id[:64]
        display_name = display_name[:64]
        if not user_id:
            return Response(
                json.dumps({"error": "Invalid user_id"}),
                status=400,
                headers={"Content-Type": "application/json"},
            )

        client, server = WebSocketPair.new().object_values()
        self.ctx.acceptWebSocket(server)

        session_id = str(uuid.uuid4())
        existing = self.presence.get(user_id)
        if existing is None:
            existing = {
                "x": 0.5,
                "y": 0.5,
                "emoji": "",
                "hand_raised": False,
                "display_name": display_name,
            }
            self.presence[user_id] = dict(existing)
        else:
            existing["display_name"] = display_name
            self.presence[user_id] = existing

        attachment = json.dumps({
            "session_id": session_id,
            "user_id": user_id,
            "display_name": display_name,
            "x": existing["x"],
            "y": existing["y"],
            "emoji": existing["emoji"],
            "hand_raised": existing["hand_raised"],
        })
        server.serializeAttachment(attachment)

        self.sessions[session_id] = {
            "ws": server,
            "user_id": user_id,
            "display_name": display_name,
        }

        self._send_welcome(server, session_id, user_id)
        self._broadcast(
            json.dumps({
                "type": "delta",
                "user_id": user_id,
                "display_name": display_name,
                "x": existing["x"],
                "y": existing["y"],
                "emoji": existing["emoji"],
                "hand_raised": existing["hand_raised"],
            }),
            exclude_session_id=session_id,
        )

        return Response(None, status=101, web_socket=client)

    async def on_webSocketMessage(self, ws, message):
        try:
            raw = message if isinstance(message, str) else message.decode("utf-8")
            if len(raw) > 512:
                print("[PresenceDO.on_webSocketMessage] dropped oversized payload")
                return
            data = json.loads(raw)
        except Exception as exc:
            await capture_exception(exc, None, self.env, "presence_on_webSocketMessage.parse")
            return

        if not isinstance(data, dict):
            return

        session = self._session_for_ws(ws)
        if not session:
            return
        sid, info = session
        user_id = info["user_id"]
        current = self.presence.get(user_id)
        if current is None:
            current = {
                "x": 0.5,
                "y": 0.5,
                "emoji": "",
                "hand_raised": False,
                "display_name": info["display_name"],
            }
            self.presence[user_id] = current

        msg_type = data.get("type", "")
        if msg_type == "join":
            self._send_welcome(ws, sid, user_id)
            return

        if msg_type != "presence":
            return

        delta = {"type": "delta", "user_id": user_id}
        changed = False

        if "x" in data:
            next_x = self._clamp_01(data.get("x"))
            if next_x != current["x"]:
                current["x"] = next_x
                delta["x"] = next_x
                changed = True

        if "y" in data:
            next_y = self._clamp_01(data.get("y"))
            if next_y != current["y"]:
                current["y"] = next_y
                delta["y"] = next_y
                changed = True

        if "emoji" in data and isinstance(data.get("emoji"), str):
            next_emoji = data.get("emoji", "")[:32]
            if next_emoji != current["emoji"]:
                current["emoji"] = next_emoji
                delta["emoji"] = next_emoji
                changed = True

        if "hand_raised" in data and isinstance(data.get("hand_raised"), bool):
            next_hand = data.get("hand_raised")
            if next_hand != current["hand_raised"]:
                current["hand_raised"] = next_hand
                delta["hand_raised"] = next_hand
                changed = True

        if "display_name" in data and isinstance(data.get("display_name"), str):
            next_display_name = data.get("display_name", "").strip()[:64]
            if next_display_name and next_display_name != current.get("display_name", ""):
                current["display_name"] = next_display_name
                delta["display_name"] = next_display_name
                for session_info in self.sessions.values():
                    if session_info["user_id"] == user_id:
                        session_info["display_name"] = next_display_name
                changed = True

        if not changed:
            return

        self.presence[user_id] = current
        self._persist_user_attachments(user_id)
        self._broadcast(json.dumps(delta), exclude_session_id=sid)

    async def on_webSocketClose(self, ws, _code, _reason, _was_clean):
        session = self._session_for_ws(ws)
        if not session:
            return

        sid, info = session
        user_id = info["user_id"]
        self.sessions.pop(sid, None)

        still_connected = any(s["user_id"] == user_id for s in self.sessions.values())
        if not still_connected:
            self.presence.pop(user_id, None)
            self._broadcast(json.dumps({"type": "leave", "user_id": user_id}))

    async def on_webSocketError(self, _ws, error):
        print(f"[PresenceDO.on_webSocketError] error={error!r}")

    def _send_welcome(self, ws, session_id, user_id):
        snapshot = {uid: dict(state) for uid, state in self.presence.items()}
        try:
            ws.send(json.dumps({
                "type": "welcome",
                "session_id": session_id,
                "user_id": user_id,
                "state": snapshot,
            }))
        except Exception as exc:
            print(f"[PresenceDO._send_welcome] error={exc!r}")

    def _session_for_ws(self, ws):
        try:
            raw = ws.deserializeAttachment()
            if raw:
                data = json.loads(raw) if isinstance(raw, str) else raw
                session_id = data.get("session_id", "")
                if session_id and session_id in self.sessions:
                    return session_id, self.sessions[session_id]
        except Exception as exc:
            print(f"[PresenceDO._session_for_ws.deserialize] error={exc!r}")

        for sid, info in self.sessions.items():
            try:
                if info["ws"] == ws:
                    return sid, info
            except Exception as exc:
                print(f"[PresenceDO._session_for_ws.fallback] sid={sid} error={exc!r}")
        return None

    def _broadcast(self, payload, exclude_session_id=None):
        for sid, info in self.sessions.items():
            if sid == exclude_session_id:
                continue
            try:
                info["ws"].send(payload)
            except Exception as exc:
                print(f"[PresenceDO._broadcast] sid={sid} user_id={info.get('user_id')} error={exc!r}")

    def _persist_user_attachments(self, user_id):
        state = self.presence.get(user_id)
        if not state:
            return
        for sid, info in self.sessions.items():
            if info["user_id"] != user_id:
                continue
            try:
                info["ws"].serializeAttachment(json.dumps({
                    "session_id": sid,
                    "user_id": user_id,
                    "display_name": info["display_name"],
                    "x": state["x"],
                    "y": state["y"],
                    "emoji": state["emoji"],
                    "hand_raised": state["hand_raised"],
                }))
            except Exception as exc:
                print(f"[PresenceDO._persist_user_attachments] sid={sid} user_id={user_id} error={exc!r}")

    @staticmethod
    def _clamp_01(value):
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.5


# ---------------------------------------------------------------------------
# Main dispatcher
# ---------------------------------------------------------------------------

async def _dispatch(request, env):
    path   = urlparse(request.url).path
    method = request.method.upper()
    admin_path = _clean_path(getattr(env, "ADMIN_URL", ""))

    if method == "OPTIONS":
        return Response("", status=204, headers=_CORS)

    if path == admin_path and method == "GET":
        if not _is_basic_auth_valid(request, env):
            return _unauthorized_basic()
        return await serve_static("/admin.html", env)

    m_classroom = re.fullmatch(r"/api/classroom/([A-Za-z0-9_-]+)", path)
    if m_classroom:
        room_id = m_classroom.group(1)
        try:
            do_id = env.CLASSROOM_DO.idFromName(room_id)
            stub = env.CLASSROOM_DO.get(do_id)
            return await stub.fetch(request)
        except Exception as e:
            await capture_exception(e, request, env, "classroom_do_dispatch")
            return err("Failed to connect to classroom", 500)

    m_presence = re.fullmatch(r"/api/presence/([A-Za-z0-9_-]+)", path)
    if m_presence:
        room_id = m_presence.group(1)
        try:
            do_id = env.PRESENCE_DO.idFromName(room_id)
            stub = env.PRESENCE_DO.get(do_id)
            return await stub.fetch(request)
        except Exception as e:
            await capture_exception(e, request, env, "presence_do_dispatch")
            return err("Failed to connect to presence channel", 500)

    if path.startswith("/api/"):
        if path == "/api/init" and method == "POST":
            try:
                await init_db(env)
                return ok(None, "Database initialised")
            except Exception as e:
                await capture_exception(e, request, env, "api_init")
                return err("Database init failed — check D1 binding", 500)

        if path == "/api/seed" and method == "POST":
            try:
                await init_db(env)
                await seed_db(env, env.ENCRYPTION_KEY)
                return ok(None, "Sample data seeded")
            except Exception as e:
                await capture_exception(e, request, env, "api_seed")
                return err("Seed failed — check D1 binding and schema", 500)

        if path == "/api/register" and method == "POST":
            return await api_register(request, env)

        if path == "/api/login" and method == "POST":
            return await api_login(request, env)

        if path == "/api/activities" and method == "GET":
            return await api_list_activities(request, env)

        if path == "/api/activities" and method == "POST":
            return await api_create_activity(request, env)

        m = re.fullmatch(r"/api/activities/([A-Za-z0-9_-]+)", path)
        if m and method == "GET":
            return await api_get_activity(m.group(1), request, env)

        if path == "/api/join" and method == "POST":
            return await api_join(request, env)

        if path == "/api/dashboard" and method == "GET":
            return await api_dashboard(request, env)

        if path == "/api/sessions" and method == "POST":
            return await api_create_session(request, env)

        if path == "/api/tags" and method == "GET":
            return await api_list_tags(request, env)

        if path == "/api/activity-tags" and method == "POST":
            return await api_add_activity_tags(request, env)

        if path == "/api/admin/table-counts" and method == "GET":
            return await api_admin_table_counts(request, env)

        if path.rstrip("/") == "/api/error" and method == "GET":
            exc = RuntimeError("Sentry test error from /api/error")
            await capture_exception(exc, request, env, "api_error_test")
            return ok(None, "Test error sent to Sentry v2")

        return err("API endpoint not found", 404)

    return await serve_static(path, env)


async def on_fetch(request, env):
    try:
        init_sentry(env)
        return await _dispatch(request, env)
    except Exception as e:
        await capture_exception(e, request, env, "on_fetch_unhandled")
        return err("Internal server error", 500)
