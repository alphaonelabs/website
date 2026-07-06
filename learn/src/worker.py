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
import datetime
import hashlib
import hmac as _hmac
import json
import os
import re
import traceback
from types import SimpleNamespace
from typing import Any, Dict, Optional
from urllib.parse import urlparse, parse_qs, urlencode, quote, unquote

from workers import Response, DurableObject

import js
from pyodide.ffi import to_js
from js import WebSocketPair, WebSocketRequestResponsePair
import uuid

_SENTRY_INITIALIZED = False
_SENTRY_DSN: str = ""
_AES_CRYPTO_KEY_CACHE: Dict[str, object] = {}


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


async def _get_aes_crypto_key(secret: str) -> object:
    """Return a cached AES-GCM CryptoKey for this Worker isolate."""
    cached = _AES_CRYPTO_KEY_CACHE.get(secret)
    if cached is not None:
        return cached
    key_bytes = _derive_aes_key_bytes(secret)
    crypto_key = await _import_aes_key(key_bytes)
    _AES_CRYPTO_KEY_CACHE[secret] = crypto_key
    return crypto_key


async def encrypt_aes(plaintext: str, secret: str) -> str:
    """
    AES-256-GCM encryption using js.crypto.subtle (Web Crypto API).
    Returns "v1:" + base64(iv || ciphertext+tag).
    Raises RuntimeError on encryption failure — no silent XOR fallback.
    """
    if not plaintext:
        return ""
    try:
        crypto_key = await _get_aes_crypto_key(secret)

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
        crypto_key = await _get_aes_crypto_key(secret)
        iv_array   = to_js(iv, create_pyproxies=False)
        algo       = to_js({"name": "AES-GCM", "iv": iv_array}, dict_converter=js.Object.fromEntries)
        data       = to_js(ct, create_pyproxies=False)
        pt_buf     = await js.crypto.subtle.decrypt(algo, crypto_key, data)
        return bytes(js.Uint8Array.new(pt_buf)).decode("utf-8")
    except Exception as exc:
        await capture_exception(exc, where="decrypt_aes.auth")
        return "[decryption error]"


async def decrypt_aes_with_key(ciphertext: str, crypto_key: object, secret: str) -> str:
    """
    AES-256-GCM decryption using a pre-imported CryptoKey.
    Handles both v1 (AES-GCM) and legacy (XOR) ciphertext.
    """
    if not ciphertext:
        return ""
    if not ciphertext.startswith("v1:"):
        return _decrypt_xor(ciphertext, secret)
    try:
        raw = base64.b64decode(ciphertext[3:])
        iv, ct = raw[:12], raw[12:]
    except Exception as exc:
        await capture_exception(exc, where="decrypt_aes_with_key.decode")
        return "[decryption error]"
    try:
        iv_array = to_js(iv, create_pyproxies=False)
        algo = to_js({"name": "AES-GCM", "iv": iv_array}, dict_converter=js.Object.fromEntries)
        data = to_js(ct, create_pyproxies=False)
        pt_buf = await js.crypto.subtle.decrypt(algo, crypto_key, data)
        return bytes(js.Uint8Array.new(pt_buf)).decode("utf-8")
    except Exception as exc:
        await capture_exception(exc, where="decrypt_aes_with_key.auth")
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
    if _verify_django_password(password, stored):
        return True
    return hash_password(password, username) == stored


def _verify_django_password(password: str, stored: str) -> bool:
    """Verify legacy Django PBKDF2 password hashes preserved during migration."""
    if not stored or "$" not in stored:
        return False
    try:
        algorithm, iterations_raw, salt, encoded = stored.split("$", 3)
        if algorithm == "pbkdf2_sha256":
            digest = "sha256"
        elif algorithm == "pbkdf2_sha1":
            digest = "sha1"
        else:
            return False
        iterations = int(iterations_raw)
        dk = hashlib.pbkdf2_hmac(
            digest, password.encode("utf-8"), salt.encode("utf-8"), iterations
        )
        calculated = base64.b64encode(dk).decode("ascii").strip()
        return _hmac.compare_digest(calculated, encoded)
    except Exception:
        return False


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
    "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Guest-Cart",
}


def json_resp(data, status: int = 200):
    return Response(
        json.dumps(data),
        status=status,
        headers={"Content-Type": "application/json", **_CORS},
    )


_US_ZIP_RE = re.compile(r"\b\d{5}(?:-\d{4})?\b")
_CA_POSTAL_RE = re.compile(r"\b[A-Z]\d[A-Z][ -]?\d[A-Z]\d\b", re.I)


def _extract_location_zip_codes(location: str) -> list:
    """Return ZIP/postal codes found in a decrypted location string."""
    if not location:
        return []
    found = []
    for match in _US_ZIP_RE.findall(location):
        found.append(match)
    for match in _CA_POSTAL_RE.findall(location):
        found.append(re.sub(r"\s+", "", match.upper()))
    deduped = []
    for code in found:
        if code not in deduped:
            deduped.append(code)
    return deduped


def _normalize_location_code(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", str(value or "").upper())


def _location_codes_match(query: str, codes: list) -> bool:
    normalized_query = _normalize_location_code(query)
    if not normalized_query:
        return True

    for code in codes or []:
        normalized_code = _normalize_location_code(code)
        if normalized_code == normalized_query:
            return True
        if normalized_query.isdigit() and len(normalized_query) == 5 and normalized_code.startswith(normalized_query):
            return True
        if normalized_code.isdigit() and len(normalized_code) == 5 and normalized_query.startswith(normalized_code):
            return True

    return False


def _get_request_postal_code(req) -> str:
    cf = getattr(req, "cf", None)
    if not cf:
        return ""
    if isinstance(cf, dict):
        return cf.get("postalCode") or cf.get("postal_code") or ""
    return getattr(cf, "postalCode", "") or getattr(cf, "postal_code", "") or ""


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


def _slugify(value: str, fallback: str = "activity") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return (slug or fallback).strip("-")[:80] or fallback


async def _unique_activity_slug(env, title: str, activity_id: str) -> str:
    base = _slugify(title, activity_id[:8])
    slug = base
    suffix = 2
    while True:
        row = await env.DB.prepare(
            "SELECT id FROM activities WHERE slug=? AND id<>? LIMIT 1"
        ).bind(slug, activity_id).first()
        if not row:
            return slug
        tail = f"-{suffix}"
        slug = (base[: 80 - len(tail)].rstrip("-") or activity_id[:8]) + tail
        suffix += 1


def _referral_code_hash(code: str, enc: str) -> str:
    return blind_index((code or "").strip(), enc)


def _random_referral_code() -> str:
    return base64.b32encode(os.urandom(5)).decode("ascii").rstrip("=")[:8]


async def _unique_referral_code(env, enc: str) -> str:
    for _ in range(20):
        code = _random_referral_code()
        row = await env.DB.prepare(
            "SELECT user_id FROM user_profiles WHERE referral_code_hash=? LIMIT 1"
        ).bind(_referral_code_hash(code, enc)).first()
        if not row:
            return code
    return hashlib.sha256(os.urandom(16)).hexdigest()[:8].upper()


async def _referrer_user_id_for_code(env, enc: str, code: str) -> str:
    code = (code or "").strip()
    if not code:
        return ""
    row = await env.DB.prepare(
        "SELECT user_id FROM user_profiles WHERE referral_code_hash=? LIMIT 1"
    ).bind(_referral_code_hash(code, enc)).first()
    return row.user_id if row else ""


async def _ensure_user_profile(env, user_id: str, enc: str, referred_by_user_id: str = ""):
    row = await env.DB.prepare(
        "SELECT referral_code,referral_code_hash,referral_earnings_cents,referred_by_user_id FROM user_profiles WHERE user_id=?"
    ).bind(user_id).first()
    if row:
        code = await decrypt_aes(getattr(row, "referral_code", "") or "", enc)
        if not code or code == "[decryption error]":
            code = await _unique_referral_code(env, enc)
            code_enc = await encrypt_aes(code, enc)
        else:
            code_enc = getattr(row, "referral_code", "") or ""
        code_hash = getattr(row, "referral_code_hash", "") or _referral_code_hash(code, enc)
        next_referred_by = getattr(row, "referred_by_user_id", "") or referred_by_user_id or ""
        await env.DB.prepare(
            "UPDATE user_profiles SET referral_code=?,referral_code_hash=?,referred_by_user_id=? WHERE user_id=?"
        ).bind(code_enc, code_hash, next_referred_by, user_id).run()
        return {
            "referral_code": code,
            "referral_earnings_cents": int(getattr(row, "referral_earnings_cents", 0) or 0),
            "referred_by_user_id": next_referred_by,
        }
    code = await _unique_referral_code(env, enc)
    await env.DB.prepare(
        "INSERT INTO user_profiles"
        " (user_id,referral_code,referral_code_hash,referred_by_user_id,referral_earnings_cents)"
        " VALUES (?,?,?,?,?)"
    ).bind(
        user_id,
        await encrypt_aes(code, enc),
        _referral_code_hash(code, enc),
        referred_by_user_id or "",
        0,
    ).run()
    return {"referral_code": code, "referral_earnings_cents": 0, "referred_by_user_id": referred_by_user_id or ""}


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
# Secure token helpers
# ---------------------------------------------------------------------------

def generate_secure_token() -> str:
    """Return a cryptographically secure URL-safe token (256 bits of entropy)."""
    return base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode("ascii")


def hash_token(token: str) -> str:
    """SHA-256 hash of a token for safe database storage. Never store plaintext."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Email service (SendGrid / Mailgun)
# ---------------------------------------------------------------------------

async def _send_email_via_sendgrid(to_email: str, subject: str, html: str, env) -> bool:
    """Send a transactional email via SendGrid when SENDGRID_API_KEY is configured."""
    api_key = (getattr(env, "SENDGRID_API_KEY", "") or "").strip()
    from_addr = (
        getattr(env, "EMAIL_FROM", "")
        or getattr(env, "DEFAULT_FROM_EMAIL", "")
        or "info@alphaonelabs.com"
    ).strip()

    if not api_key:
        return False

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_addr},
        "subject": subject,
        "content": [{"type": "text/html", "value": html}],
    }
    try:
        options = to_js(
            {
                "method": "POST",
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                "body": json.dumps(payload),
            },
            dict_converter=js.Object.fromEntries,
        )
        resp = await js.fetch("https://api.sendgrid.com/v3/mail/send", options)
        if resp.status not in (200, 201, 202):
            body_text = await resp.text()
            print(json.dumps({"level": "warn", "where": "_send_email_via_sendgrid",
                              "status": resp.status, "body": body_text[:300]}))
            return False
        return True
    except Exception as exc:
        print(json.dumps({"level": "error", "where": "_send_email_via_sendgrid",
                          "error": str(exc)}))
        return False


async def _send_email_via_mailgun(to_email: str, subject: str, html: str, env) -> bool:
    """Send a transactional email via the Mailgun Messages API using js.fetch.

    Authentication: HTTP Basic with username "api" and MAILGUN_API_KEY as password.
    Endpoint: https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages
    Body: application/x-www-form-urlencoded
    """
    api_key   = (
        getattr(env, "MAILGUN_SENDING_KEY", "")
        or getattr(env, "mailgun_sending_key", "")
        or getattr(env, "MAILGUN_API_KEY", "")
        or getattr(env, "mailgun_api_key", "")
        or ""
    ).strip()
    domain    = (getattr(env, "MAILGUN_DOMAIN", "") or getattr(env, "mailgun_domain", "") or "").strip()
    api_base  = (getattr(env, "MAILGUN_API_BASE", "") or getattr(env, "mailgun_api_base", "") or "https://api.mailgun.net/v3").strip().rstrip("/")
    if not re.search(r"/v\d+$", api_base):
        api_base += "/v3"
    from_addr = (
        getattr(env, "EMAIL_FROM", "")
        or getattr(env, "DEFAULT_FROM_EMAIL", "")
        or "info@alphaonelabs.com"
    ).strip()

    if not api_key or not domain:
        print(json.dumps({"level": "warn", "where": "_send_email_via_mailgun",
                          "msg": "MAILGUN_API_KEY or MAILGUN_DOMAIN not configured — email not sent"}))
        return False

    endpoint    = f"{api_base}/{domain}/messages"
    credentials = base64.b64encode(f"api:{api_key}".encode()).decode()
    body        = urlencode({
        "from":    from_addr,
        "to":      to_email,
        "subject": subject,
        "html":    html,
    })

    try:
        options = to_js(
            {
                "method": "POST",
                "headers": {
                    "Content-Type":  "application/x-www-form-urlencoded",
                    "Authorization": f"Basic {credentials}",
                },
                "body": body,
            },
            dict_converter=js.Object.fromEntries,
        )
        resp = await js.fetch(endpoint, options)
        if resp.status not in (200, 201):
            body_text = await resp.text()
            print(json.dumps({"level": "warn", "where": "_send_email_via_mailgun",
                              "status": resp.status, "body": body_text[:300]}))
            return False
        return True
    except Exception as exc:
        print(json.dumps({"level": "error", "where": "_send_email_via_mailgun",
                          "error": str(exc)}))
        return False


async def _send_email(to_email: str, subject: str, html: str, env) -> bool:
    """Send through the configured transactional email provider.

    Prefer SendGrid because the legacy environment carries SENDGRID_API_KEY.
    Fall back to Mailgun only when Mailgun credentials are present.
    """
    has_sendgrid = bool((getattr(env, "SENDGRID_API_KEY", "") or getattr(env, "sendgrid_api_key", "") or "").strip())
    has_mailgun = bool(
        (
            getattr(env, "MAILGUN_SENDING_KEY", "")
            or getattr(env, "mailgun_sending_key", "")
            or getattr(env, "MAILGUN_API_KEY", "")
            or getattr(env, "mailgun_api_key", "")
            or ""
        ).strip()
        and (getattr(env, "MAILGUN_DOMAIN", "") or getattr(env, "mailgun_domain", "") or "").strip()
    )

    if has_mailgun:
        if await _send_email_via_mailgun(to_email, subject, html, env):
            return True
        if not has_sendgrid:
            return False
    if has_sendgrid and await _send_email_via_sendgrid(to_email, subject, html, env):
        return True

    print(json.dumps({"level": "warn", "where": "_send_email",
                      "msg": "SENDGRID_API_KEY or Mailgun credentials not configured; email not sent"}))
    return False


def _frontend_url(env, req=None) -> str:
    if req:
        parsed = urlparse(req.url)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    configured = (
        getattr(env, "FRONTEND_URL", "")
        or getattr(env, "PUBLIC_BASE_URL", "")
        or getattr(env, "SITE_URL", "")
        or ""
    ).strip().rstrip("/")
    if configured:
        return configured
    return "https://learn.info-cloudflare139.workers.dev"


def _branded_email_html(frontend_url: str, title: str, intro: str, cta_label: str, link: str, note: str) -> str:
    logo = f"{frontend_url.rstrip('/')}/images/logo.png"
    return (
        '<!DOCTYPE html><html><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1.0"></head>'
        '<body style="margin:0;background:#f8fafc;color:#0f172a;font-family:Segoe UI,Helvetica,Arial,sans-serif;">'
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f8fafc;padding:28px 12px;">'
        '<tr><td align="center">'
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px;background:#ffffff;border:1px solid #e2e8f0;border-radius:20px;overflow:hidden;">'
        '<tr><td style="background:linear-gradient(135deg,#0f766e,#0891b2);padding:28px;text-align:center;color:#ffffff;">'
        f'<img src="{logo}" alt="Alpha One Labs" width="56" height="56" style="width:56px;height:56px;border-radius:12px;background:#ffffff;padding:6px;margin-bottom:12px;">'
        '<div style="font-size:22px;font-weight:800;letter-spacing:.01em;">Alpha One Labs</div>'
        '<div style="font-size:13px;color:#ccfbf1;margin-top:4px;">Open Source Education Platform</div>'
        '</td></tr>'
        '<tr><td style="padding:32px;">'
        f'<h1 style="font-size:26px;line-height:1.2;margin:0 0 16px;color:#0f172a;">{title}</h1>'
        f'<p style="font-size:16px;line-height:1.6;margin:0 0 24px;color:#334155;">{intro}</p>'
        f'<p style="margin:0 0 24px;"><a href="{link}" style="display:inline-block;background:#f97316;color:#ffffff;text-decoration:none;font-weight:700;padding:13px 20px;border-radius:12px;">{cta_label}</a></p>'
        f'<p style="font-size:13px;line-height:1.5;color:#64748b;margin:0 0 20px;">If the button does not work, copy and paste this link:<br><a href="{link}" style="color:#0f766e;word-break:break-all;">{link}</a></p>'
        f'<p style="font-size:13px;line-height:1.5;color:#64748b;margin:0;">{note}</p>'
        '</td></tr>'
        '<tr><td style="border-top:1px solid #e2e8f0;padding:18px 32px;text-align:center;font-size:12px;color:#94a3b8;">'
        'Thank you for using Alpha One Labs.<br>alphaonelabs.com'
        '</td></tr></table></td></tr></table></body></html>'
    )


async def send_verification_email(to_email: str, username: str, token: str, env, req=None) -> bool:
    """Send an email address verification link."""
    frontend_url = _frontend_url(env, req)
    link    = f"{frontend_url}/verify-email?token={token}"
    subject = "[alphaonelabs.com] Please Confirm Your Email Address"
    safe_username = username.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    email_html = _branded_email_html(
        frontend_url,
        "Confirm your email address",
        f"You are receiving this email because <strong>{safe_username}</strong> registered an Alpha One Labs account with this address.",
        "Confirm email",
        link,
        "This link expires in 24 hours. If you did not create an account, you can safely ignore this email.",
    )
    return await _send_email(to_email, subject, email_html, env)


async def send_password_reset_email(to_email: str, _username: str, token: str, env, req=None) -> bool:
    """Send a password reset link."""
    frontend_url = _frontend_url(env, req)
    link    = f"{frontend_url}/reset-password?token={token}"
    subject = "[alphaonelabs.com] Reset Your Password"
    email_html = _branded_email_html(
        frontend_url,
        "Reset your password",
        "We received a request to reset the password for your Alpha One Labs account.",
        "Reset password",
        link,
        "This link expires in 1 hour. If you did not request a password reset, you can safely ignore this email.",
    )
    return await _send_email(to_email, subject, email_html, env)


# ---------------------------------------------------------------------------
# DDL - full schema (mirrors schema.sql)
# ---------------------------------------------------------------------------

_DDL = [
    # Users - all PII encrypted; HMAC blind indexes for O(1) lookups
    """CREATE TABLE IF NOT EXISTS users (
        id             TEXT PRIMARY KEY,
        username_hash  TEXT NOT NULL UNIQUE,
        email_hash     TEXT NOT NULL UNIQUE,
        name           TEXT NOT NULL,
        username       TEXT NOT NULL,
        email          TEXT NOT NULL,
        password_hash  TEXT NOT NULL,
        role           TEXT NOT NULL,
        email_verified INTEGER NOT NULL DEFAULT 0,
        created_at     TEXT NOT NULL DEFAULT (datetime('now'))
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
    # Notifications
    """CREATE TABLE IF NOT EXISTS notifications (
        id         TEXT PRIMARY KEY,
        user_id    TEXT NOT NULL,
        type       TEXT NOT NULL,
        title      TEXT NOT NULL,
        message    TEXT NOT NULL,
        is_read    INTEGER NOT NULL DEFAULT 0,
        related_id TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )""",
    "CREATE INDEX IF NOT EXISTS idx_notif_user   ON notifications(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_notif_unread  ON notifications(user_id, is_read)",
    "CREATE INDEX IF NOT EXISTS idx_notif_created ON notifications(user_id, created_at DESC)",
    # Notification preferences
    """CREATE TABLE IF NOT EXISTS notification_preferences (
        user_id           TEXT PRIMARY KEY,
        enrollment_notify INTEGER NOT NULL DEFAULT 1,
        session_notify    INTEGER NOT NULL DEFAULT 1,
        system_notify     INTEGER NOT NULL DEFAULT 1,
        updated_at        TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )""",
    # Email verification tokens (token_hash = SHA-256 of plaintext token)
    """CREATE TABLE IF NOT EXISTS email_verification_tokens (
        id         TEXT PRIMARY KEY,
        user_id    TEXT NOT NULL,
        token_hash TEXT NOT NULL UNIQUE,
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )""",
    "CREATE INDEX IF NOT EXISTS idx_evtoken_user ON email_verification_tokens(user_id)",
    # Password reset tokens (token_hash = SHA-256 of plaintext token)
    """CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id         TEXT PRIMARY KEY,
        user_id    TEXT NOT NULL,
        token_hash TEXT NOT NULL UNIQUE,
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )""",
    "CREATE INDEX IF NOT EXISTS idx_prtoken_user ON password_reset_tokens(user_id)",
]


async def init_db(env):
    for sql in _DDL:
        await env.DB.prepare(sql).run()
    # Idempotent migration: add email_verified to existing users table.
    # Fails silently when the column already exists (second run is a no-op).
    try:
        await env.DB.prepare(
            "ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0"
        ).run()
        # Pre-existing accounts are treated as verified (registered before this feature).
        await env.DB.prepare("UPDATE users SET email_verified=1").run()
        print("[init_db] email_verified column added successfully")
    except Exception as e:
        print(f"[init_db] email_verified migration skipped (likely already exists): {e}")

    legacy_alters = [
        "ALTER TABLE users ADD COLUMN legacy_user_id TEXT",
        "ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE users ADD COLUMN is_staff INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE users ADD COLUMN last_login TEXT",
        "ALTER TABLE activities ADD COLUMN legacy_course_id TEXT",
        "ALTER TABLE activities ADD COLUMN slug TEXT",
        "ALTER TABLE activities ADD COLUMN image_url TEXT",
        "ALTER TABLE activities ADD COLUMN image_r2_key TEXT",
        "ALTER TABLE activities ADD COLUMN learning_objectives TEXT",
        "ALTER TABLE activities ADD COLUMN prerequisites TEXT",
        "ALTER TABLE activities ADD COLUMN price_cents INTEGER",
        "ALTER TABLE activities ADD COLUMN price_currency TEXT NOT NULL DEFAULT 'USD'",
        "ALTER TABLE activities ADD COLUMN max_students INTEGER",
        "ALTER TABLE activities ADD COLUMN invite_only INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE activities ADD COLUMN allow_individual_sessions INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE activities ADD COLUMN status TEXT NOT NULL DEFAULT 'published'",
        "ALTER TABLE activities ADD COLUMN subject_id TEXT",
        "ALTER TABLE activities ADD COLUMN level TEXT",
        "ALTER TABLE activities ADD COLUMN is_featured INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE activities ADD COLUMN legacy_metadata TEXT",
        "ALTER TABLE sessions ADD COLUMN legacy_session_id TEXT",
        "ALTER TABLE sessions ADD COLUMN legacy_metadata TEXT",
        "ALTER TABLE enrollments ADD COLUMN legacy_enrollment_id TEXT",
        "ALTER TABLE enrollments ADD COLUMN completion_date TEXT",
        "ALTER TABLE enrollments ADD COLUMN legacy_metadata TEXT",
        "ALTER TABLE session_attendance ADD COLUMN legacy_attendance_id TEXT",
        "ALTER TABLE session_attendance ADD COLUMN notes TEXT",
        "ALTER TABLE session_attendance ADD COLUMN legacy_metadata TEXT",
        "ALTER TABLE session_attendance ADD COLUMN updated_at TEXT",
        "ALTER TABLE notifications ADD COLUMN legacy_notification_id TEXT",
        "ALTER TABLE user_profiles ADD COLUMN referral_code_hash TEXT",
    ]
    for sql in legacy_alters:
        try:
            await env.DB.prepare(sql).run()
        except Exception:
            pass

    legacy_tables = [
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_legacy_user_id ON users(legacy_user_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_activities_legacy_course_id ON activities(legacy_course_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_activities_slug ON activities(slug)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_legacy_session_id ON sessions(legacy_session_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_enrollments_legacy_enrollment_id ON enrollments(legacy_enrollment_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_session_attendance_legacy_attendance_id ON session_attendance(legacy_attendance_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_notifications_legacy_notification_id ON notifications(legacy_notification_id)",
        """CREATE TABLE IF NOT EXISTS subjects (
            id                TEXT PRIMARY KEY,
            legacy_subject_id TEXT UNIQUE,
            name              TEXT NOT NULL,
            slug              TEXT UNIQUE,
            description       TEXT,
            icon              TEXT,
            display_order     INTEGER NOT NULL DEFAULT 0,
            created_at        TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at        TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS user_profiles (
            user_id                  TEXT PRIMARY KEY,
            legacy_profile_id         TEXT UNIQUE,
            bio                       TEXT,
            expertise                 TEXT,
            avatar_url                TEXT,
            avatar_r2_key             TEXT,
            discord_username          TEXT,
            slack_username            TEXT,
            github_username           TEXT,
            referral_code             TEXT,
            referral_code_hash        TEXT,
            referred_by_user_id       TEXT,
            referral_earnings_cents   INTEGER,
            stripe_account_id         TEXT,
            stripe_account_status     TEXT,
            commission_rate           TEXT,
            is_teacher                INTEGER NOT NULL DEFAULT 0,
            is_social_media_manager   INTEGER NOT NULL DEFAULT 0,
            is_profile_public         INTEGER NOT NULL DEFAULT 0,
            how_did_you_hear_about_us TEXT,
            created_at                TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at                TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS activity_materials (
            id                  TEXT PRIMARY KEY,
            legacy_material_id  TEXT UNIQUE,
            activity_id          TEXT NOT NULL,
            session_id           TEXT,
            title                TEXT NOT NULL,
            description          TEXT,
            material_type        TEXT,
            file_url             TEXT,
            file_r2_key          TEXT,
            external_url         TEXT,
            display_order        INTEGER NOT NULL DEFAULT 0,
            is_downloadable      INTEGER NOT NULL DEFAULT 0,
            requires_enrollment  INTEGER NOT NULL DEFAULT 1,
            due_date             TEXT,
            created_at           TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at           TEXT,
            legacy_metadata      TEXT,
            FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
            FOREIGN KEY (session_id)  REFERENCES sessions(id) ON DELETE SET NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_activity_materials_activity ON activity_materials(activity_id)",
        "CREATE INDEX IF NOT EXISTS idx_activity_materials_session ON activity_materials(session_id)",
        """CREATE TABLE IF NOT EXISTS legacy_records (
            id           TEXT PRIMARY KEY,
            legacy_model TEXT NOT NULL,
            legacy_pk    TEXT NOT NULL,
            user_id      TEXT,
            activity_id  TEXT,
            payload      TEXT NOT NULL,
            created_at   TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE (legacy_model, legacy_pk)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_legacy_records_model ON legacy_records(legacy_model)",
        "CREATE INDEX IF NOT EXISTS idx_legacy_records_user ON legacy_records(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_legacy_records_activity ON legacy_records(activity_id)",
        """CREATE TABLE IF NOT EXISTS legacy_migration_runs (
            id          TEXT PRIMARY KEY,
            source_host TEXT,
            started_at  TEXT NOT NULL DEFAULT (datetime('now')),
            finished_at TEXT,
            stats       TEXT,
            notes       TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS activity_carts (
            id         TEXT PRIMARY KEY,
            user_id    TEXT,
            guest_id   TEXT NOT NULL DEFAULT '',
            owner_kind TEXT NOT NULL DEFAULT 'user',
            status     TEXT NOT NULL DEFAULT 'open',
            currency   TEXT NOT NULL DEFAULT 'USD',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )""",
        "CREATE INDEX IF NOT EXISTS idx_activity_carts_user_status ON activity_carts(user_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_activity_carts_guest_status ON activity_carts(guest_id, status)",
        """CREATE TABLE IF NOT EXISTS activity_cart_items (
            id               TEXT PRIMARY KEY,
            cart_id          TEXT NOT NULL,
            activity_id      TEXT NOT NULL,
            session_id       TEXT NOT NULL DEFAULT '',
            quantity         INTEGER NOT NULL DEFAULT 1,
            unit_price_cents INTEGER NOT NULL DEFAULT 0,
            title_snapshot   TEXT NOT NULL DEFAULT '',
            created_at       TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at       TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE (cart_id, activity_id, session_id),
            FOREIGN KEY (cart_id)     REFERENCES activity_carts(id) ON DELETE CASCADE,
            FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE
        )""",
        "CREATE INDEX IF NOT EXISTS idx_activity_cart_items_cart ON activity_cart_items(cart_id)",
        "CREATE INDEX IF NOT EXISTS idx_activity_cart_items_activity ON activity_cart_items(activity_id)",
        """CREATE TABLE IF NOT EXISTS activity_checkout_sessions (
            id                TEXT PRIMARY KEY,
            user_id           TEXT,
            guest_id          TEXT NOT NULL DEFAULT '',
            owner_kind        TEXT NOT NULL DEFAULT 'user',
            cart_id           TEXT NOT NULL,
            stripe_session_id TEXT NOT NULL UNIQUE,
            status            TEXT NOT NULL DEFAULT 'pending',
            amount_total      INTEGER NOT NULL DEFAULT 0,
            currency          TEXT NOT NULL DEFAULT 'USD',
            guest_email       TEXT,
            created_at        TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at      TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (cart_id) REFERENCES activity_carts(id) ON DELETE CASCADE
        )""",
        "CREATE INDEX IF NOT EXISTS idx_activity_checkout_sessions_user ON activity_checkout_sessions(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_activity_checkout_sessions_guest ON activity_checkout_sessions(guest_id)",
        "CREATE INDEX IF NOT EXISTS idx_activity_checkout_sessions_cart ON activity_checkout_sessions(cart_id)",
        "CREATE INDEX IF NOT EXISTS idx_user_profiles_referral_code_hash ON user_profiles(referral_code_hash)",
        "CREATE INDEX IF NOT EXISTS idx_user_profiles_referred_by ON user_profiles(referred_by_user_id)",
        """CREATE TABLE IF NOT EXISTS learning_intents (
            id          TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL,
            kind        TEXT NOT NULL,
            title       TEXT NOT NULL,
            subject     TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            status      TEXT NOT NULL DEFAULT 'open',
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )""",
        "CREATE INDEX IF NOT EXISTS idx_learning_intents_kind_status ON learning_intents(kind, status)",
        "CREATE INDEX IF NOT EXISTS idx_learning_intents_user ON learning_intents(user_id)",
        """CREATE TABLE IF NOT EXISTS activity_completions (
            id           TEXT PRIMARY KEY,
            activity_id  TEXT NOT NULL,
            user_id      TEXT NOT NULL,
            kind         TEXT NOT NULL DEFAULT 'completed',
            completed_at TEXT NOT NULL DEFAULT (datetime('now')),
            notes        TEXT NOT NULL DEFAULT '',
            UNIQUE(activity_id, user_id, kind),
            FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )""",
        "CREATE INDEX IF NOT EXISTS idx_activity_completions_user ON activity_completions(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_activity_completions_activity ON activity_completions(activity_id)",
        """CREATE TABLE IF NOT EXISTS activity_interest (
            id          TEXT PRIMARY KEY,
            activity_id TEXT NOT NULL,
            user_id     TEXT NOT NULL,
            message     TEXT NOT NULL DEFAULT '',
            status      TEXT NOT NULL DEFAULT 'interested',
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(activity_id, user_id),
            FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )""",
        "CREATE INDEX IF NOT EXISTS idx_activity_interest_activity ON activity_interest(activity_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_activity_interest_user ON activity_interest(user_id)",
        """CREATE TABLE IF NOT EXISTS donation_checkout_sessions (
            id                TEXT PRIMARY KEY,
            user_id           TEXT,
            stripe_session_id TEXT NOT NULL UNIQUE,
            status            TEXT NOT NULL DEFAULT 'pending',
            amount_total      INTEGER NOT NULL DEFAULT 0,
            currency          TEXT NOT NULL DEFAULT 'USD',
            message           TEXT NOT NULL DEFAULT '',
            created_at        TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at      TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_donation_checkout_sessions_user ON donation_checkout_sessions(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_donation_checkout_sessions_stripe ON donation_checkout_sessions(stripe_session_id)",
        """CREATE TABLE IF NOT EXISTS feedback_messages (
            id         TEXT PRIMARY KEY,
            user_id    TEXT,
            name       TEXT NOT NULL DEFAULT '',
            email      TEXT NOT NULL DEFAULT '',
            message    TEXT NOT NULL,
            status     TEXT NOT NULL DEFAULT 'new',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_feedback_messages_status ON feedback_messages(status, created_at)",
    ]
    for sql in legacy_tables:
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
                "(id,username_hash,email_hash,name,username,email,password_hash,role,email_verified)"
                " VALUES (?,?,?,?,?,?,?,?,?)"
            ).bind(
                uid,
                blind_index(uname, enc_key),
                blind_index(email, enc_key),
                await encrypt_aes(display,  enc_key),
                await encrypt_aes(uname,    enc_key),
                await encrypt_aes(email,    enc_key),
                hash_password(pw, uname),
                await encrypt_aes(role,     enc_key),
                1,
            ).run()
        except Exception:
            pass
        # Ensure existing seed users are always marked as verified
        try:
            await env.DB.prepare(
                "UPDATE users SET email_verified=1 WHERE id=?"
            ).bind(uid).run()
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
            "study_group", "hybrid", "recurring", bid,
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
    referral_code = (body.get("referral_code") or "").strip()

    if not username or not email or not password:
        return err("username, email, and password are required")
    if len(password) < 8:
        return err("Password must be at least 8 characters")

    role = "member"

    enc = env.ENCRYPTION_KEY
    referred_by_user_id = ""
    if referral_code:
        referred_by_user_id = await _referrer_user_id_for_code(env, enc, referral_code)
        if not referred_by_user_id:
            return err("Invalid referral code. Please check and try again.", 400)
    uid = new_id()
    try:
        await env.DB.prepare(
            "INSERT INTO users "
            "(id,username_hash,email_hash,name,username,email,password_hash,role,email_verified)"
            " VALUES (?,?,?,?,?,?,?,?,?)"
        ).bind(
            uid,
            blind_index(username, enc),
            blind_index(email,    enc),
            await encrypt_aes(name,     enc),
            await encrypt_aes(username, enc),
            await encrypt_aes(email,    enc),
            hash_password(password, username),
            await encrypt_aes(role, enc),
            0,
        ).run()
    except Exception as e:
        if "UNIQUE" in str(e):
            return err("Username or email already registered", 409)
        await capture_exception(e, req, env, "api_register.insert_user")
        return err("Registration failed — please try again", 500)

    await _seed_notification_preferences(env, uid)
    try:
        await _ensure_user_profile(env, uid, enc, referred_by_user_id)
    except Exception as e:
        await capture_exception(e, req, env, "api_register.create_profile")
        try:
            await env.DB.prepare("DELETE FROM users WHERE id=?").bind(uid).run()
        except Exception:
            pass
        return err("Registration failed — please try again", 500)

    # Generate email verification token (single-use, 24-hour expiry)
    v_token    = generate_secure_token()
    v_hash     = hash_token(v_token)
    v_id       = new_id()
    expires_at = (
        datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
    ).strftime("%Y-%m-%d %H:%M:%S")
    try:
        await env.DB.prepare(
            "INSERT INTO email_verification_tokens (id,user_id,token_hash,expires_at)"
            " VALUES (?,?,?,?)"
        ).bind(v_id, uid, v_hash, expires_at).run()
    except Exception as e:
        await capture_exception(e, req, env, "api_register.insert_verification_token")
        # Compensating rollback: remove the just-created user so the caller can retry.
        try:
            await env.DB.prepare("DELETE FROM users WHERE id=?").bind(uid).run()
        except Exception:
            pass
        return err("Registration failed — please try again", 500)

    await send_verification_email(email, username, v_token, env, req)

    return ok(
        None,
        "Registration successful! Please check your email to verify your account before signing in.",
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
        "SELECT id,password_hash,role,name,username,email_verified FROM users WHERE username_hash=?"
    ).bind(u_hash).first()
    if not row:
        e_hash = blind_index(username, enc)
        row = await env.DB.prepare(
            "SELECT id,password_hash,role,name,username,email_verified FROM users WHERE email_hash=?"
        ).bind(e_hash).first()

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

    if not row.email_verified:
        return err(
            "Please verify your email before signing in. "
            "Check your inbox for the verification link.",
            403,
        )

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


async def api_verify_email(req, env):
    """GET /api/verify-email?token=... — consume token and mark account as verified."""
    parsed = urlparse(req.url)
    params = parse_qs(parsed.query)
    token  = (params.get("token") or [None])[0]

    if not token:
        return err("Verification token is required", 400)

    token_hash = hash_token(token)

    try:
        row = await env.DB.prepare(
            "SELECT id, user_id FROM email_verification_tokens"
            " WHERE token_hash=? AND expires_at > datetime('now')"
        ).bind(token_hash).first()
    except Exception as exc:
        await capture_exception(exc, req, env, "api_verify_email.lookup")
        return err("Verification failed — please try again", 500)

    if not row:
        return err("This verification link is invalid or has expired.", 400)

    try:
        await env.DB.prepare(
            "UPDATE users SET email_verified=1 WHERE id=?"
        ).bind(row.user_id).run()
        await env.DB.prepare(
            "DELETE FROM email_verification_tokens WHERE id=?"
        ).bind(row.id).run()
    except Exception as exc:
        await capture_exception(exc, req, env, "api_verify_email.update")
        return err("Verification failed — please try again", 500)

    return ok(None, "Email verified successfully. You can now sign in.")


async def api_resend_verification(req, env):
    """POST /api/resend-verification — issue a fresh verification token for an unverified account."""
    body, bad_resp = await parse_json_object(req)
    if bad_resp:
        return bad_resp

    email = (body.get("email") or "").strip()
    if not email:
        return err("Email address is required")

    # Generic message to prevent account-existence enumeration.
    _GENERIC_OK = "If an unverified account with that email exists, a new verification link has been sent."

    enc        = env.ENCRYPTION_KEY
    email_hash = blind_index(email, enc)

    try:
        user_row = await env.DB.prepare(
            "SELECT id, username, email, email_verified FROM users WHERE email_hash=?"
        ).bind(email_hash).first()
    except Exception as exc:
        await capture_exception(exc, req, env, "api_resend_verification.lookup")
        return ok(None, _GENERIC_OK)

    # Return generic ok if account not found or already verified (no enumeration).
    if not user_row or user_row.email_verified:
        return ok(None, _GENERIC_OK)

    username   = await decrypt_aes(user_row.username, enc)
    real_email = await decrypt_aes(user_row.email,    enc)
    if (not username   or username   == "[decryption error]" or
            not real_email or real_email == "[decryption error]"):
        return ok(None, _GENERIC_OK)

    # Per-account cooldown: abort (fail closed) if the lookup errors or a recent token exists.
    try:
        recent = await env.DB.prepare(
            "SELECT id FROM email_verification_tokens"
            " WHERE user_id=? AND created_at > datetime('now', '-5 minutes')"
        ).bind(user_row.id).first()
        if recent:
            return ok(None, _GENERIC_OK)
    except Exception as exc:
        await capture_exception(exc, req, env, "api_resend_verification.cooldown_check")
        return ok(None, _GENERIC_OK)

    # Replace any existing token so only the latest link is valid.
    try:
        await env.DB.prepare(
            "DELETE FROM email_verification_tokens WHERE user_id=?"
        ).bind(user_row.id).run()
    except Exception:
        pass

    v_token    = generate_secure_token()
    v_hash     = hash_token(v_token)
    v_id       = new_id()
    expires_at = (
        datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
    ).strftime("%Y-%m-%d %H:%M:%S")

    try:
        await env.DB.prepare(
            "INSERT INTO email_verification_tokens (id,user_id,token_hash,expires_at)"
            " VALUES (?,?,?,?)"
        ).bind(v_id, user_row.id, v_hash, expires_at).run()
    except Exception as exc:
        await capture_exception(exc, req, env, "api_resend_verification.insert_token")
        return ok(None, _GENERIC_OK)

    await send_verification_email(real_email, username, v_token, env, req)

    return ok(None, _GENERIC_OK)


async def api_forgot_password(req, env):
    """POST /api/forgot-password — generate and email a password reset link."""
    body, bad_resp = await parse_json_object(req)
    if bad_resp:
        return bad_resp

    email = (body.get("email") or "").strip()
    if not email:
        return err("Email address is required")

    # Always return the same message to prevent account-existence enumeration.
    _GENERIC_OK = "If an account with that email exists, a password reset link has been sent."

    enc        = env.ENCRYPTION_KEY
    email_hash = blind_index(email, enc)

    try:
        user_row = await env.DB.prepare(
            "SELECT id, username, email FROM users WHERE email_hash=?"
        ).bind(email_hash).first()
    except Exception as exc:
        await capture_exception(exc, req, env, "api_forgot_password.lookup")
        return ok(None, _GENERIC_OK)

    if not user_row:
        return ok(None, _GENERIC_OK)

    username   = await decrypt_aes(user_row.username, enc)
    real_email = await decrypt_aes(user_row.email,    enc)
    if (not username   or username   == "[decryption error]" or
            not real_email or real_email == "[decryption error]"):
        return ok(None, _GENERIC_OK)

    # Per-account cooldown: abort (fail closed) if the lookup errors or a recent token exists.
    try:
        recent = await env.DB.prepare(
            "SELECT id FROM password_reset_tokens"
            " WHERE user_id=? AND created_at > datetime('now', '-5 minutes')"
        ).bind(user_row.id).first()
        if recent:
            return ok(None, _GENERIC_OK)
    except Exception as exc:
        await capture_exception(exc, req, env, "api_forgot_password.cooldown_check")
        return ok(None, _GENERIC_OK)

    # Replace any existing reset token for this user (only one active at a time).
    try:
        await env.DB.prepare(
            "DELETE FROM password_reset_tokens WHERE user_id=?"
        ).bind(user_row.id).run()
    except Exception:
        pass

    r_token    = generate_secure_token()
    r_hash     = hash_token(r_token)
    r_id       = new_id()
    expires_at = (
        datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    ).strftime("%Y-%m-%d %H:%M:%S")

    try:
        await env.DB.prepare(
            "INSERT INTO password_reset_tokens (id,user_id,token_hash,expires_at)"
            " VALUES (?,?,?,?)"
        ).bind(r_id, user_row.id, r_hash, expires_at).run()
    except Exception as exc:
        await capture_exception(exc, req, env, "api_forgot_password.insert_token")
        return ok(None, _GENERIC_OK)

    await send_password_reset_email(real_email, username, r_token, env, req)

    return ok(None, _GENERIC_OK)


async def api_reset_password(req, env):
    """POST /api/reset-password — validate token and apply new password hash."""
    body, bad_resp = await parse_json_object(req)
    if bad_resp:
        return bad_resp

    token        = (body.get("token")        or "").strip()
    new_password = (body.get("new_password") or "")

    if not token:
        return err("Reset token is required")
    if len(new_password) < 8:
        return err("Password must be at least 8 characters")

    token_hash = hash_token(token)

    try:
        row = await env.DB.prepare(
            "SELECT id, user_id FROM password_reset_tokens"
            " WHERE token_hash=? AND expires_at > datetime('now')"
        ).bind(token_hash).first()
    except Exception as exc:
        await capture_exception(exc, req, env, "api_reset_password.lookup")
        return err("Password reset failed — please try again", 500)

    if not row:
        return err("This reset link is invalid or has expired.", 400)

    enc = env.ENCRYPTION_KEY
    try:
        user_row = await env.DB.prepare(
            "SELECT username FROM users WHERE id=?"
        ).bind(row.user_id).first()
    except Exception as exc:
        await capture_exception(exc, req, env, "api_reset_password.get_user")
        return err("Password reset failed — please try again", 500)

    if not user_row:
        return err("Account not found", 404)

    username = await decrypt_aes(user_row.username, enc)
    if not username or username == "[decryption error]":
        return err("Password reset failed — please try again", 500)

    new_hash = hash_password(new_password, username)

    try:
        await env.DB.prepare(
            "UPDATE users SET password_hash=?, email_verified=1 WHERE id=?"
        ).bind(new_hash, row.user_id).run()
        await env.DB.prepare(
            "DELETE FROM password_reset_tokens WHERE id=?"
        ).bind(row.id).run()
    except Exception as exc:
        await capture_exception(exc, req, env, "api_reset_password.update")
        return err("Password reset failed — please try again", 500)

    return ok(None, "Password reset successfully. You can now sign in with your new password.")


async def api_list_activities(req, env):
    parsed = urlparse(req.url)
    params = parse_qs(parsed.query)
    atype  = (params.get("type")   or [None])[0]
    fmt    = (params.get("format") or [None])[0]
    search = (params.get("q")      or [None])[0]
    tag    = (params.get("tag")    or [None])[0]
    status = (params.get("status") or ["catalog"])[0]
    if status not in {"catalog", "published", "waitlist", "draft", "archived", "all"}:
        status = "catalog"
    enc    = env.ENCRYPTION_KEY
    page_raw = (params.get("page") or [None])[0]
    page_size_raw = (params.get("page_size") or [None])[0]
    try:
        page = max(1, int(page_raw or 1))
    except Exception:
        page = 1
    try:
        page_size = max(1, min(100, int(page_size_raw))) if page_size_raw else None
    except Exception:
        page_size = None

    base_q = (
        "SELECT a.id,a.title,a.description,a.type,a.format,a.schedule_type,"
        "a.created_at,a.status,a.slug,a.image_url,a.price_cents,a.price_currency,"
        "a.max_students,a.level,a.is_featured,u.name AS host_name_enc,"
        "(SELECT COUNT(*) FROM enrollments WHERE activity_id=a.id AND status='active')"
        " AS participant_count,"
        "(SELECT COUNT(*) FROM activity_interest WHERE activity_id=a.id AND status='interested')"
        " AS interest_count,"
        "(SELECT COUNT(*) FROM sessions WHERE activity_id=a.id) AS session_count"
        " FROM activities a JOIN users u ON a.host_id=u.id"
    )

    async def fetch_activities():
        join = ""
        clauses = []
        binds = []
        if tag:
            tag_row = await env.DB.prepare(
                "SELECT id FROM tags WHERE name=?"
            ).bind(tag).first()
            if not tag_row:
                return _empty_d1_result()
            join = " JOIN activity_tags at2 ON at2.activity_id=a.id"
            clauses.append("at2.tag_id=?")
            binds.append(tag_row.id)
        if status == "catalog":
            clauses.append("COALESCE(a.status,'published') IN ('published','waitlist')")
        elif status != "all":
            clauses.append("a.status=?")
            binds.append(status)
        if atype:
            clauses.append("a.type=?")
            binds.append(atype)
        if fmt:
            clauses.append("a.format=?")
            binds.append(fmt)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        stmt = env.DB.prepare(base_q + join + where + " ORDER BY a.created_at DESC")
        return await stmt.bind(*binds).all() if binds else await stmt.all()

    try:
        res = await fetch_activities()
    except Exception as e:
        if not _is_no_such_table_error(e):
            raise
        await init_db(env)
        res = await fetch_activities()

    rows = list(res.results or [])
    tag_map = {}
    if rows:
        try:
            placeholders = ",".join(["?"] * len(rows))
            tag_res = await env.DB.prepare(
                "SELECT at2.activity_id,t.name FROM tags t"
                " JOIN activity_tags at2 ON at2.tag_id=t.id"
                f" WHERE at2.activity_id IN ({placeholders})"
            ).bind(*[row.id for row in rows]).all()
            for tag_row in tag_res.results or []:
                tag_map.setdefault(tag_row.activity_id, []).append(tag_row.name)
        except Exception:
            tag_map = {}

    activities = []
    search_l = (search or "").lower()
    for row in rows:
        desc      = await decrypt_aes(row.description or "", enc)
        host_name = await decrypt_aes(row.host_name_enc or "", enc)
        if search_l and (
            search_l not in (row.title or "").lower()
            and search_l not in (desc or "").lower()
        ):
            continue

        activities.append({
            "id":                row.id,
            "title":             row.title,
            "description":       desc,
            "type":              row.type,
            "format":            row.format,
            "schedule_type":     row.schedule_type,
            "status":            getattr(row, "status", "published"),
            "slug":              getattr(row, "slug", "") or "",
            "image_url":         getattr(row, "image_url", "") or "",
            "price_cents":       int(getattr(row, "price_cents", 0) or 0),
            "price_currency":    getattr(row, "price_currency", "USD") or "USD",
            "max_students":      getattr(row, "max_students", 0) or 0,
            "level":             getattr(row, "level", "") or "",
            "is_featured":       bool(getattr(row, "is_featured", 0)),
            "host_name":         host_name,
            "participant_count": row.participant_count,
            "interest_count":    int(getattr(row, "interest_count", 0) or 0),
            "session_count":     row.session_count,
            "tags":              tag_map.get(row.id, []),
            "created_at":        row.created_at,
        })

    total = len(activities)
    if page_size:
        total_pages = max(1, (total + page_size - 1) // page_size)
        if page > total_pages:
            page = total_pages
        start = (page - 1) * page_size
        activities = activities[start:start + page_size]
    else:
        total_pages = 1

    return json_resp({
        "activities": activities,
        "pagination": {
            "page": page,
            "page_size": page_size or total,
            "total": total,
            "total_pages": total_pages,
        },
    })


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
    if atype not in ("course", "meetup", "workshop", "seminar", "club", "event", "video", "study_group", "other"):
        atype = "course"
    if fmt not in ("live", "self_paced", "hybrid"):
        fmt = "self_paced"
    if schedule_type not in ("one_time", "multi_session", "recurring", "ongoing"):
        schedule_type = "ongoing"

    enc    = env.ENCRYPTION_KEY
    act_id = new_id()
    slug   = await _unique_activity_slug(env, title, act_id)
    try:
        await env.DB.prepare(
            "INSERT INTO activities "
            "(id,title,description,type,format,schedule_type,host_id,slug)"
            " VALUES (?,?,?,?,?,?,?,?)"
        ).bind(
            act_id, title,
            await encrypt_aes(description, enc) if description else "",
            atype, fmt, schedule_type, user["id"], slug
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

    await emit_event(env, "ACTIVITY_CREATED", {
        "user_id": user["id"], "activity_id": act_id, "title": title,
    })

    return ok({"id": act_id, "slug": slug, "title": title}, "Activity created")


async def api_classes_near_me(req, env):
    params = parse_qs(urlparse(req.url).query)
    requested_zip = ((params.get("zip") or [""])[0] or "").strip()[:32]
    near_requested = ((params.get("near") or [""])[0] or "").strip().lower() in ("1", "true", "yes", "on")
    detected_zip = _get_request_postal_code(req) if near_requested and not requested_zip else ""
    zip_filter = requested_zip or detected_zip

    if near_requested and not zip_filter:
        return json_resp({
            "classes": [],
            "zip": "",
            "detected_zip": "",
            "location_lookup_failed": True,
        })

    res = await env.DB.prepare(
        "SELECT a.id AS activity_id,a.title,a.type,a.format AS activity_format,"
        " a.schedule_type,a.slug,a.image_url,a.price_cents,a.price_currency,"
        " a.level,a.created_at,s.id AS session_id,s.location AS session_location"
        " FROM activities a"
        " JOIN sessions s ON s.activity_id=a.id"
        " WHERE COALESCE(a.status,'published')='published'"
        " AND s.location IS NOT NULL AND trim(s.location)<>''"
        " ORDER BY a.created_at DESC,s.start_time"
    ).all()

    classes_by_id = {}
    class_order = []
    for row in res.results or []:
        encrypted_location = getattr(row, "session_location", "") or ""
        try:
            location = await decrypt_aes(encrypted_location, env.ENCRYPTION_KEY)
        except Exception:
            location = encrypted_location if not str(encrypted_location).startswith("v1:") else ""

        zip_codes = _extract_location_zip_codes(location)
        if not zip_codes or not _location_codes_match(zip_filter, zip_codes):
            continue

        activity_id = getattr(row, "activity_id", "") or ""
        if not activity_id:
            continue

        if activity_id not in classes_by_id:
            class_order.append(activity_id)
            classes_by_id[activity_id] = {
                "id": activity_id,
                "title": getattr(row, "title", "") or "",
                "type": getattr(row, "type", "") or "",
                "format": getattr(row, "activity_format", "") or "",
                "schedule_type": getattr(row, "schedule_type", "") or "",
                "slug": getattr(row, "slug", "") or "",
                "image_url": getattr(row, "image_url", "") or "",
                "price_cents": int(getattr(row, "price_cents", 0) or 0),
                "price_currency": getattr(row, "price_currency", "USD") or "USD",
                "level": getattr(row, "level", "") or "",
                "created_at": getattr(row, "created_at", "") or "",
                "zip_codes": [],
                "session_count": 0,
            }

        activity = classes_by_id[activity_id]
        activity["session_count"] += 1
        for code in zip_codes:
            if code not in activity["zip_codes"]:
                activity["zip_codes"].append(code)

    return json_resp({
        "classes": [classes_by_id[activity_id] for activity_id in class_order],
        "zip": zip_filter,
        "detected_zip": detected_zip,
        "location_lookup_failed": False,
    })


async def api_get_activity(activity_ref: str, req, env):
    user    = verify_token(req.headers.get("Authorization") or "", env.JWT_SECRET)
    enc     = env.ENCRYPTION_KEY

    act = await env.DB.prepare(
        "SELECT a.*,u.name AS host_name_enc,u.id AS host_uid"
        " FROM activities a JOIN users u ON a.host_id=u.id"
        " WHERE a.slug=?"
    ).bind(activity_ref).first()
    if not act:
        act = await env.DB.prepare(
            "SELECT a.*,u.name AS host_name_enc,u.id AS host_uid"
            " FROM activities a JOIN users u ON a.host_id=u.id"
            " WHERE a.id=?"
        ).bind(activity_ref).first()
    if not act:
        return err("Activity not found", 404)
    act_id = act.id

    enrollment  = None
    is_enrolled = False
    completion = None
    is_completed = False
    interest = None
    user_interested = False
    if user:
        enrollment  = await env.DB.prepare(
            "SELECT id,role,status FROM enrollments"
            " WHERE activity_id=? AND user_id=?"
        ).bind(act_id, user["id"]).first()
        is_enrolled = enrollment is not None
        completion = await env.DB.prepare(
            "SELECT id,kind,completed_at FROM activity_completions"
            " WHERE activity_id=? AND user_id=? ORDER BY completed_at DESC LIMIT 1"
        ).bind(act_id, user["id"]).first()
        is_completed = completion is not None
        interest = await env.DB.prepare(
            "SELECT id,status,created_at FROM activity_interest"
            " WHERE activity_id=? AND user_id=?"
        ).bind(act_id, user["id"]).first()
        user_interested = interest is not None

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
    interest_count_row = await env.DB.prepare(
        "SELECT COUNT(*) AS cnt FROM activity_interest WHERE activity_id=? AND status='interested'"
    ).bind(act_id).first()

    legacy_metadata = {}
    raw_metadata = await decrypt_aes(getattr(act, "legacy_metadata", "") or "", enc)
    if raw_metadata:
        try:
            parsed_metadata = json.loads(raw_metadata)
            if isinstance(parsed_metadata, dict):
                legacy_metadata = parsed_metadata
        except Exception:
            legacy_metadata = {}

    return json_resp({
        "activity": {
            "id":                act.id,
            "title":             act.title,
            "description":       await decrypt_aes(act.description or "", enc),
            "learning_objectives": await decrypt_aes(getattr(act, "learning_objectives", "") or "", enc),
            "prerequisites":     await decrypt_aes(getattr(act, "prerequisites", "") or "", enc),
            "type":              act.type,
            "format":            act.format,
            "schedule_type":     act.schedule_type,
            "status":            getattr(act, "status", "published"),
            "slug":              getattr(act, "slug", "") or "",
            "image_url":         getattr(act, "image_url", "") or "",
            "price_cents":       int(getattr(act, "price_cents", 0) or 0),
            "price_currency":    getattr(act, "price_currency", "USD") or "USD",
            "max_students":      getattr(act, "max_students", 0) or 0,
            "invite_only":       bool(getattr(act, "invite_only", 0)),
            "allow_individual_sessions": bool(getattr(act, "allow_individual_sessions", 0)),
            "subject_id":        getattr(act, "subject_id", "") or "",
            "level":             getattr(act, "level", "") or "",
            "is_featured":       bool(getattr(act, "is_featured", 0)),
            "external_url":      legacy_metadata.get("video_url") or legacy_metadata.get("external_url") or legacy_metadata.get("url") or "",
            "host_name":         await decrypt_aes(act.host_name_enc or "", enc),
            "participant_count": count_row.cnt if count_row else 0,
            "interest_count":    interest_count_row.cnt if interest_count_row else 0,
            "tags":              [t.name for t in (t_res.results or [])],
            "created_at":        act.created_at,
        },
        "sessions":    sessions,
        "is_enrolled": is_enrolled,
        "is_host":     is_host,
        "is_completed": is_completed,
        "user_interested": user_interested,
        "interest": {
            "status": interest.status,
            "created_at": interest.created_at,
        } if interest else None,
        "completion": {
            "kind": completion.kind,
            "completed_at": completion.completed_at,
        } if completion else None,
        "enrollment":  {
            "role":   enrollment.role,
            "status": enrollment.status,
        } if enrollment else None,
    })


async def api_complete_activity(activity_ref: str, req, env):
    user = verify_token(req.headers.get("Authorization") or "", env.JWT_SECRET)
    if not user:
        return err("Authentication required", 401)

    act = await env.DB.prepare(
        "SELECT id,title,type,host_id FROM activities WHERE slug=? OR id=? LIMIT 1"
    ).bind(activity_ref, activity_ref).first()
    if not act:
        return err("Activity not found", 404)

    if act.host_id != user["id"]:
        enrollment = await env.DB.prepare(
            "SELECT id FROM enrollments WHERE activity_id=? AND user_id=?"
        ).bind(act.id, user["id"]).first()
        if not enrollment:
            return err("Join this activity before marking it complete", 403)

    kind = "watched" if act.type == "video" else "completed"
    completion_id = new_id()
    await env.DB.prepare(
        "INSERT INTO activity_completions (id,activity_id,user_id,kind,completed_at)"
        " VALUES (?,?,?,?,datetime('now'))"
        " ON CONFLICT(activity_id,user_id,kind) DO UPDATE SET completed_at=datetime('now')"
    ).bind(completion_id, act.id, user["id"], kind).run()

    return ok({
        "activity_id": act.id,
        "kind": kind,
    }, "Activity marked " + kind)


async def api_express_activity_interest(activity_ref: str, req, env):
    user = verify_token(req.headers.get("Authorization") or "", env.JWT_SECRET)
    if not user:
        return err("Authentication required", 401)

    body, bad_resp = await parse_json_object(req)
    if bad_resp:
        return bad_resp

    act = await env.DB.prepare(
        "SELECT id,title,host_id FROM activities WHERE slug=? OR id=? LIMIT 1"
    ).bind(activity_ref, activity_ref).first()
    if not act:
        return err("Activity not found", 404)

    message = (body.get("message") or "").strip()[:500]
    interest_id = new_id()
    await env.DB.prepare(
        "INSERT INTO activity_interest (id,activity_id,user_id,message,status,updated_at)"
        " VALUES (?,?,?,?,?,datetime('now'))"
        " ON CONFLICT(activity_id,user_id) DO UPDATE SET"
        " message=excluded.message,status='interested',updated_at=datetime('now')"
    ).bind(
        interest_id,
        act.id,
        user["id"],
        await encrypt_aes(message, env.ENCRYPTION_KEY) if message else "",
        "interested",
    ).run()

    count_row = await env.DB.prepare(
        "SELECT COUNT(*) AS cnt FROM activity_interest WHERE activity_id=? AND status='interested'"
    ).bind(act.id).first()

    await emit_event(env, "ACTIVITY_INTEREST_EXPRESSED", {
        "user_id": user["id"],
        "activity_id": act.id,
        "activity_title": act.title,
        "recipient_ids": [act.host_id],
    })

    return ok({
        "activity_id": act.id,
        "interest_count": count_row.cnt if count_row else 1,
    }, "Interest recorded")


async def api_join(req, env):
    user = verify_token(req.headers.get("Authorization"), env.JWT_SECRET)
    if not user:
        return err("Authentication required", 401)

    body, bad_resp = await parse_json_object(req)
    if bad_resp:
        return bad_resp

    act_id = body.get("activity_id")
    role = (body.get("role") or "participant").strip()

    if not act_id:
        return err("activity_id is required")

    if role not in ("participant", "instructor", "organizer"):
        role = "participant"

    # 1️⃣ Get activity
    act = await env.DB.prepare(
        "SELECT id, title, host_id FROM activities WHERE id=?"
    ).bind(act_id).first()

    if not act:
        return err("Activity not found", 404)

    # ❌ REMOVE existing check completely

    # 2️⃣ Insert enrollment
    enr_id = new_id()
    try:
        insert_res = await env.DB.prepare(
            "INSERT OR IGNORE INTO enrollments (id,activity_id,user_id,role) VALUES (?,?,?,?)"
        ).bind(enr_id, act_id, user["id"], role).run()
    except Exception as e:
        await capture_exception(e, req, env, "api_join.insert_enrollment")
        return err("Failed to join activity — please try again", 500)

    # 3️⃣ Idempotency via changes
    changes = None
    try:
        meta = getattr(insert_res, "meta", None)
        if isinstance(meta, dict):
            changes = meta.get("changes")
        elif meta is not None:
            changes = getattr(meta, "changes", None)
    except Exception:
        pass

    if changes == 0:
        return ok(None, "Already joined this activity")

    # 4️⃣ Participant name
    participant_name = user.get("username") or "Participant"
    host_id = getattr(act, "host_id", None)

    if host_id != user["id"]:
        try:
            u_row = await env.DB.prepare(
                "SELECT name FROM users WHERE id=?"
            ).bind(user["id"]).first()

            if u_row and u_row.name:
                dec_name = await decrypt_aes(u_row.name, env.ENCRYPTION_KEY)
                if dec_name and dec_name != "[decryption error]":
                    participant_name = dec_name
        except Exception:
            pass

    # 5️⃣ Emit notification
    try:
        await emit_event(env, "USER_ENROLLED", {
            "user_id": user["id"],
            "host_id": host_id,
            "activity_id": act_id,
            "activity_title": getattr(act, "title", "Activity"),
            "participant_name": participant_name,
        })
    except Exception:
        pass

    return ok(None, "Joined activity successfully")
async def api_dashboard(req, env):
    user = verify_token(req.headers.get("Authorization"), env.JWT_SECRET)
    if not user:
        return err("Authentication required", 401)

    enc = env.ENCRYPTION_KEY

    res = await env.DB.prepare(
        "SELECT a.id,a.title,a.slug,a.type,a.format,a.schedule_type,a.created_at,"
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
            "slug":              getattr(r, "slug", "") or "",
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
        "SELECT a.id,a.title,a.slug,a.type,a.format,a.schedule_type,"
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
            "slug":          getattr(r, "slug", "") or "",
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


async def api_profile(req, env):
    user = verify_token(req.headers.get("Authorization"), env.JWT_SECRET)
    if not user:
        return err("Authentication required", 401)

    enc = env.ENCRYPTION_KEY
    await _ensure_user_profile(env, user["id"], enc)

    if req.method.upper() == "GET":
        row = await env.DB.prepare(
            "SELECT u.id,u.name,u.username,u.email,u.role,p.bio,p.expertise,p.avatar_url,"
            "p.discord_username,p.slack_username,p.github_username,p.is_teacher,p.is_profile_public,"
            "p.how_did_you_hear_about_us,p.referral_code,p.referral_earnings_cents"
            " FROM users u LEFT JOIN user_profiles p ON p.user_id=u.id WHERE u.id=?"
        ).bind(user["id"]).first()
        if not row:
            return err("Profile not found", 404)
        referral_code = await decrypt_aes(getattr(row, "referral_code", "") or "", enc)
        return json_resp({"profile": {
            "id": row.id,
            "name": await decrypt_aes(row.name or "", enc),
            "username": await decrypt_aes(row.username or "", enc),
            "email": await decrypt_aes(row.email or "", enc),
            "role": row.role,
            "bio": await decrypt_aes(getattr(row, "bio", "") or "", enc),
            "expertise": await decrypt_aes(getattr(row, "expertise", "") or "", enc),
            "avatar_url": getattr(row, "avatar_url", "") or "",
            "discord_username": await decrypt_aes(getattr(row, "discord_username", "") or "", enc),
            "slack_username": await decrypt_aes(getattr(row, "slack_username", "") or "", enc),
            "github_username": await decrypt_aes(getattr(row, "github_username", "") or "", enc),
            "is_teacher": bool(getattr(row, "is_teacher", 0)),
            "is_profile_public": bool(getattr(row, "is_profile_public", 0)),
            "how_did_you_hear_about_us": await decrypt_aes(getattr(row, "how_did_you_hear_about_us", "") or "", enc),
            "referral_code": referral_code if referral_code != "[decryption error]" else "",
            "referral_earnings_cents": int(getattr(row, "referral_earnings_cents", 0) or 0),
        }})

    if req.method.upper() != "PATCH":
        return err("Method not allowed", 405)

    body, bad_resp = await parse_json_object(req)
    if bad_resp:
        return bad_resp

    name = _legacy_text(body.get("name")).strip()[:160]
    bio = _legacy_text(body.get("bio")).strip()[:3000]
    expertise = _legacy_text(body.get("expertise")).strip()[:1000]
    discord_username = _legacy_text(body.get("discord_username")).strip()[:120]
    slack_username = _legacy_text(body.get("slack_username")).strip()[:120]
    github_username = _legacy_text(body.get("github_username")).strip()[:120]
    how_heard = _legacy_text(body.get("how_did_you_hear_about_us")).strip()[:1000]
    is_teacher = 1 if body.get("is_teacher") else 0
    is_public = 1 if body.get("is_profile_public") else 0

    try:
        if name:
            await env.DB.prepare("UPDATE users SET name=? WHERE id=?").bind(
                await encrypt_aes(name, enc), user["id"]
            ).run()
        await env.DB.prepare(
            "UPDATE user_profiles SET bio=?,expertise=?,discord_username=?,slack_username=?,"
            "github_username=?,how_did_you_hear_about_us=?,is_teacher=?,is_profile_public=?,updated_at=datetime('now')"
            " WHERE user_id=?"
        ).bind(
            await encrypt_aes(bio, enc),
            await encrypt_aes(expertise, enc),
            await encrypt_aes(discord_username, enc),
            await encrypt_aes(slack_username, enc),
            await encrypt_aes(github_username, enc),
            await encrypt_aes(how_heard, enc),
            is_teacher,
            is_public,
            user["id"],
        ).run()
    except Exception as exc:
        await capture_exception(exc, req, env, "api_profile.patch")
        return err("Could not update profile", 500)

    return ok(None, "Profile updated")


async def api_delete_account(req, env):
    user = verify_token(req.headers.get("Authorization"), env.JWT_SECRET)
    if not user:
        return err("Authentication required", 401)

    body, bad_resp = await parse_json_object(req)
    if bad_resp:
        return bad_resp
    confirmation = _legacy_text(body.get("confirmation")).strip().upper()
    if confirmation != "DELETE":
        return err("Type DELETE to confirm account deletion", 400)

    enc = env.ENCRYPTION_KEY
    uid = user["id"]
    deleted_label = f"deleted-{uid[:8]}"
    deleted_email = f"deleted-{uid}@alphaonelabs.invalid"
    try:
        cart_rows = await env.DB.prepare("SELECT id FROM activity_carts WHERE user_id=?").bind(uid).all()
        for cart in cart_rows.results or []:
            await env.DB.prepare("DELETE FROM activity_cart_items WHERE cart_id=?").bind(cart.id).run()

        cleanup_sql = [
            "DELETE FROM notification_preferences WHERE user_id=?",
            "DELETE FROM notifications WHERE user_id=?",
            "DELETE FROM email_verification_tokens WHERE user_id=?",
            "DELETE FROM password_reset_tokens WHERE user_id=?",
            "DELETE FROM enrollments WHERE user_id=?",
            "DELETE FROM session_attendance WHERE user_id=?",
            "DELETE FROM activity_completions WHERE user_id=?",
            "DELETE FROM activity_interest WHERE user_id=?",
            "DELETE FROM learning_intents WHERE user_id=?",
            "DELETE FROM activity_carts WHERE user_id=?",
            "DELETE FROM activity_checkout_sessions WHERE user_id=?",
            "DELETE FROM feedback_messages WHERE user_id=?",
            "DELETE FROM user_profiles WHERE user_id=?",
        ]
        for sql in cleanup_sql:
            try:
                await env.DB.prepare(sql).bind(uid).run()
            except Exception as cleanup_exc:
                await capture_exception(cleanup_exc, req, env, "api_delete_account.cleanup")
                continue

        try:
            await env.DB.prepare(
                "UPDATE activities SET status='archived' WHERE host_id=? AND status <> 'archived'"
            ).bind(uid).run()
        except Exception:
            pass

        await env.DB.prepare(
            "UPDATE users SET username_hash=?,email_hash=?,name=?,username=?,email=?,password_hash=?,role=?,email_verified=0 WHERE id=?"
        ).bind(
            blind_index(deleted_label, enc),
            blind_index(deleted_email, enc),
            await encrypt_aes("Deleted user", enc),
            await encrypt_aes(deleted_label, enc),
            await encrypt_aes(deleted_email, enc),
            "deleted:" + os.urandom(24).hex(),
            "deleted",
            uid,
        ).run()
    except Exception as exc:
        await capture_exception(exc, req, env, "api_delete_account")
        return err("Could not delete account", 500)

    return ok(None, "Account deleted")


async def api_feedback(req, env):
    if req.method.upper() != "POST":
        return err("Method not allowed", 405)
    user = verify_token(req.headers.get("Authorization") or "", env.JWT_SECRET)
    body, bad_resp = await parse_json_object(req)
    if bad_resp:
        return bad_resp
    name = _legacy_text(body.get("name")).strip()[:160]
    email = _legacy_text(body.get("email")).strip()[:240]
    message = _legacy_text(body.get("message")).strip()
    trap = _legacy_text(body.get("company_website")).strip()
    if trap:
        return ok(None, "Feedback received")
    if not message:
        return err("Feedback message is required")
    if len(message) > 5000:
        return err("Feedback message is too long")

    async def insert_feedback():
        await env.DB.prepare(
            "INSERT INTO feedback_messages (id,user_id,name,email,message) VALUES (?,?,?,?,?)"
        ).bind(
            new_id(),
            user["id"] if user else None,
            await encrypt_aes(name, env.ENCRYPTION_KEY),
            await encrypt_aes(email, env.ENCRYPTION_KEY),
            await encrypt_aes(message, env.ENCRYPTION_KEY),
        ).run()

    try:
        await insert_feedback()
    except Exception as exc:
        if _is_no_such_table_error(exc):
            await init_db(env)
            await insert_feedback()
        else:
            await capture_exception(exc, req, env, "api_feedback")
            return err("Could not save feedback", 500)
    return ok(None, "Thank you for the feedback.")


async def api_get_referral(req, env):
    user = verify_token(req.headers.get("Authorization"), env.JWT_SECRET)
    if not user:
        return err("Authentication required", 401)
    enc = env.ENCRYPTION_KEY
    profile = await _ensure_user_profile(env, user["id"], enc)
    referred = await env.DB.prepare(
        "SELECT COUNT(*) AS cnt FROM user_profiles WHERE referred_by_user_id=?"
    ).bind(user["id"]).first()
    enrolled = await env.DB.prepare(
        "SELECT COUNT(DISTINCT e.id) AS cnt"
        " FROM user_profiles up JOIN enrollments e ON e.user_id=up.user_id"
        " WHERE up.referred_by_user_id=? AND e.status IN ('active','approved','completed')"
    ).bind(user["id"]).first()
    code = profile["referral_code"]
    origin = f"{urlparse(req.url).scheme}://{urlparse(req.url).netloc}"
    return ok({
        "referral_code": code,
        "referral_link": origin + "/ref/" + quote(code, safe=""),
        "referral_earnings_cents": int(profile.get("referral_earnings_cents") or 0),
        "referred_count": int((referred.cnt if referred else 0) or 0),
        "referred_enrollment_count": int((enrolled.cnt if enrolled else 0) or 0),
        "referred_by_user_id": profile.get("referred_by_user_id") or "",
    })


async def api_referral_leaderboard(req, env):
    parsed = urlparse(req.url)
    params = parse_qs(parsed.query)
    try:
        limit = max(1, min(50, int((params.get("limit") or ["10"])[0])))
    except Exception:
        limit = 10

    enc = env.ENCRYPTION_KEY
    res = await env.DB.prepare(
        "SELECT * FROM ("
        " SELECT up.user_id,u.name AS name_enc,"
        " COALESCE(up.referral_earnings_cents,0) AS referral_earnings_cents,"
        " (SELECT COUNT(*) FROM user_profiles child WHERE child.referred_by_user_id=up.user_id) AS referred_count,"
        " (SELECT COUNT(DISTINCT e.id)"
        "    FROM user_profiles child"
        "    JOIN enrollments e ON e.user_id=child.user_id"
        "   WHERE child.referred_by_user_id=up.user_id"
        "     AND e.status IN ('active','approved','completed')) AS referred_enrollment_count"
        " FROM user_profiles up JOIN users u ON u.id=up.user_id"
        ") ranked"
        " WHERE referred_count > 0 OR referred_enrollment_count > 0 OR referral_earnings_cents > 0"
        " ORDER BY referred_count DESC, referred_enrollment_count DESC, referral_earnings_cents DESC"
        " LIMIT ?"
    ).bind(limit).all()

    leaders = []
    for idx, row in enumerate(res.results or [], 1):
        name = await decrypt_aes(getattr(row, "name_enc", "") or "", enc)
        if not name or name == "[decryption error]":
            name = "Alpha One Labs member"
        leaders.append({
            "rank": idx,
            "user_id": row.user_id,
            "name": name,
            "referred_count": int(getattr(row, "referred_count", 0) or 0),
            "referred_enrollment_count": int(getattr(row, "referred_enrollment_count", 0) or 0),
            "referral_earnings_cents": int(getattr(row, "referral_earnings_cents", 0) or 0),
        })

    return json_resp({"leaders": leaders})


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

    act_row = await env.DB.prepare(
        "SELECT title FROM activities WHERE id = ?"
    ).bind(act_id).first()
    recipient_ids = await _activity_enrollee_ids(env, act_id, exclude_user_id=user["id"])
    
    await emit_event(env, "SESSION_CREATED", {
        "session_id":    sid,
        "session_title": title,
        "activity_id":   act_id,
        "activity_title": act_row.title if act_row else act_id,
        "recipient_ids": recipient_ids,
    })

    return ok({"id": sid}, "Session created")


async def api_list_tags(_req, env):
    res  = await env.DB.prepare("SELECT id,name FROM tags ORDER BY name").all()
    tags = [{"id": r.id, "name": r.name} for r in (res.results or [])]
    return json_resp({"tags": tags})


async def api_list_subjects(_req, env):
    enc = env.ENCRYPTION_KEY
    res = await env.DB.prepare(
        "SELECT id,name,slug,description,icon,display_order FROM subjects"
        " ORDER BY display_order ASC, name ASC"
    ).all()
    subjects = []
    for row in res.results or []:
        subjects.append({
            "id": row.id,
            "name": row.name,
            "slug": getattr(row, "slug", "") or "",
            "description": await decrypt_aes(getattr(row, "description", "") or "", enc),
            "icon": getattr(row, "icon", "") or "",
        })
    return json_resp({"subjects": subjects})


LEGACY_FEATURE_GROUPS = {
    "community": {
        "title": "Community",
        "models": [
            "web.ForumCategory", "web.ForumTopic", "web.ForumReply", "web.ForumVote",
            "web.StudyGroup", "web.PeerMessage", "web.BlogPost", "web.SuccessStory",
            "web.Meme", "web.FeatureVote",
        ],
    },
    "assessment": {
        "title": "Assessment",
        "models": [
            "web.Quiz", "web.QuizQuestion", "web.QuizOption", "web.UserQuiz",
            "web.Survey", "web.Question", "web.Choice", "web.Response",
            "web.Achievement",
        ],
    },
    "progress": {
        "title": "Progress",
        "models": [
            "web.CourseProgress", "web.LearningStreak", "web.Points", "web.ProgressTracker",
        ],
    },
    "challenges": {
        "title": "Challenges",
        "models": ["web.Challenge", "web.ChallengeSubmission"],
    },
    "calendar": {
        "title": "Calendar and Scheduling",
        "models": ["web.EventCalendar", "web.TimeSlot", "web.VideoRequest"],
    },
    "videos": {
        "title": "Videos",
        "models": ["web.EducationalVideo", "web.VideoRequest"],
    },
    "grading": {
        "title": "Gradeable Links",
        "models": ["web.GradeableLink", "web.LinkGrade"],
    },
    "donations": {
        "title": "Donations",
        "models": ["web.Donation"],
    },
}

SSR_RECORD_PAGES = {
    "/forum": {
        "title": "Forum",
        "kicker": "Discussions",
        "description": "Join discussions, ask questions, and share knowledge across Alpha One Labs.",
        "group": "community",
        "models": ["web.ForumCategory", "web.ForumTopic", "web.ForumReply", "web.ForumVote"],
        "noun": "topics",
        "private": False,
    },
    "/blog": {
        "title": "Blog",
        "kicker": "Community writing",
        "description": "Read posts, updates, and learning notes from the Alpha One Labs community.",
        "group": "community",
        "models": ["web.BlogPost"],
        "noun": "posts",
        "private": False,
    },
    "/study-groups": {
        "title": "Study Groups",
        "kicker": "Learn together",
        "description": "Browse study groups and group invitations from the learning community.",
        "group": "community",
        "models": ["web.StudyGroup", "web.StudyGroupInvite"],
        "noun": "groups",
        "private": False,
    },
    "/quizzes": {
        "title": "Quizzes",
        "kicker": "Assessments",
        "description": "Create, take, and review quiz material from the learning platform.",
        "group": "assessment",
        "models": ["web.Quiz", "web.QuizQuestion", "web.QuizOption", "web.UserQuiz"],
        "noun": "quiz records",
        "private": True,
    },
    "/surveys": {
        "title": "Surveys",
        "kicker": "Feedback and polls",
        "description": "Review surveys, questions, choices, and responses.",
        "group": "assessment",
        "models": ["web.Survey", "web.Question", "web.Choice", "web.Response"],
        "noun": "survey records",
        "private": True,
    },
    "/challenges": {
        "title": "Challenges",
        "kicker": "Weekly practice",
        "description": "Explore challenges and submissions from Alpha One Labs.",
        "group": "challenges",
        "models": ["web.Challenge", "web.ChallengeSubmission"],
        "noun": "challenge records",
        "private": False,
    },
    "/progress": {
        "title": "Progress",
        "kicker": "Learning activity",
        "description": "Track course progress, learning streaks, points, and progress trackers.",
        "group": "progress",
        "models": ["web.CourseProgress", "web.LearningStreak", "web.Points", "web.ProgressTracker"],
        "noun": "progress records",
        "private": True,
    },
    "/grade-links": {
        "title": "Grade Links",
        "kicker": "Review work",
        "description": "Submit and grade links using the restored Alpha One Labs workflow.",
        "group": "grading",
        "models": ["web.GradeableLink", "web.LinkGrade"],
        "noun": "grade records",
        "private": False,
    },
    "/calendar": {
        "title": "Calendar",
        "kicker": "Scheduling",
        "description": "View calendars, time slots, and scheduling records.",
        "group": "calendar",
        "models": ["web.EventCalendar", "web.TimeSlot"],
        "noun": "calendar records",
        "private": True,
    },
    "/memes": {
        "title": "Edu Memes",
        "kicker": "Community gallery",
        "description": "Browse educational memes from the Alpha One Labs community.",
        "group": "community",
        "models": ["web.Meme"],
        "noun": "memes",
        "private": False,
    },
    "/success-stories": {
        "title": "Success Stories",
        "kicker": "Community wins",
        "description": "Read success stories from learners and teachers.",
        "group": "community",
        "models": ["web.SuccessStory"],
        "noun": "stories",
        "private": False,
    },
    "/feature-votes": {
        "title": "Feature Voting",
        "kicker": "Platform ideas",
        "description": "Browse feature ideas and votes from the community.",
        "group": "community",
        "models": ["web.FeatureVote"],
        "noun": "feature records",
        "private": False,
    },
    "/messages": {
        "title": "Messages",
        "kicker": "Peer communication",
        "description": "View peer and secure messaging records while the first-class inbox is rebuilt.",
        "group": "community",
        "models": ["web.PeerMessage"],
        "noun": "messages",
        "private": True,
    },
}

SENSITIVE_RECORD_MODELS = {
    "web.PeerMessage", "web.Donation",
    "web.EventCalendar", "web.TimeSlot",
    "web.CourseProgress", "web.LearningStreak", "web.Points", "web.ProgressTracker",
    "web.Quiz", "web.QuizQuestion", "web.QuizOption", "web.UserQuiz",
    "web.Survey", "web.Question", "web.Choice", "web.Response",
}
FORUM_RECORD_MODELS = {"web.ForumCategory", "web.ForumTopic", "web.ForumReply", "web.ForumVote"}
BLOG_RECORD_MODELS = {"web.BlogPost"}


STATIC_CLEAN_ROUTES = {
    "/activity": "/activity.html",
    "/classes-map": "/classes-map.html",
    "/requests": "/requests.html",
    "/waiting-rooms": "/waiting-rooms.html",
    "/cart": "/cart.html",
    "/checkout-success": "/checkout-success.html",
    "/dashboard": "/dashboard.html",
    "/donate": "/donate.html",
    "/feedack": "/feedback.html",
    "/feedback": "/feedback.html",
    "/forgot-password": "/forgot-password.html",
    "/login": "/login.html",
    "/notification-preferences": "/notification-preferences.html",
    "/notifications": "/notifications.html",
    "/profile": "/profile.html",
    "/referral-leaderboard": "/referral-leaderboard.html",
    "/reset-password": "/reset-password.html",
    "/status": "/status.html",
    "/teach": "/teach.html",
    "/verify-email": "/verify-email.html",
    "/virtual-classroom": "/virtual-classroom.html",
    "/whiteboard": "/whiteboard.html",
    "/calculator": "/calculator.html",
    "/contributors": "/contributors.html",
    "/gsoc": "/gsoc.html",
    "/about": "/about.html",
    "/terms": "/terms.html",
    "/privacy": "/privacy.html",
    "/cookies": "/cookies.html",
    "/429": "/429.html",
    "/500": "/500.html",
    "/forum": "/forum.html",
    "/blog": "/blog.html",
    "/study-groups": "/study-groups.html",
    "/quizzes": "/quizzes.html",
    "/surveys": "/surveys.html",
    "/challenges": "/challenges.html",
    "/progress": "/progress.html",
    "/grade-links": "/grade-links.html",
    "/calendar": "/calendar.html",
    "/memes": "/memes.html",
    "/success-stories": "/success-stories.html",
    "/feature-votes": "/feature-votes.html",
    "/messages": "/messages.html",
}


LANGUAGE_URL_PREFIXES = {"en", "es", "fr", "de", "zh"}
LEGACY_LANGUAGE_ROUTE_ALIASES = {
    "/courses": "/activity",
    "/classes": "/activity",
    "/subjects": "/requests",
    "/request": "/requests",
    "/learn": "/requests?kind=learn",
    "/teacher": "/teach",
    "/teaching": "/teach",
    "/accounts/login": "/login",
    "/account/login": "/login",
    "/login": "/login",
    "/accounts/signup": "/login?tab=register",
    "/account/signup": "/login?tab=register",
    "/register": "/login?tab=register",
    "/signup": "/login?tab=register",
    "/accounts/password_reset": "/forgot-password",
    "/account/password_reset": "/forgot-password",
    "/password_reset": "/forgot-password",
    "/forgot_password": "/forgot-password",
    "/feedack": "/feedback",
    "/donation": "/donate",
    "/donations": "/donate",
    "/graphing_calculator": "/calculator",
    "/graphing-calculator": "/calculator",
    "/whiteboard": "/whiteboard",
    "/dashboard": "/dashboard",
    "/profile": "/profile",
    "/cart": "/cart",
    "/checkout": "/cart",
    "/referrals": "/referrals",
    "/referral-leaderboard": "/referral-leaderboard",
}


def _language_prefixed_target(path: str) -> Optional[str]:
    match = re.fullmatch(r"/([A-Za-z]{2})(/.*)?", path or "")
    if not match:
        return None
    lang = match.group(1).lower()
    if lang not in LANGUAGE_URL_PREFIXES:
        return None

    rest = match.group(2) or "/"
    if not rest.startswith("/"):
        rest = "/" + rest
    if rest != "/" and rest.endswith("/"):
        rest = rest.rstrip("/")

    if rest.startswith(("/images/", "/js/", "/partials/", "/media/")):
        return rest

    route = rest[:-5] if rest.endswith(".html") else rest
    if route == "":
        route = "/"
    if route == "/":
        return "/"

    if route in LEGACY_LANGUAGE_ROUTE_ALIASES:
        return LEGACY_LANGUAGE_ROUTE_ALIASES[route]
    for old_prefix, new_prefix in (("/courses/", "/activity/"), ("/course/", "/activity/"), ("/classes/", "/activity/")):
        if route.startswith(old_prefix):
            return new_prefix + route[len(old_prefix):]

    if route in STATIC_CLEAN_ROUTES or route in SSR_RECORD_PAGES:
        return route
    if route in ("/features", "/legacy-features"):
        return "/feature-votes"
    if re.fullmatch(r"/activity/[^/]+", route):
        return route
    if re.fullmatch(r"/memes/[^/]+", route):
        return route
    return ""


def _redirect_to_current_route(req, target: str):
    parsed = urlparse(req.url)
    target_path = target or "/"
    target_query = ""
    if "?" in target_path:
        target_path, target_query = target_path.split("?", 1)
    query = parsed.query
    if target_query and query:
        query = target_query + "&" + query
    elif target_query:
        query = target_query
    location = parsed._replace(path=target_path, query=query).geturl()
    return Response("", status=302, headers={"Location": location, **_CORS})


async def render_404(req, env, requested_path: str = ""):
    requested = requested_path or (urlparse(req.url).path if req else "")
    content = await _load_static_text(env, "404.html")
    if content:
        try:
            content = await _render_template_source(content, env, req, {"requested_path": requested})
        except Exception as exc:
            await capture_exception(exc, req, env, "render_404.template")
            content = None
    if not content:
        content = (
            "<!DOCTYPE html><html><head><title>Page Not Found - Alpha One Labs</title></head>"
            "<body><main style='font-family:sans-serif;max-width:720px;margin:4rem auto;padding:1rem;'>"
            "<h1>Page not found</h1><p>This old link is no longer active.</p>"
            "<p><a href='/'>Go home</a> or <a href='/activity'>browse activities</a>.</p>"
            "</main></body></html>"
        )
    return Response(
        content,
        status=404,
        headers={"Content-Type": "text/html; charset=utf-8", "Cache-Control": "public, max-age=60, s-maxage=300", **_CORS},
    )


def _html_escape(value: Any) -> str:
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _legacy_pick(fields: Dict[str, Any], names) -> str:
    for name in names:
        value = fields.get(name)
        if value not in (None, ""):
            return _legacy_text(value)
    return ""


def _legacy_public_media_url(value: Any) -> str:
    if value is None:
        return ""
    raw = str(value).strip()
    if not raw:
        return ""
    if raw.startswith(("http://", "https://", "/media/")):
        return raw
    if raw.startswith("/"):
        raw = raw.lstrip("/")
    return "/media/" + raw


def _legacy_route_for_record(model: str, pk: str, fields: Dict[str, Any], title: str) -> str:
    slug = _legacy_pick(fields, ("slug",))
    if model == "web.BlogPost":
        return "/blog/" + quote(slug or _slugify(title, pk or "post"))
    if model == "web.ForumCategory":
        return "/forum/" + quote(slug or _slugify(title, pk or "category"))
    if model == "web.ForumTopic":
        return "/forum/topic/" + quote(pk or _slugify(title, "topic"))
    if model == "web.Meme":
        return "/memes/" + quote(slug or _slugify(title, pk or "meme"))
    return _legacy_pick(fields, ("url", "video_url"))


def _legacy_vote_value(fields: Dict[str, Any]) -> int:
    raw = _legacy_pick(fields, ("vote_type", "value", "vote", "score"))
    low = str(raw).strip().lower()
    if low in {"up", "upvote", "+", "+1", "1", "true"}:
        return 1
    if low in {"down", "downvote", "-", "-1"}:
        return -1
    try:
        value = int(float(low))
        return 1 if value > 0 else (-1 if value < 0 else 0)
    except Exception:
        return 0


def _legacy_feature_summary(record: Dict[str, Any]) -> Dict[str, Any]:
    model = _legacy_text(record.get("model"), "unknown")
    pk = _legacy_text(record.get("pk"), "")
    fields = record.get("fields") or {}
    title = _legacy_pick(fields, ("title", "name", "caption", "question_text", "text", "link_type", "subject"))
    description = _legacy_pick(fields, (
        "caption", "description", "excerpt", "summary", "content", "body", "message", "notes", "submission_text",
        "comment", "url", "video_url",
    ))
    if not title:
        title = model.rsplit(".", 1)[-1] + (f" #{pk}" if pk else "")
    if len(description) > 700:
        description = description[:697] + "..."
    amount = _legacy_pick(fields, (
        "amount", "grade", "score", "points_awarded", "points", "current_streak", "longest_streak",
    ))
    image_url = _legacy_public_media_url(_legacy_pick(fields, (
        "featured_image", "image", "thumbnail", "cover_image", "photo", "picture",
    )))
    created_at = _legacy_pick(fields, (
        "published_at", "created_at", "updated_at", "uploaded_at", "awarded_at",
        "submitted_at", "start_date", "joined_at",
    ))
    parent_ref = _legacy_pick(fields, (
        "topic", "post", "blog_post", "category", "calendar", "quiz", "survey", "question", "enrollment", "user", "creator", "author", "student",
    ))
    category_ref = _legacy_pick(fields, ("category", "forum_category"))
    return {
        "model": model,
        "legacy_pk": pk,
        "title": title,
        "description": description,
        "status": _legacy_pick(fields, ("status", "challenge_type", "donation_type", "link_type", "category")),
        "created_at": created_at,
        "url": _legacy_pick(fields, ("url", "video_url")),
        "route_url": _legacy_route_for_record(model, pk, fields, title),
        "image_url": image_url,
        "amount": amount,
        "parent_ref": parent_ref,
        "category_ref": category_ref,
        "slug": _legacy_pick(fields, ("slug",)),
        "author_ref": _legacy_pick(fields, ("author", "creator", "user", "student")),
        "subject_ref": _legacy_pick(fields, ("subject",)),
        "uploader_ref": _legacy_pick(fields, ("uploader",)),
        "vote_value": _legacy_vote_value(fields) if model == "web.ForumVote" else 0,
    }


def _is_test_success_story_record(record: Dict[str, Any]) -> bool:
    if (record.get("model") or "") != "web.SuccessStory":
        return False
    title = _legacy_text(record.get("title"), "").strip().lower()
    slug = _legacy_text(record.get("slug"), "").strip().lower()
    description = _legacy_text(record.get("description"), "").strip().lower()
    exact_test_names = {"test success story", "success story test", "test story"}
    if title in exact_test_names or slug in {"test-success-story", "success-story-test", "test-story"}:
        return True
    if title.startswith("test ") and "success" in title and "story" in title:
        return True
    return "test success story" in description[:240]


def _ssr_nav() -> str:
    links = [
        ("/activity", "Courses"),
        ("/classes-map", "Classes Near Me"),
        ("/waiting-rooms", "Waiting Rooms"),
        ("/forum", "Forum"),
        ("/blog", "Blog"),
        ("/study-groups", "Study Groups"),
        ("/quizzes", "Quizzes"),
        ("/challenges", "Challenges"),
        ("/progress", "Progress"),
        ("/cart", "Cart"),
        ("/login", "Login"),
    ]
    nav_links = "".join(
        f'<a href="{href}" class="px-3 py-2 rounded-md hover:bg-teal-700 text-sm font-medium">{label}</a>'
        for href, label in links
    )
    return (
        '<header class="w-full bg-teal-600 dark:bg-teal-800 text-white shadow-md">'
        '<div class="max-w-[90rem] mx-auto px-4 md:px-6 min-h-[70px] flex flex-wrap items-center justify-between gap-3 py-3">'
        '<a href="/" class="flex items-center space-x-2">'
        '<img src="/images/logo.png" alt="Alpha One Labs Logo" height="40" width="40" class="h-10 w-10">'
        '<span class="text-xl font-bold">Alpha One Labs</span></a>'
        f'<nav class="flex flex-wrap items-center gap-1">{nav_links}</nav>'
        '</div></header>'
    )


def _ssr_footer() -> str:
    return (
        '<footer class="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 mt-auto">'
        '<div class="max-w-[90rem] mx-auto px-4 md:px-6 py-8 flex flex-col md:flex-row justify-between gap-4 text-sm text-gray-500 dark:text-gray-400">'
        '<p>&copy; 2026 Alpha One Labs. All rights reserved.</p>'
        '<div class="flex flex-wrap gap-4">'
        '<a href="/about" class="hover:text-teal-600">About</a>'
        '<a href="/status" class="hover:text-teal-600">Status</a>'
        '<a href="/feedback" class="hover:text-teal-600">Feedback</a>'
        '<a href="/terms" class="hover:text-teal-600">Terms</a>'
        '<a href="/privacy" class="hover:text-teal-600">Privacy</a>'
        '</div></div></footer>'
    )


def _ssr_record_icon(model: str) -> str:
    m = (model or "").lower()
    if "forum" in m:
        return "fa-comments"
    if "blog" in m:
        return "fa-blog"
    if "study" in m:
        return "fa-users"
    if "quiz" in m:
        return "fa-circle-question"
    if "survey" in m or "question" in m:
        return "fa-square-poll-vertical"
    if "challenge" in m:
        return "fa-trophy"
    if "progress" in m or "streak" in m or "points" in m:
        return "fa-chart-line"
    if "grade" in m or "link" in m:
        return "fa-link"
    if "calendar" in m or "slot" in m:
        return "fa-calendar-days"
    if "meme" in m:
        return "fa-face-smile"
    if "success" in m:
        return "fa-star"
    if "message" in m:
        return "fa-envelope"
    if "feature" in m:
        return "fa-lightbulb"
    return "fa-layer-group"


def _ssr_model_label(model: str) -> str:
    label = re.sub(r"^web\.", "", model or "")
    return re.sub(r"([a-z])([A-Z])", r"\1 \2", label)


def _ssr_record_card(record: Dict[str, Any]) -> str:
    model = _html_escape(_ssr_model_label(record.get("model", "")))
    icon = _ssr_record_icon(record.get("model", ""))
    title = _html_escape(record.get("title", ""))
    desc = _html_escape(record.get("description", ""))
    date = _html_escape((record.get("created_at") or "")[:10])
    status = _html_escape(record.get("status", ""))
    amount = _html_escape(record.get("amount", ""))
    url = _html_escape(record.get("url", ""))
    route_url = _html_escape(record.get("route_url", ""))
    image_url = _html_escape(record.get("image_url", ""))
    pills = ""
    if status:
        pills += f'<span class="rounded-full bg-gray-100 dark:bg-gray-900 px-3 py-1 text-gray-600 dark:text-gray-300">{status}</span>'
    if amount:
        pills += f'<span class="rounded-full bg-amber-100 dark:bg-amber-900/30 px-3 py-1 text-amber-700 dark:text-amber-300">{amount}</span>'
    if url:
        pills += f'<a href="{url}" target="_blank" rel="noopener" class="rounded-full bg-teal-100 dark:bg-teal-900/30 px-3 py-1 text-teal-700 dark:text-teal-300 hover:underline">Open link</a>'
    if route_url:
        pills += f'<a href="{route_url}" class="rounded-full bg-cyan-100 dark:bg-cyan-900/30 px-3 py-1 text-cyan-700 dark:text-cyan-300 hover:underline">Open page</a>'
    date_html = f"<span>{date}</span>" if date else ""
    desc_html = f'<p class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">{desc}</p>' if desc else ""
    pills_html = f'<div class="mt-3 flex flex-wrap gap-2 text-xs">{pills}</div>' if pills else ""
    image_html = (
        f'<a href="{route_url or url or "#"}" class="block sm:w-44 shrink-0 rounded-xl overflow-hidden bg-gray-100 dark:bg-gray-900 border border-gray-100 dark:border-gray-700">'
        f'<img src="{image_url}" alt="{title}" class="w-full aspect-video sm:aspect-square object-cover" loading="lazy" onerror="this.closest(\'a\').remove();"></a>'
        if image_url else
        f'<div class="hidden sm:flex w-11 h-11 rounded-full bg-teal-100 dark:bg-teal-900 items-center justify-center text-teal-600 dark:text-teal-300 shrink-0"><i class="fa-solid {icon}"></i></div>'
    )
    title_html = f'<a href="{route_url}" class="hover:text-teal-700 dark:hover:text-teal-300">{title}</a>' if route_url else title
    return (
        '<article class="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-700 p-4 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">'
        '<div class="flex flex-col sm:flex-row items-start gap-4">'
        f'{image_html}'
        '<div class="min-w-0 flex-1">'
        '<div class="flex flex-wrap items-center justify-between gap-2 mb-1 text-xs text-gray-500 dark:text-gray-400">'
        f'<span class="font-medium text-teal-600 dark:text-teal-300">{model}</span>'
        f'{date_html}'
        '</div>'
        f'<h2 class="text-lg font-bold text-gray-900 dark:text-gray-100 mb-2">{title_html}</h2>'
        f'{desc_html}'
        f'{pills_html}'
        '</div></div></article>'
    )


def _ssr_meme_grid_html(records: list) -> str:
    if not records:
        return '<div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-8 text-center text-gray-500 dark:text-gray-400">No memes found yet.</div>'
    cards = []
    for record in records:
        title = _html_escape(record.get("title") or "Educational meme")
        caption = _html_escape(record.get("description") or "")
        image_url = _html_escape(record.get("image_url") or "")
        href = _html_escape(record.get("route_url") or record.get("url") or image_url or "/memes")
        date = _html_escape((record.get("created_at") or "")[:10])
        image_html = (
            '<div class="w-full h-56 bg-gray-100 dark:bg-gray-900 flex items-center justify-center overflow-hidden">'
            f'<img src="{image_url}" alt="{title}" class="max-w-full max-h-full object-contain" loading="lazy" onerror="this.closest(\'a\').classList.add(\'hidden\');">'
            '</div>'
            if image_url else
            '<div class="w-full h-56 bg-gradient-to-br from-teal-100 to-cyan-100 dark:from-teal-900 dark:to-cyan-900 flex items-center justify-center text-teal-700 dark:text-teal-200"><i class="fa-solid fa-face-smile text-4xl"></i></div>'
        )
        cards.append(
            f'<a href="{href}" class="group bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden transition-all duration-300 hover:shadow-xl hover:-translate-y-0.5">'
            f'{image_html}'
            '<div class="p-4">'
            f'<h3 class="text-lg font-black text-gray-900 dark:text-white group-hover:text-teal-700 dark:group-hover:text-teal-300">{title}</h3>'
            + (f'<p class="text-sm text-gray-600 dark:text-gray-300 mt-2 line-clamp-2">{caption}</p>' if caption else '') +
            '<div class="mt-4 flex items-center justify-between gap-3 text-xs text-gray-500 dark:text-gray-400">'
            '<span class="inline-flex items-center rounded-full bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300 px-3 py-1 font-bold"><i class="fa-solid fa-face-smile mr-1"></i>Edu Meme</span>'
            + (f'<span>{date}</span>' if date else '') +
            '</div></div></a>'
        )
    return '<div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-6">' + "".join(cards) + '</div>'


def _legacy_record_matches_ref(record: Dict[str, Any], ref: str) -> bool:
    target = (ref or "").strip().lower()
    if not target:
        return False
    candidates = {
        str(record.get("legacy_pk") or "").strip().lower(),
        str(record.get("slug") or "").strip().lower(),
        _slugify(record.get("title") or "", record.get("legacy_pk") or "").strip().lower(),
    }
    return target in candidates


async def render_meme_detail(req, env, ref: str):
    records = await _server_records_for_models(env, ["web.Meme"], limit=500)
    meme = next((record for record in records if _legacy_record_matches_ref(record, ref)), None)
    if not meme:
        return await render_404(req, env, urlparse(req.url).path)
    title = _html_escape(meme.get("title") or "Educational meme")
    caption = _html_escape(meme.get("description") or "")
    image_url = _html_escape(meme.get("image_url") or "")
    date = _html_escape((meme.get("created_at") or "")[:10])
    image_html = (
        '<div class="bg-gray-100 dark:bg-gray-950 rounded-2xl p-4 md:p-6 flex items-center justify-center">'
        f'<img src="{image_url}" alt="{title}" class="max-w-full max-h-[75vh] object-contain rounded-xl" loading="eager">'
        '</div>'
        if image_url else
        '<div class="bg-gray-100 dark:bg-gray-950 rounded-2xl p-16 text-center text-teal-600 dark:text-teal-300"><i class="fa-solid fa-face-smile text-6xl"></i></div>'
    )
    html = (
        '<!DOCTYPE html><html lang="en" class="scroll-smooth"><head>'
        '<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">'
        f'<title>{title} - Edu Meme</title>'
        '<link rel="icon" type="image/png" href="/images/logo.png">'
        '<script src="https://cdn.tailwindcss.com"></script>'
        '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">'
        '<script>tailwind.config={darkMode:"class",theme:{extend:{}}};if(localStorage.getItem("darkMode")==="true"){document.documentElement.classList.add("dark");}</script>'
        '</head><body class="min-h-screen flex flex-col bg-gray-50 text-gray-900 dark:bg-black dark:text-gray-100">'
        f'{_ssr_nav()}'
        '<main class="flex-1 w-full max-w-5xl mx-auto px-4 py-8 md:py-12">'
        '<article class="bg-white dark:bg-gray-800 rounded-3xl shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden">'
        '<div class="p-5 md:p-8">'
        '<div class="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-6">'
        '<div>'
        f'<h1 class="text-3xl font-black text-gray-900 dark:text-white">{title}</h1>'
        '<div class="mt-3 flex flex-wrap items-center gap-2 text-sm text-gray-500 dark:text-gray-400">'
        '<span class="rounded-full bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300 px-3 py-1 font-bold"><i class="fa-solid fa-face-smile mr-1"></i>Edu Meme</span>'
        + (f'<span>{date}</span>' if date else '') +
        '</div></div>'
        '<a href="/memes" class="inline-flex items-center text-teal-700 dark:text-teal-300 hover:underline font-semibold"><i class="fa-solid fa-arrow-left mr-2"></i>Back to memes</a>'
        '</div>'
        f'{image_html}'
        + (f'<section class="mt-6"><h2 class="text-lg font-bold text-gray-900 dark:text-white mb-2">Caption</h2><p class="text-gray-700 dark:text-gray-300 leading-relaxed">{caption}</p></section>' if caption else '') +
        '<div class="mt-6 flex flex-wrap gap-3">'
        '<button onclick="navigator.clipboard&&navigator.clipboard.writeText(location.href)" class="inline-flex items-center px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white font-bold"><i class="fa-solid fa-share-alt mr-2"></i>Share</button>'
        + (f'<a href="{image_url}" download class="inline-flex items-center px-4 py-2 rounded-lg bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-900 dark:text-white font-bold"><i class="fa-solid fa-download mr-2"></i>Save</a>' if image_url else '') +
        '</div></div></article></main>'
        f'{_ssr_footer()}'
        '</body></html>'
    )
    return Response(html, headers={"Content-Type": "text/html; charset=utf-8", **_CORS})


def _ssr_side_nav(active_path: str) -> str:
    links = [
        ("/forum", "Forum", "fa-comments"),
        ("/blog", "Blog", "fa-blog"),
        ("/study-groups", "Study Groups", "fa-users"),
        ("/quizzes", "Quizzes", "fa-circle-question"),
        ("/surveys", "Surveys", "fa-square-poll-vertical"),
        ("/challenges", "Challenges", "fa-trophy"),
        ("/progress", "Progress", "fa-chart-line"),
        ("/grade-links", "Grade Links", "fa-link"),
        ("/calendar", "Calendar", "fa-calendar-days"),
        ("/memes", "Edu Memes", "fa-face-smile"),
        ("/success-stories", "Success Stories", "fa-star"),
        ("/feature-votes", "Feature Voting", "fa-lightbulb"),
    ]
    html = []
    for href, label, icon in links:
        active = href == active_path
        cls = "bg-gray-100 dark:bg-gray-700 font-medium" if active else "hover:bg-gray-100 dark:hover:bg-gray-700"
        html.append(
            f'<a href="{href}" class="flex items-center py-2 px-3 text-gray-700 dark:text-gray-300 {cls} rounded-lg">'
            f'<i class="fa-solid {icon} text-teal-500 mr-2"></i>{label}</a>'
        )
    return "".join(html)


async def _private_records_signin_html() -> str:
    return (
        '<div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-8 text-center">'
        '<p class="text-gray-600 dark:text-gray-300 mb-4">Sign in to view this private section.</p>'
        '<a href="/login" class="inline-flex items-center px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white font-semibold">'
        '<i class="fa-solid fa-right-to-bracket mr-2"></i>Sign in</a></div>'
    )


async def _server_forum_payload(env) -> Dict[str, Any]:
    records = await _server_records_for_models(env, list(FORUM_RECORD_MODELS), limit=500)
    categories = [r for r in records if r.get("model") == "web.ForumCategory"]
    topics = [r for r in records if r.get("model") == "web.ForumTopic"]
    replies = [r for r in records if r.get("model") == "web.ForumReply"]
    votes = [r for r in records if r.get("model") == "web.ForumVote"]
    reply_counts = {}
    vote_scores = {}
    for reply in replies:
        ref = str(reply.get("parent_ref") or "")
        if ref:
            reply_counts[ref] = reply_counts.get(ref, 0) + 1
    for vote in votes:
        ref = str(vote.get("parent_ref") or vote.get("category_ref") or "")
        if ref:
            vote_scores[ref] = vote_scores.get(ref, 0) + int(vote.get("vote_value") or 0)
    return {"records": records, "categories": categories, "topics": topics, "replies": replies, "votes": votes, "reply_counts": reply_counts, "vote_scores": vote_scores}


async def _server_forum_records_html(env) -> str:
    payload = await _server_forum_payload(env)
    categories = payload["categories"]
    topics = payload["topics"]
    reply_counts = payload["reply_counts"]
    vote_scores = payload["vote_scores"]
    cat_by_pk = {str(c.get("legacy_pk") or ""): c for c in categories}
    rows = []
    if categories:
        rows.append('<section class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mb-8">')
        for cat in categories:
            href = _html_escape(cat.get("route_url") or "/forum")
            title = _html_escape(cat.get("title") or "Forum category")
            desc = _html_escape(cat.get("description") or "")
            count = sum(1 for t in topics if str(t.get("category_ref") or "") == str(cat.get("legacy_pk") or ""))
            rows.append(
                '<a href="' + href + '" class="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-sm hover:border-teal-400 hover:-translate-y-0.5 transition">'
                '<p class="text-xs font-bold uppercase tracking-[0.22em] text-teal-600 dark:text-teal-300">Category</p>'
                '<h3 class="mt-2 text-lg font-black text-gray-900 dark:text-white">' + title + '</h3>'
                + (('<p class="mt-2 text-sm text-gray-600 dark:text-gray-300">' + desc + '</p>') if desc else '') +
                '<p class="mt-4 text-xs font-bold text-gray-500 dark:text-gray-400">' + str(count) + ' topics</p></a>'
            )
        rows.append('</section>')
    if not topics:
        rows.append('<div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-8 text-center text-gray-500 dark:text-gray-400">No forum topics found yet.</div>')
        return "".join(rows)
    rows.append('<section class="space-y-4">')
    for topic in topics:
        pk = str(topic.get("legacy_pk") or "")
        category = cat_by_pk.get(str(topic.get("category_ref") or ""), {})
        href = _html_escape(topic.get("route_url") or "/forum")
        title = _html_escape(topic.get("title") or "Forum topic")
        desc = _html_escape(topic.get("description") or "")
        date = _html_escape((topic.get("created_at") or "")[:10])
        cat_title = _html_escape(category.get("title") or "Forum")
        replies = int(reply_counts.get(pk, 0))
        score = int(vote_scores.get(pk, 0))
        rows.append(
            '<article class="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-5 shadow-sm hover:bg-gray-50 dark:hover:bg-gray-700 transition">'
            '<div class="flex flex-col md:flex-row md:items-start justify-between gap-4">'
            '<div class="min-w-0 flex-1">'
            '<div class="flex flex-wrap gap-2 text-xs mb-2"><span class="rounded-full bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300 px-3 py-1 font-bold">' + cat_title + '</span>' + (('<span class="text-gray-500 dark:text-gray-400 px-2 py-1">' + date + '</span>') if date else '') + '</div>'
            '<h3 class="text-xl font-black text-gray-900 dark:text-white"><a href="' + href + '" class="hover:text-teal-700 dark:hover:text-teal-300">' + title + '</a></h3>'
            + (('<p class="mt-2 text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap">' + desc + '</p>') if desc else '') +
            '</div><div class="flex md:flex-col gap-2 shrink-0 text-sm">'
            '<span class="rounded-xl bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 px-3 py-2 font-black"><i class="fa-solid fa-arrow-up mr-1"></i>' + str(score) + ' votes</span>'
            '<span class="rounded-xl bg-cyan-100 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-300 px-3 py-2 font-black"><i class="fa-solid fa-reply mr-1"></i>' + str(replies) + ' replies</span>'
            '</div></div></article>'
        )
    rows.append('</section>')
    return "".join(rows)


async def render_blog_detail(req, env, slug: str):
    posts = await _server_records_for_models(env, ["web.BlogPost"], limit=250)
    target = None
    for post in posts:
        post_slug = post.get("slug") or _slugify(post.get("title") or "post", post.get("legacy_pk") or "post")
        if slug in {post_slug, str(post.get("legacy_pk") or "")}:
            target = post
            break
    if not target:
        return await render_404(req, env, "/blog/" + slug)
    comments = [c for c in await _server_records_for_models(env, ["web.BlogComment"], limit=250) if str(c.get("parent_ref") or "") == str(target.get("legacy_pk") or "")]
    title = _html_escape(target.get("title") or "Blog post")
    desc = _html_escape(target.get("description") or "")
    date = _html_escape((target.get("created_at") or "")[:10])
    image = _html_escape(target.get("image_url") or "")
    comments_html = "".join(_ssr_record_card(c) for c in comments) or '<div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 text-gray-500 dark:text-gray-400">No comments yet.</div>'
    image_html = f'<img src="{image}" alt="{title}" class="w-full max-h-[32rem] object-cover rounded-3xl border border-gray-200 dark:border-gray-700 shadow-lg mb-8" onerror="this.remove();">' if image else ""
    html = (
        '<!DOCTYPE html><html lang="en" class="scroll-smooth"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">'
        f'<title>{title} - Alpha One Labs</title><link rel="icon" type="image/png" href="/images/logo.png"><script src="https://cdn.tailwindcss.com"></script><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">'
        '<script>tailwind.config={darkMode:"class",theme:{extend:{}}};if(localStorage.getItem("darkMode")==="true"){document.documentElement.classList.add("dark");}</script></head>'
        '<body class="min-h-screen flex flex-col bg-gray-50 text-gray-900 dark:bg-black dark:text-gray-100">' + _ssr_nav() +
        '<main class="flex-1 max-w-5xl mx-auto w-full px-4 md:px-6 py-10"><a href="/blog" class="inline-flex items-center text-sm font-bold text-teal-700 dark:text-teal-300 hover:underline mb-6"><i class="fa-solid fa-arrow-left mr-2"></i>Back to blog</a>'
        f'<article class="bg-white dark:bg-gray-900 rounded-3xl border border-gray-200 dark:border-gray-700 p-6 md:p-10 shadow-sm">{image_html}<p class="text-xs font-bold uppercase tracking-[0.24em] text-teal-700 dark:text-teal-300">Blog</p><h1 class="mt-3 text-4xl md:text-5xl font-black text-gray-950 dark:text-white leading-tight">{title}</h1>'
        + (f'<p class="mt-3 text-sm text-gray-500 dark:text-gray-400">{date}</p>' if date else '') +
        f'<div class="mt-8 prose prose-lg dark:prose-invert max-w-none text-gray-700 dark:text-gray-200 whitespace-pre-wrap">{desc}</div></article>'
        '<section class="mt-8"><h2 class="text-2xl font-black mb-4">Comments</h2><div class="space-y-4">' + comments_html + '</div></section></main>' + _ssr_footer() + '</body></html>'
    )
    return Response(html, headers={"Content-Type": "text/html; charset=utf-8", **_CORS})


async def render_forum_topic_detail(req, env, topic_ref: str):
    payload = await _server_forum_payload(env)
    topic = next((t for t in payload["topics"] if str(t.get("legacy_pk") or "") == str(topic_ref)), None)
    if not topic:
        return await render_404(req, env, "/forum/topic/" + topic_ref)
    pk = str(topic.get("legacy_pk") or "")
    replies = [r for r in payload["replies"] if str(r.get("parent_ref") or "") == pk]
    votes = int(payload["vote_scores"].get(pk, 0))
    title = _html_escape(topic.get("title") or "Forum topic")
    desc = _html_escape(topic.get("description") or "")
    date = _html_escape((topic.get("created_at") or "")[:10])
    replies_html = "".join(_ssr_record_card(r) for r in replies) or '<div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 text-gray-500 dark:text-gray-400">No replies yet.</div>'
    html = (
        '<!DOCTYPE html><html lang="en" class="scroll-smooth"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">'
        f'<title>{title} - Alpha One Labs Forum</title><link rel="icon" type="image/png" href="/images/logo.png"><script src="https://cdn.tailwindcss.com"></script><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">'
        '<script>tailwind.config={darkMode:"class",theme:{extend:{}}};if(localStorage.getItem("darkMode")==="true"){document.documentElement.classList.add("dark");}</script></head>'
        '<body class="min-h-screen flex flex-col bg-gray-50 text-gray-900 dark:bg-black dark:text-gray-100">' + _ssr_nav() +
        '<main class="flex-1 max-w-5xl mx-auto w-full px-4 md:px-6 py-10"><a href="/forum" class="inline-flex items-center text-sm font-bold text-teal-700 dark:text-teal-300 hover:underline mb-6"><i class="fa-solid fa-arrow-left mr-2"></i>Back to forum</a>'
        f'<article class="bg-white dark:bg-gray-900 rounded-3xl border border-gray-200 dark:border-gray-700 p-6 md:p-10 shadow-sm"><div class="flex flex-wrap gap-2 mb-4"><span class="rounded-full bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 px-3 py-1 text-xs font-black"><i class="fa-solid fa-arrow-up mr-1"></i>{votes} votes</span>' + (f'<span class="text-xs text-gray-500 dark:text-gray-400 px-2 py-1">{date}</span>' if date else '') + f'</div><h1 class="text-4xl md:text-5xl font-black text-gray-950 dark:text-white leading-tight">{title}</h1><div class="mt-8 text-gray-700 dark:text-gray-200 whitespace-pre-wrap">{desc}</div></article>'
        '<section class="mt-8"><h2 class="text-2xl font-black mb-4">Replies</h2><div class="space-y-4">' + replies_html + '</div></section></main>' + _ssr_footer() + '</body></html>'
    )
    return Response(html, headers={"Content-Type": "text/html; charset=utf-8", **_CORS})


async def render_ssr_record_page(req, env, clean_path: str, config: Dict[str, Any]):
    user = verify_token(req.headers.get("Authorization") or "", env.JWT_SECRET)
    records = []
    if clean_path == "/forum":
        body = await _server_forum_records_html(env)
        count = str(len((await _server_forum_payload(env))["topics"]))
    elif config.get("private") and not user:
        body = await _private_records_signin_html()
        count = "0"
    else:
        owner_user_id = user["id"] if config.get("private") and user else None
        records = await _server_records_for_models(env, config["models"], owner_user_id=owner_user_id, limit=250)
        count = str(len(records))
        body = "".join(_ssr_record_card(record) for record in records) or (
            f'<div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-8 text-center text-gray-500 dark:text-gray-400">No {_html_escape(config["noun"])} found yet.</div>'
        )

    title = _html_escape(config["title"])
    kicker = _html_escape(config["kicker"])
    desc = _html_escape(config["description"])
    noun = _html_escape(config["noun"])
    html = (
        '<!DOCTYPE html><html lang="en" class="scroll-smooth"><head>'
        '<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">'
        f'<title>{title} - Alpha One Labs</title>'
        '<link rel="icon" type="image/png" href="/images/logo.png">'
        '<script src="https://cdn.tailwindcss.com"></script>'
        '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">'
        '<script>tailwind.config={darkMode:"class",theme:{extend:{}}};if(localStorage.getItem("darkMode")==="true"){document.documentElement.classList.add("dark");}</script>'
        '</head><body class="min-h-screen flex flex-col bg-gray-50 text-gray-900 dark:bg-black dark:text-gray-100">'
        f'{_ssr_nav()}'
        '<main class="flex-1 w-full max-w-[90rem] mx-auto px-0 md:px-0">'
        '<div class="flex flex-col lg:flex-row min-h-[calc(100vh-4rem)]">'
        '<aside class="w-full lg:w-64 xl:w-72 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 p-4 lg:p-6">'
        f'<div class="mb-6"><h1 class="text-xl font-bold flex items-center text-gray-800 dark:text-gray-100"><i class="fa-solid fa-layer-group text-teal-500 mr-2"></i>{title}</h1>'
        f'<p class="text-sm text-gray-600 dark:text-gray-400 mt-1">{kicker}</p></div>'
        f'<nav class="space-y-2 text-sm">{_ssr_side_nav(clean_path)}</nav>'
        '</aside>'
        '<section class="flex-1 bg-gray-50 dark:bg-gray-900 p-4 lg:p-6">'
        '<div class="flex flex-wrap justify-between items-start gap-4 mb-6">'
        f'<div><p class="text-sm uppercase tracking-wide text-teal-600 dark:text-teal-300 font-bold">{kicker}</p><h2 class="text-3xl font-bold mt-1 text-gray-900 dark:text-gray-100">{title}</h2><p class="text-gray-600 dark:text-gray-400 mt-2 max-w-3xl">{desc}</p></div>'
        f'<div class="rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 py-3 text-sm text-gray-600 dark:text-gray-300"><span class="text-2xl font-black text-teal-600 dark:text-teal-300">{count}</span> {noun}</div>'
        '</div>'
        f'<div class="space-y-4">{body}</div>'
        '</section></div></main>'
        f'{_ssr_footer()}'
        '</body></html>'
    )
    return Response(html, headers={"Content-Type": "text/html; charset=utf-8", **_CORS})


async def api_features(req, env):
    user = verify_token(req.headers.get("Authorization") or "", env.JWT_SECRET)

    parsed = urlparse(req.url)
    params = parse_qs(parsed.query)
    group = (params.get("group") or ["community"])[0]
    if group not in LEGACY_FEATURE_GROUPS:
        group = "community"
    try:
        limit = max(1, min(250, int((params.get("limit") or ["100"])[0])))
    except Exception:
        limit = 100

    models = LEGACY_FEATURE_GROUPS[group]["models"]
    requested_models = []
    for raw_models in (params.get("models") or params.get("model") or []):
        requested_models.extend([
            item.strip()
            for item in str(raw_models).split(",")
            if item.strip()
        ])
    if requested_models:
        filtered_models = [model for model in requested_models if model in models]
        if filtered_models:
            models = filtered_models
    requires_owner = any(model in SENSITIVE_RECORD_MODELS for model in models)
    if requires_owner and not user:
        return err("Authentication required", 401)
    records = await _server_records_for_models(
        env,
        models,
        owner_user_id=(user["id"] if requires_owner and user else None),
        limit=limit,
    )

    groups = [
        {"id": key, "title": value["title"], "count_models": len(value["models"])}
        for key, value in LEGACY_FEATURE_GROUPS.items()
    ]
    return json_resp({
        "group": group,
        "title": LEGACY_FEATURE_GROUPS[group]["title"],
        "groups": groups,
        "records": records,
    })


async def api_create_donation_checkout(req, env):
    user = verify_token(req.headers.get("Authorization") or "", env.JWT_SECRET)
    body, bad_resp = await parse_json_object(req)
    if bad_resp:
        return bad_resp

    try:
        amount_cents = int(body.get("amount_cents") or 0)
    except Exception:
        amount_cents = 0
    if amount_cents < 100:
        return err("Donation amount must be at least $1.00")
    if amount_cents > 1000000:
        return err("Donation amount is too large")

    message = _legacy_text(body.get("message"))[:500]
    email = _legacy_text(body.get("email")).strip()[:180]
    origin = f"{urlparse(req.url).scheme}://{urlparse(req.url).netloc}"
    fields = {
        "mode": "payment",
        "success_url": origin + "/checkout-success?donation=1&session_id={CHECKOUT_SESSION_ID}",
        "cancel_url": origin + "/donate",
        "line_items[0][quantity]": 1,
        "line_items[0][price_data][currency]": "usd",
        "line_items[0][price_data][unit_amount]": amount_cents,
        "line_items[0][price_data][product_data][name]": "Alpha One Labs donation",
        "metadata[kind]": "donation",
    }
    if user:
        fields["metadata[user_id]"] = user["id"]
    if email and "@" in email:
        fields["customer_email"] = email

    try:
        session = await _stripe_form_request(env, "/checkout/sessions", fields)
        session_id = session.get("id", "")
        await env.DB.prepare(
            "INSERT INTO donation_checkout_sessions"
            " (id,user_id,stripe_session_id,status,amount_total,currency,message)"
            " VALUES (?,?,?,?,?,?,?)"
            " ON CONFLICT(stripe_session_id) DO UPDATE SET status=excluded.status,amount_total=excluded.amount_total"
        ).bind(
            new_id(),
            user["id"] if user else None,
            session_id,
            "pending",
            amount_cents,
            "USD",
            await encrypt_aes(message, env.ENCRYPTION_KEY) if message else "",
        ).run()
        return ok({
            "checkout_url": session.get("url", ""),
            "session_id": session_id,
        }, "Donation checkout created")
    except Exception as exc:
        await capture_exception(exc, req, env, "api_create_donation_checkout")
        return err("Could not create donation checkout", 500)


async def serve_r2_media(path: str, env):
    bucket = getattr(env, "MY_BUCKET", None)
    if not bucket:
        return err("Media bucket is not configured", 500)
    key = path.lstrip("/")
    try:
        obj = await bucket.get(key)
    except Exception as exc:
        await capture_exception(exc, where="serve_r2_media.get")
        return err("Media unavailable", 500)
    if not obj:
        return err("Media not found", 404)
    headers = {"Cache-Control": "public, max-age=31536000, immutable"}
    http_meta = getattr(obj, "http_metadata", None) or getattr(obj, "httpMetadata", None)
    content_type = getattr(http_meta, "contentType", None) if http_meta else None
    if content_type:
        headers["Content-Type"] = content_type
    return Response(getattr(obj, "body", obj), headers=headers)


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

    act_row = await env.DB.prepare(
        "SELECT title FROM activities WHERE id=?"
    ).bind(act_id).first()
    recipient_ids = await _activity_enrollee_ids(env, act_id, exclude_user_id=user["id"])
    if recipient_ids:
        await emit_event(env, "ACTIVITY_TAGS_UPDATED", {
            "activity_id":    act_id,
            "activity_title": act_row.title if act_row else act_id,
            "recipient_ids":  recipient_ids,
        })

    return ok(None, "Tags updated")


def _legacy_text(value, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _legacy_bool(value) -> int:
    return 1 if value in (True, 1, "1", "true", "True", "yes", "on") else 0


def _legacy_id(prefix: str, value) -> str:
    raw = re.sub(r"[^A-Za-z0-9_-]+", "-", _legacy_text(value, "unknown")).strip("-")
    return f"legacy-{prefix}-{raw or 'unknown'}"


def _legacy_money_cents(value) -> Optional[int]:
    if value in (None, ""):
        return 0
    try:
        return int(round(float(str(value)) * 100))
    except Exception:
        return None


def _legacy_media(path):
    if not path:
        return "", ""
    clean = str(path).strip().lstrip("/")
    if not clean:
        return "", ""
    key = f"media/{clean}"
    return f"/{key}", key


async def _legacy_json(value, enc: str) -> str:
    return await encrypt_aes(json.dumps(value, sort_keys=True, default=str), enc)


async def _legacy_ensure_tag(env, name: str) -> Optional[str]:
    name = (name or "").strip()
    if not name:
        return None
    row = await env.DB.prepare("SELECT id FROM tags WHERE name=?").bind(name).first()
    if row:
        return row.id
    tag_id = "legacy-tag-" + hashlib.sha256(name.lower().encode("utf-8")).hexdigest()[:24]
    await env.DB.prepare("INSERT OR IGNORE INTO tags (id,name) VALUES (?,?)").bind(tag_id, name).run()
    return tag_id


async def _legacy_ensure_user_exists(env, enc: str, user_id: str, label: str = "Legacy User"):
    row = await env.DB.prepare("SELECT id FROM users WHERE id=?").bind(user_id).first()
    if row:
        return
    username = re.sub(r"[^a-z0-9_-]+", "-", label.lower()).strip("-") or "legacy-user"
    username = f"{username}-{hashlib.sha256(user_id.encode('utf-8')).hexdigest()[:8]}"
    email = f"{username}@alphaonelabs.invalid"
    await env.DB.prepare(
        "INSERT OR IGNORE INTO users"
        " (id,username_hash,email_hash,name,username,email,password_hash,role,email_verified)"
        " VALUES (?,?,?,?,?,?,?,?,?)"
    ).bind(
        user_id,
        blind_index(username, enc),
        blind_index(email, enc),
        await encrypt_aes(label, enc),
        await encrypt_aes(username, enc),
        await encrypt_aes(email, enc),
        hash_password(str(uuid.uuid4()), username),
        await encrypt_aes("host", enc),
        1,
    ).run()


def _guest_cart_token(req) -> str:
    token = (req.headers.get("X-Guest-Cart") or "").strip()
    if not re.fullmatch(r"gct_[A-Za-z0-9._:-]{24,180}", token):
        return ""
    return token


def _guest_cart_id(req, env) -> str:
    token = _guest_cart_token(req)
    if not token:
        return ""
    secret = getattr(env, "JWT_SECRET", "") or getattr(env, "SECRET_KEY", "") or "guest-cart"
    digest = hashlib.sha256((token + ":" + secret).encode("utf-8")).hexdigest()
    return "guest:" + digest[:48]


def _human_cart_check(req, body: Dict[str, Any]):
    """Minimal friction check for guest cart mutations.

    This is intentionally not a hard identity challenge. It blocks the cheapest
    scripted cart-fill attempts while keeping guest checkout lightweight.
    """
    for field in ("website", "homepage", "company_website", "url"):
        if str(body.get(field) or "").strip():
            return False, "Cart request did not pass the human check"

    user_agent = (req.headers.get("User-Agent") or "").strip()
    if len(user_agent) < 8:
        return False, "Cart request did not pass the human check"

    fetch_site = (req.headers.get("Sec-Fetch-Site") or "").strip().lower()
    if fetch_site and fetch_site not in {"same-origin", "none"}:
        return False, "Cart request did not pass the human check"

    try:
        started = int(float(body.get("human_started_at") or 0))
        confirmed = int(float(body.get("human_confirmed_at") or 0))
    except Exception:
        return False, "Cart request did not pass the human check"

    now_ms = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
    elapsed = confirmed - started
    if elapsed < 350 or elapsed > 24 * 60 * 60 * 1000:
        return False, "Please try again"
    if started < now_ms - 24 * 60 * 60 * 1000 or confirmed > now_ms + 5 * 60 * 1000:
        return False, "Please try again"

    return True, ""


def _cart_owner(req, env, body: Optional[Dict[str, Any]] = None, require_human: bool = False):
    user = verify_token(req.headers.get("Authorization") or "", env.JWT_SECRET)
    if user:
        return {"kind": "user", "user_id": user["id"], "guest_id": "", "user": user}, None

    guest_id = _guest_cart_id(req, env)
    if not guest_id:
        return None, err("Authentication or guest cart token required", 401)

    if require_human:
        ok_human, message = _human_cart_check(req, body or {})
        if not ok_human:
            return None, err(message or "Cart request did not pass the human check", 429)

    return {"kind": "guest", "user_id": "", "guest_id": guest_id, "user": None}, None


async def _active_cart_id(env, owner: Dict[str, Any], create: bool = True) -> str:
    if owner["kind"] == "user":
        row = await env.DB.prepare(
            "SELECT id FROM activity_carts WHERE user_id=? AND owner_kind='user' AND status='open' ORDER BY created_at DESC LIMIT 1"
        ).bind(owner["user_id"]).first()
    else:
        row = await env.DB.prepare(
            "SELECT id FROM activity_carts WHERE guest_id=? AND owner_kind='guest' AND status='open' ORDER BY created_at DESC LIMIT 1"
        ).bind(owner["guest_id"]).first()
    if row:
        return row.id
    if not create:
        return ""
    cart_id = new_id()
    if owner["kind"] == "user":
        await env.DB.prepare(
            "INSERT INTO activity_carts (id,user_id,guest_id,owner_kind,status,currency) VALUES (?,?,?,?,?,?)"
        ).bind(
            cart_id,
            owner["user_id"],
            "",
            "user",
            "open",
            "USD",
        ).run()
    else:
        await env.DB.prepare(
            "INSERT INTO activity_carts (id,user_id,guest_id,owner_kind,status,currency) VALUES (?,NULL,?,?,?,?)"
        ).bind(
            cart_id,
            owner["guest_id"],
            "guest",
            "open",
            "USD",
        ).run()
    return cart_id


async def _cart_payload(env, owner: Dict[str, Any]):
    cart_id = await _active_cart_id(env, owner, create=False)
    if not cart_id:
        return {"cart": None, "items": [], "subtotal_cents": 0, "currency": "USD", "owner_kind": owner["kind"]}
    res = await env.DB.prepare(
        "SELECT ci.id,ci.activity_id,ci.session_id,ci.quantity,ci.unit_price_cents,ci.title_snapshot,"
        "a.title,a.status,a.slug,a.image_url"
        " FROM activity_cart_items ci"
        " JOIN activities a ON a.id=ci.activity_id"
        " WHERE ci.cart_id=? ORDER BY ci.created_at ASC"
    ).bind(cart_id).all()
    items = []
    subtotal = 0
    for r in res.results or []:
        quantity = int(r.quantity or 1)
        unit_price = int(r.unit_price_cents or 0)
        line_total = quantity * unit_price
        subtotal += line_total
        items.append({
            "id": r.id,
            "activity_id": r.activity_id,
            "session_id": r.session_id or "",
            "title": r.title or r.title_snapshot,
            "slug": getattr(r, "slug", "") or "",
            "status": getattr(r, "status", "") or "",
            "image_url": getattr(r, "image_url", "") or "",
            "quantity": quantity,
            "unit_price_cents": unit_price,
            "line_total_cents": line_total,
        })
    return {
        "cart": {"id": cart_id, "status": "open", "owner_kind": owner["kind"]},
        "items": items,
        "subtotal_cents": subtotal,
        "currency": "USD",
        "owner_kind": owner["kind"],
    }


async def api_get_cart(req, env):
    owner, owner_err = _cart_owner(req, env)
    if owner_err:
        return owner_err
    return json_resp(await _cart_payload(env, owner))


async def api_add_cart_item(req, env):
    body, bad_resp = await parse_json_object(req)
    if bad_resp:
        return bad_resp
    owner, owner_err = _cart_owner(req, env, body, require_human=True)
    if owner_err:
        return owner_err
    activity_id = _legacy_text(body.get("activity_id")).strip()
    session_id = _legacy_text(body.get("session_id")).strip()
    if not activity_id:
        return err("activity_id is required")
    act = await env.DB.prepare(
        "SELECT id,title,price_cents,status FROM activities WHERE id=?"
    ).bind(activity_id).first()
    if not act:
        return err("Activity not found", 404)
    if getattr(act, "status", "") == "waitlist":
        return err("This class is in the waiting room. Express interest instead.", 400)
    cart_id = await _active_cart_id(env, owner, create=True)
    if owner["kind"] == "guest":
        count_row = await env.DB.prepare(
            "SELECT COUNT(*) AS cnt FROM activity_cart_items WHERE cart_id=?"
        ).bind(cart_id).first()
        if count_row and int(getattr(count_row, "cnt", 0) or 0) >= 20:
            return err("Guest carts are limited to 20 activities", 400)
    item_id = new_id()
    await env.DB.prepare(
        "INSERT OR IGNORE INTO activity_cart_items"
        " (id,cart_id,activity_id,session_id,quantity,unit_price_cents,title_snapshot)"
        " VALUES (?,?,?,?,?,?,?)"
    ).bind(
        item_id,
        cart_id,
        activity_id,
        session_id,
        1,
        int(getattr(act, "price_cents", 0) or 0),
        act.title or "",
    ).run()
    await env.DB.prepare(
        "UPDATE activity_carts SET updated_at=datetime('now') WHERE id=?"
    ).bind(cart_id).run()
    return json_resp(await _cart_payload(env, owner))


async def api_remove_cart_item(req, env, item_id: str):
    owner, owner_err = _cart_owner(req, env)
    if owner_err:
        return owner_err
    cart_id = await _active_cart_id(env, owner, create=False)
    if not cart_id:
        return json_resp(await _cart_payload(env, owner))
    await env.DB.prepare(
        "DELETE FROM activity_cart_items WHERE id=? AND cart_id=?"
    ).bind(item_id, cart_id).run()
    await env.DB.prepare(
        "UPDATE activity_carts SET updated_at=datetime('now') WHERE id=?"
    ).bind(cart_id).run()
    return json_resp(await _cart_payload(env, owner))


async def api_clear_cart(req, env):
    owner, owner_err = _cart_owner(req, env)
    if owner_err:
        return owner_err
    cart_id = await _active_cart_id(env, owner, create=False)
    if cart_id:
        await env.DB.prepare("DELETE FROM activity_cart_items WHERE cart_id=?").bind(cart_id).run()
        await env.DB.prepare(
            "UPDATE activity_carts SET updated_at=datetime('now') WHERE id=?"
        ).bind(cart_id).run()
    return json_resp(await _cart_payload(env, owner))


async def _stripe_form_request(env, path: str, fields: Dict[str, Any]):
    secret = getattr(env, "STRIPE_SECRET_KEY", "") or ""
    if not secret:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")
    body = urlencode({k: str(v) for k, v in fields.items()})
    options = to_js(
        {
            "method": "POST",
            "headers": {
                "Authorization": "Bearer " + secret,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            "body": body,
        },
        dict_converter=js.Object.fromEntries,
    )
    resp = await js.fetch("https://api.stripe.com/v1" + path, options)
    text = await resp.text()
    try:
        data = json.loads(text or "{}")
    except Exception:
        data = {"raw": text}
    if resp.status < 200 or resp.status >= 300:
        message = data.get("error", {}).get("message") if isinstance(data.get("error"), dict) else None
        raise RuntimeError(message or f"Stripe request failed with status {resp.status}")
    return data


async def _stripe_get_request(env, path: str):
    secret = getattr(env, "STRIPE_SECRET_KEY", "") or ""
    if not secret:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")
    options = to_js(
        {
            "method": "GET",
            "headers": {"Authorization": "Bearer " + secret},
        },
        dict_converter=js.Object.fromEntries,
    )
    resp = await js.fetch("https://api.stripe.com/v1" + path, options)
    text = await resp.text()
    try:
        data = json.loads(text or "{}")
    except Exception:
        data = {"raw": text}
    if resp.status < 200 or resp.status >= 300:
        message = data.get("error", {}).get("message") if isinstance(data.get("error"), dict) else None
        raise RuntimeError(message or f"Stripe request failed with status {resp.status}")
    return data


async def api_create_checkout(req, env):
    body, bad_resp = await parse_json_object(req)
    if bad_resp:
        return bad_resp
    owner, owner_err = _cart_owner(req, env, body, require_human=True)
    if owner_err:
        return owner_err
    cart = await _cart_payload(env, owner)
    cart_id = (cart.get("cart") or {}).get("id") or ""
    items = cart.get("items") or []
    paid_items = [i for i in items if int(i.get("unit_price_cents") or 0) > 0]
    if not cart_id or not items:
        return err("Add at least one activity to your cart before checkout", 400)

    if not paid_items:
        enrolled = 0
        if owner["kind"] == "user":
            for item in items:
                try:
                    insert_res = await env.DB.prepare(
                        "INSERT OR IGNORE INTO enrollments (id,activity_id,user_id,role,status) VALUES (?,?,?,?,?)"
                    ).bind(new_id(), item.get("activity_id", ""), owner["user_id"], "participant", "active").run()
                    meta = getattr(insert_res, "meta", None)
                    changes = meta.get("changes") if isinstance(meta, dict) else getattr(meta, "changes", None)
                    if changes != 0:
                        enrolled += 1
                except Exception as exc:
                    await capture_exception(exc, req, env, "api_create_checkout.free_enroll")
        free_session_id = "free_" + new_id()
        if owner["kind"] == "user":
            await env.DB.prepare(
                "INSERT INTO activity_checkout_sessions"
                " (id,user_id,guest_id,owner_kind,cart_id,stripe_session_id,status,amount_total,currency,completed_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,datetime('now'))"
            ).bind(
                new_id(),
                owner["user_id"],
                "",
                "user",
                cart_id,
                free_session_id,
                "paid",
                0,
                "USD",
            ).run()
        else:
            await env.DB.prepare(
                "INSERT INTO activity_checkout_sessions"
                " (id,user_id,guest_id,owner_kind,cart_id,stripe_session_id,status,amount_total,currency,completed_at)"
                " VALUES (?,NULL,?,?,?,?,?,?,?,datetime('now'))"
            ).bind(
                new_id(),
                owner["guest_id"],
                "guest",
                cart_id,
                free_session_id,
                "paid",
                0,
                "USD",
            ).run()
        if owner["kind"] == "user":
            await env.DB.prepare(
                "UPDATE activity_carts SET status='checked_out', updated_at=datetime('now') WHERE id=? AND user_id=? AND owner_kind='user'"
            ).bind(cart_id, owner["user_id"]).run()
            return ok({"free_checkout": True, "enrolled": enrolled, "guest": False, "session_id": free_session_id}, "Free activities joined")
        await env.DB.prepare(
            "UPDATE activity_carts SET status='checked_out', updated_at=datetime('now') WHERE id=? AND guest_id=? AND owner_kind='guest'"
        ).bind(cart_id, owner["guest_id"]).run()
        return ok(
            {"free_checkout": True, "enrolled": 0, "guest": True, "session_id": free_session_id},
            "Free activities selected. Create or sign in to attach them to your dashboard.",
        )

    origin = f"{urlparse(req.url).scheme}://{urlparse(req.url).netloc}"
    fields: Dict[str, Any] = {
        "mode": "payment",
        "success_url": origin + "/checkout-success?session_id={CHECKOUT_SESSION_ID}",
        "cancel_url": origin + "/cart",
        "client_reference_id": owner["user_id"] or owner["guest_id"],
        "metadata[owner_kind]": owner["kind"],
        "metadata[user_id]": owner["user_id"] or "",
        "metadata[guest_id]": owner["guest_id"],
        "metadata[cart_id]": cart_id,
    }
    for idx, item in enumerate(paid_items):
        name = item.get("title") or "Alpha One Labs activity"
        fields[f"line_items[{idx}][quantity]"] = int(item.get("quantity") or 1)
        fields[f"line_items[{idx}][price_data][currency]"] = "usd"
        fields[f"line_items[{idx}][price_data][unit_amount]"] = int(item.get("unit_price_cents") or 0)
        fields[f"line_items[{idx}][price_data][product_data][name]"] = name[:120]
        fields[f"line_items[{idx}][price_data][product_data][metadata][activity_id]"] = item.get("activity_id", "")

    try:
        session = await _stripe_form_request(env, "/checkout/sessions", fields)
        if owner["kind"] == "user":
            await env.DB.prepare(
                "INSERT INTO activity_checkout_sessions"
                " (id,user_id,guest_id,owner_kind,cart_id,stripe_session_id,status,amount_total,currency)"
                " VALUES (?,?,?,?,?,?,?,?,?)"
                " ON CONFLICT(stripe_session_id) DO UPDATE SET status=excluded.status,amount_total=excluded.amount_total"
            ).bind(
                new_id(),
                owner["user_id"],
                "",
                "user",
                cart_id,
                session.get("id", ""),
                session.get("payment_status", "pending"),
                int(session.get("amount_total") or cart.get("subtotal_cents") or 0),
                (session.get("currency") or "usd").upper(),
            ).run()
        else:
            await env.DB.prepare(
                "INSERT INTO activity_checkout_sessions"
                " (id,user_id,guest_id,owner_kind,cart_id,stripe_session_id,status,amount_total,currency)"
                " VALUES (?,NULL,?,?,?,?,?,?,?)"
                " ON CONFLICT(stripe_session_id) DO UPDATE SET status=excluded.status,amount_total=excluded.amount_total"
            ).bind(
                new_id(),
                owner["guest_id"],
                "guest",
                cart_id,
                session.get("id", ""),
                session.get("payment_status", "pending"),
                int(session.get("amount_total") or cart.get("subtotal_cents") or 0),
                (session.get("currency") or "usd").upper(),
            ).run()
        return ok({"checkout_url": session.get("url"), "session_id": session.get("id")}, "Checkout created")
    except Exception as exc:
        await capture_exception(exc, req, env, "api_create_checkout")
        return err(str(exc), 500)


async def api_complete_checkout(req, env):
    body, bad_resp = await parse_json_object(req)
    if bad_resp:
        return bad_resp
    owner, owner_err = _cart_owner(req, env)
    if owner_err:
        return owner_err
    session_id = _legacy_text(body.get("session_id")).strip()
    if not re.fullmatch(r"cs_[A-Za-z0-9_]+", session_id):
        return err("Valid Stripe checkout session_id is required", 400)
    try:
        session = await _stripe_get_request(env, "/checkout/sessions/" + quote(session_id, safe=""))
        metadata = session.get("metadata") or {}
        owner_kind = metadata.get("owner_kind") or "user"
        if owner_kind != owner["kind"]:
            return err("Checkout session does not belong to this cart", 403)
        if owner["kind"] == "user" and metadata.get("user_id") != owner["user_id"]:
            return err("Checkout session does not belong to this user", 403)
        if owner["kind"] == "guest" and metadata.get("guest_id") != owner["guest_id"]:
            return err("Checkout session does not belong to this guest cart", 403)
        if session.get("payment_status") != "paid":
            return err("Payment is not complete yet", 400)
        cart_id = metadata.get("cart_id") or ""
        res = await env.DB.prepare(
            "SELECT activity_id FROM activity_cart_items WHERE cart_id=?"
        ).bind(cart_id).all()
        enrolled = 0
        if owner["kind"] == "user":
            for row in res.results or []:
                try:
                    insert_res = await env.DB.prepare(
                        "INSERT OR IGNORE INTO enrollments (id,activity_id,user_id,role,status) VALUES (?,?,?,?,?)"
                    ).bind(new_id(), row.activity_id, owner["user_id"], "participant", "active").run()
                    meta = getattr(insert_res, "meta", None)
                    changes = meta.get("changes") if isinstance(meta, dict) else getattr(meta, "changes", None)
                    if changes != 0:
                        enrolled += 1
                except Exception as exc:
                    await capture_exception(exc, req, env, "api_complete_checkout.enroll")
            await env.DB.prepare(
                "UPDATE activity_carts SET status='checked_out', updated_at=datetime('now') WHERE id=? AND user_id=? AND owner_kind='user'"
            ).bind(cart_id, owner["user_id"]).run()
            await env.DB.prepare(
                "UPDATE activity_checkout_sessions SET status='paid', completed_at=datetime('now'), amount_total=? WHERE stripe_session_id=? AND user_id=? AND owner_kind='user'"
            ).bind(int(session.get("amount_total") or 0), session_id, owner["user_id"]).run()
            return ok({"enrolled": enrolled, "guest": False}, "Payment confirmed and activities unlocked")

        customer_details = session.get("customer_details") or {}
        guest_email = customer_details.get("email") or ""
        await env.DB.prepare(
            "UPDATE activity_carts SET status='checked_out', updated_at=datetime('now') WHERE id=? AND guest_id=? AND owner_kind='guest'"
        ).bind(cart_id, owner["guest_id"]).run()
        await env.DB.prepare(
            "UPDATE activity_checkout_sessions SET status='paid', completed_at=datetime('now'), amount_total=?, guest_email=? WHERE stripe_session_id=? AND guest_id=? AND owner_kind='guest'"
        ).bind(int(session.get("amount_total") or 0), guest_email, session_id, owner["guest_id"]).run()
        return ok(
            {"enrolled": 0, "guest": True},
            "Payment confirmed. Create or sign in to an account when you want these activities attached to your dashboard.",
        )
    except Exception as exc:
        await capture_exception(exc, req, env, "api_complete_checkout")
        return err(str(exc), 500)


async def api_list_learning_intents(req, env):
    parsed = urlparse(req.url)
    params = parse_qs(parsed.query)
    kind = (params.get("kind") or [""])[0]
    enc = env.ENCRYPTION_KEY
    if kind not in ("learn", "teach", ""):
        return err("kind must be learn or teach", 400)
    if kind:
        res = await env.DB.prepare(
            "SELECT li.id,li.kind,li.title,li.subject,li.description,li.status,li.created_at,u.name AS name_enc"
            " FROM learning_intents li JOIN users u ON u.id=li.user_id"
            " WHERE li.kind=? AND li.status='open' ORDER BY li.created_at DESC LIMIT 100"
        ).bind(kind).all()
    else:
        res = await env.DB.prepare(
            "SELECT li.id,li.kind,li.title,li.subject,li.description,li.status,li.created_at,u.name AS name_enc"
            " FROM learning_intents li JOIN users u ON u.id=li.user_id"
            " WHERE li.status='open' ORDER BY li.created_at DESC LIMIT 100"
        ).all()
    intents = []
    for row in res.results or []:
        intents.append({
            "id": row.id,
            "kind": row.kind,
            "title": row.title,
            "subject": row.subject,
            "description": await decrypt_aes(row.description or "", enc),
            "status": row.status,
            "created_at": row.created_at,
            "user_name": await decrypt_aes(row.name_enc or "", enc),
        })
    return json_resp({"intents": intents})


async def api_create_learning_intent(req, env):
    user = verify_token(req.headers.get("Authorization"), env.JWT_SECRET)
    if not user:
        return err("Authentication required", 401)
    body, bad_resp = await parse_json_object(req)
    if bad_resp:
        return bad_resp
    kind = _legacy_text(body.get("kind")).strip()
    title = _legacy_text(body.get("title")).strip()
    subject = _legacy_text(body.get("subject")).strip()
    description = _legacy_text(body.get("description")).strip()
    if kind not in ("learn", "teach"):
        return err("kind must be learn or teach")
    if not title:
        return err("title is required")
    intent_id = new_id()
    await env.DB.prepare(
        "INSERT INTO learning_intents (id,user_id,kind,title,subject,description,status)"
        " VALUES (?,?,?,?,?,?,?)"
    ).bind(
        intent_id,
        user["id"],
        kind,
        title,
        subject,
        await encrypt_aes(description, env.ENCRYPTION_KEY),
        "open",
    ).run()
    return ok({"id": intent_id}, "Request posted")


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
            if table_name.startswith("_"):
                continue
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


def _static_cache_control(ext: str) -> str:
    if ext in {"html", "json"}:
        return "public, max-age=60, s-maxage=300"
    return "public, max-age=31536000, s-maxage=31536000, immutable"


_SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(self), payment=(self)",
}


def _template_attr_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() not in {"", "0", "false", "no", "off"}


def _template_attr_int(attrs: Dict[str, str], name: str, default: int, minimum: int = 1, maximum: int = 250) -> int:
    try:
        return max(minimum, min(maximum, int(attrs.get(name, default))))
    except Exception:
        return default


def _parse_template_attrs(raw: str) -> Dict[str, str]:
    attrs: Dict[str, str] = {}
    for match in re.finditer(r"([A-Za-z_][\w-]*)(?:\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s%]+)))?", raw or ""):
        key = match.group(1).replace("-", "_")
        value = match.group(2) if match.group(2) is not None else match.group(3) if match.group(3) is not None else match.group(4)
        attrs[key] = "true" if value is None else str(value)
    return attrs


def _json_for_html(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def _money_label(cents: Any, currency: str = "USD") -> str:
    try:
        amount = int(cents or 0)
    except Exception:
        amount = 0
    if amount <= 0:
        return "Free"
    return f"{currency or 'USD'} {amount / 100:,.2f}"


def _activity_href(activity: Dict[str, Any]) -> str:
    ref = activity.get("slug") or activity.get("id") or ""
    return "/activity/" + quote(str(ref), safe="") if ref else "/activity"


def _activity_type_label(value: Any) -> str:
    labels = {
        "course": "Course",
        "meetup": "Meetup",
        "workshop": "Workshop",
        "seminar": "Seminar",
        "club": "Club",
        "event": "Event",
        "video": "Video",
        "study_group": "Study Group",
        "other": "Activity",
    }
    raw = str(value or "").strip()
    return labels.get(raw, raw.replace("_", " ").title() if raw else "Activity")


def _activity_score(activity: Dict[str, Any]) -> int:
    return (
        (100000 if activity.get("is_featured") else 0)
        + int(activity.get("interest_count") or 0) * 50
        + int(activity.get("participant_count") or 0) * 25
        + int(activity.get("session_count") or 0) * 10
        + (5 if activity.get("status") == "published" else 0)
    )


async def _server_list_activities(env, *, limit: int = 1000, atype: str = "", fmt: str = "", search: str = "", tag: str = "", status: str = "catalog") -> Dict[str, Any]:
    limit = max(1, min(1000, int(limit or 1000)))
    if status not in {"catalog", "published", "waitlist", "draft", "archived", "all"}:
        status = "catalog"
    enc = env.ENCRYPTION_KEY
    base_q = (
        "SELECT a.id,a.title,a.description,a.type,a.format,a.schedule_type,"
        "a.created_at,a.status,a.slug,a.image_url,a.price_cents,a.price_currency,"
        "a.max_students,a.level,a.is_featured,u.name AS host_name_enc,"
        "(SELECT COUNT(*) FROM enrollments WHERE activity_id=a.id AND status='active') AS participant_count,"
        "(SELECT COUNT(*) FROM activity_interest WHERE activity_id=a.id AND status='interested') AS interest_count,"
        "(SELECT COUNT(*) FROM sessions WHERE activity_id=a.id) AS session_count"
        " FROM activities a JOIN users u ON a.host_id=u.id"
    )

    async def fetch_rows():
        order = " ORDER BY a.is_featured DESC, a.created_at DESC LIMIT " + str(limit)
        join = ""
        clauses = []
        binds = []
        if tag:
            tag_row = await env.DB.prepare("SELECT id FROM tags WHERE name=?").bind(tag).first()
            if not tag_row:
                return _empty_d1_result()
            join = " JOIN activity_tags at2 ON at2.activity_id=a.id"
            clauses.append("at2.tag_id=?")
            binds.append(tag_row.id)
        if status == "catalog":
            clauses.append("COALESCE(a.status,'published') IN ('published','waitlist')")
        elif status != "all":
            clauses.append("a.status=?")
            binds.append(status)
        if atype:
            clauses.append("a.type=?")
            binds.append(atype)
        if fmt:
            clauses.append("a.format=?")
            binds.append(fmt)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        stmt = env.DB.prepare(base_q + join + where + order)
        return await stmt.bind(*binds).all() if binds else await stmt.all()

    try:
        res = await fetch_rows()
    except Exception as exc:
        if _is_no_such_table_error(exc):
            return {"activities": [], "pagination": {"page": 1, "page_size": limit, "total": 0, "total_pages": 1}}
        raise

    rows = list(res.results or [])
    tag_map = {}
    if rows:
        try:
            placeholders = ",".join(["?"] * len(rows))
            tag_res = await env.DB.prepare(
                "SELECT at2.activity_id,t.name FROM tags t JOIN activity_tags at2 ON at2.tag_id=t.id"
                f" WHERE at2.activity_id IN ({placeholders})"
            ).bind(*[row.id for row in rows]).all()
            for tag_row in tag_res.results or []:
                tag_map.setdefault(tag_row.activity_id, []).append(tag_row.name)
        except Exception:
            tag_map = {}

    activities = []
    search_l = (search or "").lower()
    for row in rows:
        desc = await decrypt_aes(row.description or "", enc)
        host_name = await decrypt_aes(row.host_name_enc or "", enc)
        if search_l and search_l not in (row.title or "").lower() and search_l not in (desc or "").lower():
            continue
        tags = tag_map.get(row.id, [])
        activities.append({
            "id": row.id,
            "title": row.title,
            "description": desc,
            "type": row.type,
            "format": row.format,
            "schedule_type": row.schedule_type,
            "status": getattr(row, "status", "published"),
            "slug": getattr(row, "slug", "") or "",
            "image_url": getattr(row, "image_url", "") or "",
            "price_cents": int(getattr(row, "price_cents", 0) or 0),
            "price_currency": getattr(row, "price_currency", "USD") or "USD",
            "max_students": getattr(row, "max_students", 0) or 0,
            "level": getattr(row, "level", "") or "",
            "is_featured": bool(getattr(row, "is_featured", 0)),
            "host_name": host_name,
            "participant_count": int(getattr(row, "participant_count", 0) or 0),
            "interest_count": int(getattr(row, "interest_count", 0) or 0),
            "session_count": int(getattr(row, "session_count", 0) or 0),
            "tags": tags,
            "created_at": row.created_at,
        })
    return {"activities": activities, "pagination": {"page": 1, "page_size": limit, "total": len(activities), "total_pages": 1}}


async def _server_featured_activities(env, limit: int) -> list:
    payload = await _server_list_activities(env, limit=max(25, limit))
    activities = payload.get("activities", [])
    return sorted(activities, key=_activity_score, reverse=True)[:limit]


def _server_activity_card_html(activity: Dict[str, Any], *, home: bool = False) -> str:
    title = _html_escape(activity.get("title", "Untitled activity"))
    desc = _html_escape((activity.get("description") or "")[:180])
    host = _html_escape(activity.get("host_name") or "Alpha One Labs")
    image = _html_escape(activity.get("image_url") or "")
    href = _html_escape(_activity_href(activity))
    price = _html_escape(_money_label(activity.get("price_cents"), activity.get("price_currency") or "USD"))
    level = _html_escape(activity.get("level") or "All levels")
    fmt = _html_escape((activity.get("format") or "activity").replace("_", " "))
    count = int(activity.get("participant_count") or 0)
    interest = int(activity.get("interest_count") or 0)
    tags = "".join(
        f'<span class="rounded-full bg-teal-50 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300 px-2.5 py-1 text-xs font-semibold">{_html_escape(tag)}</span>'
        for tag in (activity.get("tags") or [])[:3]
    )
    badge = "Featured" if activity.get("is_featured") else _html_escape(_activity_type_label(activity.get("type")))
    metrics = []
    if count > 0:
        metrics.append(f'<span><i class="fas fa-users mr-1 text-teal-500"></i>{count} enrolled</span>')
    if interest > 0:
        metrics.append(f'<span><i class="fas fa-hand-paper mr-1 text-orange-500"></i>{interest} interested</span>')
    metrics_html = ""
    if metrics:
        metrics_html = '<div class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">' + "".join(metrics) + '</div>'
    action_html = (
        '<div class="px-5 pb-5 mt-auto">'
        f'<span class="w-full min-h-11 bg-orange-500 hover:bg-orange-600 text-white font-semibold px-3 py-2 rounded-lg flex items-center justify-center">'
        '<i class="fas fa-circle-info mr-2"></i>View More Info</span>'
        '</div>'
    )
    return (
        '<article class="group h-full min-h-[36rem] bg-white dark:bg-gray-800 rounded-2xl shadow-md border border-gray-200 dark:border-gray-700 overflow-hidden hover:shadow-xl hover:-translate-y-1 transition-all duration-300 flex flex-col">'
        f'<a href="{href}" class="block">'
        '<div class="aspect-square bg-gray-100 dark:bg-gray-700 overflow-hidden">'
        f'<img src="{image}" alt="{title}" width="500" height="500" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" loading="lazy" decoding="async" fetchpriority="low" onerror="this.remove();">'
        '</div>'
        '<div class="p-5 flex flex-col flex-1">'
        '<div class="flex items-center justify-between gap-3 mb-3">'
        f'<span class="rounded-full bg-teal-100 dark:bg-teal-900/40 text-teal-700 dark:text-teal-300 px-3 py-1 text-xs font-bold uppercase tracking-wide">{badge}</span>'
        f'<span class="text-sm font-black text-orange-600 dark:text-orange-300">{price}</span>'
        '</div>'
        f'<h3 class="text-lg font-black text-gray-900 dark:text-gray-100 leading-snug mb-2 min-h-[3.25rem]">{title}</h3>'
        f'<p class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed line-clamp-3 mb-4 min-h-[4.75rem]">{desc}</p>'
        f'<div class="text-xs text-gray-500 dark:text-gray-400 mb-3 min-h-[1.25rem]">by {host} · {fmt} · {level}</div>'
        f'<div class="flex flex-wrap gap-2 mb-4 min-h-[4.5rem] content-start">{tags}</div>'
        f'{metrics_html}'
        f'</div></a><a href="{href}" class="block">{action_html}</a></article>'
    )


async def _server_activity_detail_payload(env, activity_ref: str) -> Optional[Dict[str, Any]]:
    if not activity_ref:
        return None
    enc = env.ENCRYPTION_KEY
    try:
        act = await env.DB.prepare(
            "SELECT a.*,u.name AS host_name_enc,u.id AS host_uid FROM activities a JOIN users u ON a.host_id=u.id WHERE a.slug=?"
        ).bind(activity_ref).first()
        if not act:
            act = await env.DB.prepare(
                "SELECT a.*,u.name AS host_name_enc,u.id AS host_uid FROM activities a JOIN users u ON a.host_id=u.id WHERE a.id=?"
            ).bind(activity_ref).first()
    except Exception as exc:
        if _is_no_such_table_error(exc):
            return None
        raise
    if not act:
        return None

    ses_res = await env.DB.prepare(
        "SELECT id,title,description,start_time,end_time,location,created_at FROM sessions WHERE activity_id=? ORDER BY start_time"
    ).bind(act.id).all()
    sessions = []
    for s in ses_res.results or []:
        sessions.append({
            "id": s.id,
            "title": s.title,
            "description": None,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "location": None,
        })

    t_res = await env.DB.prepare(
        "SELECT t.name FROM tags t JOIN activity_tags at2 ON at2.tag_id=t.id WHERE at2.activity_id=?"
    ).bind(act.id).all()
    count_row = await env.DB.prepare(
        "SELECT COUNT(*) AS cnt FROM enrollments WHERE activity_id=? AND status='active'"
    ).bind(act.id).first()
    interest_count_row = await env.DB.prepare(
        "SELECT COUNT(*) AS cnt FROM activity_interest WHERE activity_id=? AND status='interested'"
    ).bind(act.id).first()

    legacy_metadata = {}
    raw_metadata = await decrypt_aes(getattr(act, "legacy_metadata", "") or "", enc)
    if raw_metadata:
        try:
            parsed_metadata = json.loads(raw_metadata)
            if isinstance(parsed_metadata, dict):
                legacy_metadata = parsed_metadata
        except Exception:
            legacy_metadata = {}

    return {
        "activity": {
            "id": act.id,
            "title": act.title,
            "description": await decrypt_aes(act.description or "", enc),
            "learning_objectives": await decrypt_aes(getattr(act, "learning_objectives", "") or "", enc),
            "prerequisites": await decrypt_aes(getattr(act, "prerequisites", "") or "", enc),
            "type": act.type,
            "format": act.format,
            "schedule_type": act.schedule_type,
            "status": getattr(act, "status", "published"),
            "slug": getattr(act, "slug", "") or "",
            "image_url": getattr(act, "image_url", "") or "",
            "price_cents": int(getattr(act, "price_cents", 0) or 0),
            "price_currency": getattr(act, "price_currency", "USD") or "USD",
            "max_students": getattr(act, "max_students", 0) or 0,
            "invite_only": bool(getattr(act, "invite_only", 0)),
            "allow_individual_sessions": bool(getattr(act, "allow_individual_sessions", 0)),
            "subject_id": getattr(act, "subject_id", "") or "",
            "level": getattr(act, "level", "") or "",
            "is_featured": bool(getattr(act, "is_featured", 0)),
            "external_url": legacy_metadata.get("video_url") or legacy_metadata.get("external_url") or legacy_metadata.get("url") or "",
            "host_name": await decrypt_aes(act.host_name_enc or "", enc),
            "participant_count": count_row.cnt if count_row else 0,
            "interest_count": interest_count_row.cnt if interest_count_row else 0,
            "tags": [t.name for t in (t_res.results or [])],
            "created_at": act.created_at,
        },
        "sessions": sessions,
        "is_enrolled": False,
        "is_host": False,
        "is_completed": False,
        "user_interested": False,
        "interest": None,
        "completion": None,
        "enrollment": None,
    }


def _template_activity_ref(req) -> str:
    if not req:
        return ""
    parsed = urlparse(req.url)
    path_match = re.fullmatch(r"/activity/([^/]+)/?", parsed.path)
    if path_match:
        return unquote(path_match.group(1))
    params = parse_qs(parsed.query)
    return (params.get("slug") or params.get("id") or [""])[0]


async def _server_waiting_rooms_html(env, kind: str = "learn") -> str:
    kind = kind if kind in {"learn", "teach", ""} else "learn"
    enc = env.ENCRYPTION_KEY
    try:
        if kind:
            res = await env.DB.prepare(
                "SELECT li.id,li.kind,li.title,li.subject,li.description,li.status,li.created_at,u.name AS name_enc"
                " FROM learning_intents li JOIN users u ON u.id=li.user_id"
                " WHERE li.kind=? AND li.status='open' ORDER BY li.created_at DESC LIMIT 100"
            ).bind(kind).all()
        else:
            res = await env.DB.prepare(
                "SELECT li.id,li.kind,li.title,li.subject,li.description,li.status,li.created_at,u.name AS name_enc"
                " FROM learning_intents li JOIN users u ON u.id=li.user_id"
                " WHERE li.status='open' ORDER BY li.created_at DESC LIMIT 100"
            ).all()
    except Exception as exc:
        if _is_no_such_table_error(exc):
            res = _empty_d1_result()
        else:
            raise
    rows = []
    for row in res.results or []:
        desc = await decrypt_aes(row.description or "", enc)
        if desc == "[decryption error]":
            desc = row.description or ""
        user_name = await decrypt_aes(row.name_enc or "", enc)
        rows.append(
            '<article class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-5 hover:bg-gray-50 dark:hover:bg-gray-700">'
            '<div class="flex items-start gap-4"><div class="w-11 h-11 rounded-full bg-teal-100 dark:bg-teal-900 flex items-center justify-center text-teal-600 dark:text-teal-300"><i class="fas fa-door-open"></i></div>'
            '<div class="flex-1"><div class="flex flex-wrap justify-between gap-2">'
            f'<h3 class="font-bold text-lg">{_html_escape(row.title)}</h3>'
            f'<span class="text-xs rounded-full bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300 px-3 py-1">{_html_escape(row.subject or "General")}</span>'
            '</div>'
            f'<p class="text-sm text-gray-600 dark:text-gray-300 mt-2 whitespace-pre-wrap">{_html_escape(desc)}</p>'
            f'<p class="text-xs text-gray-500 dark:text-gray-400 mt-3">Requested by {_html_escape(user_name or "Community member")}</p>'
            '</div></div></article>'
        )
    marker = '<span data-server-waiting-rooms="true" class="hidden"></span>'
    if not rows:
        return marker + '<div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-8 text-center text-gray-500">No open waiting rooms yet.</div>'
    return marker + "".join(rows)


async def _server_records_for_models(env, models: list, owner_user_id: Optional[str] = None, limit: int = 250) -> list:
    if not models:
        return []
    placeholders = ",".join(["?"] * len(models))
    binds = list(models)
    owner_clause = ""
    if owner_user_id is not None:
        owner_clause = " AND user_id=?"
        binds.append(owner_user_id)
    binds.append(max(1, min(500, int(limit or 250))))
    try:
        res = await env.DB.prepare(
            "SELECT legacy_model,legacy_pk,payload,created_at,updated_at FROM legacy_records"
            f" WHERE legacy_model IN ({placeholders})" + owner_clause +
            " ORDER BY updated_at DESC LIMIT ?"
        ).bind(*binds).all()
    except Exception as exc:
        if _is_no_such_table_error(exc):
            return []
        raise
    records = []
    for row in res.results or []:
        try:
            payload = await decrypt_aes(row.payload or "", env.ENCRYPTION_KEY)
            record = json.loads(payload) if payload else {}
            if isinstance(record, dict):
                summary = _legacy_feature_summary(record)
                if _is_test_success_story_record(summary):
                    continue
                records.append(summary)
        except Exception as exc:
            await capture_exception(exc, where="template_records.decrypt")
    return records


async def _template_records(context: Dict[str, Any], env, models: list, owner_user_id: Optional[str] = None) -> list:
    cache = context.setdefault("_records_cache", {})
    key = ",".join(models) + "|" + (owner_user_id or "public")
    if key not in cache:
        cache[key] = await _server_records_for_models(env, models, owner_user_id=owner_user_id)
    return cache[key]


async def _render_data_tag(name: str, attrs: Dict[str, str], env, req, context: Dict[str, Any]) -> str:
    activity_ref = _template_activity_ref(req)

    parsed_query = parse_qs(urlparse(req.url).query) if req else {}

    def requested_activity_filter(name: str) -> str:
        return (attrs.get(name) or (parsed_query.get(name) or [""])[0] or "").strip()

    async def cached_activity_list(limit: int, atype: str = "", fmt: str = "", search: str = "", tag: str = "") -> Dict[str, Any]:
        cache = context.setdefault("_activity_list_cache", {})
        key = "|".join([str(limit), atype or "", fmt or "", search or "", tag or ""])
        if key not in cache:
            cache[key] = await _server_list_activities(env, limit=limit, atype=atype, fmt=fmt, search=search, tag=tag)
        return cache[key]

    if name == "featured_activities_json":
        limit = _template_attr_int(attrs, "limit", 3, 1, 12)
        return _json_for_html(await _server_featured_activities(env, limit))
    if name == "featured_activity_cards":
        limit = _template_attr_int(attrs, "limit", 3, 1, 12)
        activities = await _server_featured_activities(env, limit)
        if not activities:
            return '<div class="col-span-3 rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-8 text-center text-gray-500 dark:text-gray-400">No featured classes found yet.</div>'
        return "".join(_server_activity_card_html(a, home=True) for a in activities)
    if name == "activities_json":
        if activity_ref:
            return '<script id="server-activities-data" type="application/json">' + _json_for_html({"activities": [], "pagination": {"page": 1, "page_size": 0, "total": 0, "total_pages": 1}}) + '</script>'
        limit = _template_attr_int(attrs, "limit", 1000, 1, 1000)
        payload = await cached_activity_list(
            limit,
            requested_activity_filter("type"),
            requested_activity_filter("format"),
            requested_activity_filter("q"),
            requested_activity_filter("tag"),
        )
        return '<script id="server-activities-data" type="application/json">' + _json_for_html(payload) + '</script>'
    if name == "activity_cards":
        if activity_ref:
            return ""
        limit = _template_attr_int(attrs, "limit", 12, 1, 1000)
        payload = await cached_activity_list(
            max(limit, 1000),
            requested_activity_filter("type"),
            requested_activity_filter("format"),
            requested_activity_filter("q"),
            requested_activity_filter("tag"),
        )
        activities = payload.get("activities", [])[:limit]
        if not activities:
            return '<div class="col-span-3 rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-8 text-center text-gray-500 dark:text-gray-400">No activities found yet.</div>'
        return "".join(_server_activity_card_html(a) for a in activities)
    if name == "activity_detail_json":
        ref = _template_activity_ref(req)
        if not ref:
            return ""
        payload = await _server_activity_detail_payload(env, ref)
        if not payload:
            return ""
        return '<script id="server-activity-detail-data" type="application/json">' + _json_for_html(payload) + '</script>'
    if name == "waiting_rooms":
        return await _server_waiting_rooms_html(env, attrs.get("kind", "learn"))
    if name in {"records_list", "records_count"}:
        models = [m.strip() for m in (attrs.get("models") or "").split(",") if m.strip()]
        auth_required = _template_attr_bool(attrs.get("auth_required"), False)
        model_set = set(models)
        if model_set == FORUM_RECORD_MODELS:
            if name == "records_count":
                return str(len((await _server_forum_payload(env))["topics"]))
            return await _server_forum_records_html(env)
        if model_set == {"web.Meme"}:
            records = await _template_records(context, env, models, owner_user_id=None)
            if name == "records_count":
                return str(len(records))
            return _ssr_meme_grid_html(records)
        owner_user_id = None
        if auth_required or any(model in SENSITIVE_RECORD_MODELS for model in models):
            user = verify_token(req.headers.get("Authorization") or "", env.JWT_SECRET) if req else None
            if not user:
                if name == "records_count":
                    return "0"
                return await _private_records_signin_html()
            owner_user_id = user["id"]
        records = await _template_records(context, env, models, owner_user_id=owner_user_id)
        if name == "records_count":
            return str(len(records))
        noun = attrs.get("noun") or "records"
        if not records:
            return f'<div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-8 text-center text-gray-500 dark:text-gray-400">No {_html_escape(noun)} found yet.</div>'
        return "".join(_ssr_record_card(record) for record in records)
    return "{% " + name + " " + " ".join(f'{k}=\"{v}\"' for k, v in attrs.items()) + " %}"


async def render_500(req, env):
    content = await _load_static_text(env, "500.html")
    if content:
        try:
            content = await _render_template_source(content, env, req, {})
        except Exception:
            content = None
    if not content:
        content = "<h1>500 - Server Error</h1><p>Please try again soon.</p>"
    return Response(
        content,
        status=500,
        headers={"Content-Type": "text/html; charset=utf-8", "Cache-Control": "public, max-age=30", **_CORS},
    )


async def _load_static_text(env, key: str) -> Optional[str]:
    normalized = (key or "").lstrip("/")
    if not normalized:
        normalized = "index.html"

    # Older Workers Sites binding used by the first Worker version.
    try:
        static_content = getattr(env, "__STATIC_CONTENT", None)
        if static_content is not None:
            value = await static_content.get(normalized, "text")
            if value is not None:
                return value
    except Exception:
        pass

    # Current Cloudflare Assets binding from wrangler.toml: [assets] binding = "ASSETS".
    try:
        assets = getattr(env, "ASSETS", None)
        if assets is not None:
            asset_url = "https://assets.local/" + normalized
            try:
                asset_req = js.Request.new(asset_url)
                resp = await assets.fetch(asset_req)
            except Exception:
                resp = await assets.fetch(asset_url)
            status = int(getattr(resp, "status", 0) or 0)
            if 200 <= status < 300:
                return await resp.text()
    except Exception:
        pass

    return None


async def _render_template_source(source: str, env, req=None, context: Optional[Dict[str, Any]] = None) -> str:
    context = context or {}
    block_re = re.compile(r"{%\s*block\s+([A-Za-z_][\w]*)\s*%}([\s\S]*?){%\s*endblock\s*%}")
    extends_match = re.search(r"{%\s*extends\s+[\"']([^\"']+)[\"']\s*%}", source)
    if extends_match:
        parent_key = extends_match.group(1).lstrip("/")
        parent = await _load_static_text(env, parent_key) or ""
        blocks = {m.group(1): m.group(2) for m in block_re.finditer(source)}
        def replace_parent_block(match):
            return blocks.get(match.group(1), match.group(2))
        html = block_re.sub(replace_parent_block, parent)
    else:
        html = re.sub(r"{%\s*extends\s+[\"'][^\"']+[\"']\s*%}", "", source)
        html = block_re.sub(lambda m: m.group(2), html)

    include_re = re.compile(r"{%\s*include\s+[\"']([^\"']+)[\"']\s*%}")
    while True:
        match = include_re.search(html)
        if not match:
            break
        include_key = match.group(1).lstrip("/")
        include = await _load_static_text(env, include_key) or ""
        html = html[:match.start()] + include + html[match.end():]

    tag_re = re.compile(r"{%\s*([A-Za-z_][\w]*)\s*([^%]*?)%}")
    while True:
        match = tag_re.search(html)
        if not match:
            break
        tag_name = match.group(1)
        if tag_name in {"endblock", "block", "extends", "include"}:
            replacement = ""
        else:
            replacement = await _render_data_tag(tag_name, _parse_template_attrs(match.group(2)), env, req, context)
        html = html[:match.start()] + replacement + html[match.end():]

    var_re = re.compile(r"{{\s*([A-Za-z_][\w.]*)\s*}}")
    def replace_var(match):
        value: Any = context
        for part in match.group(1).split('.'):
            if isinstance(value, dict):
                value = value.get(part, "")
            else:
                value = getattr(value, part, "")
        return _html_escape(value)
    return var_re.sub(replace_var, html)


async def serve_static(path: str, env, req=None):
    if path in ("/", ""):
        key = "index.html"
    else:
        key = path.lstrip("/")
        if "." not in key.split("/")[-1]:
            key += ".html"

    ext  = key.rsplit(".", 1)[-1] if "." in key else "html"
    mime = _MIME.get(ext, "text/plain")
    content = await _load_static_text(env, key)

    if content is None:
        if ext == "html":
            return await render_404(req, env, path)
        return Response(
            "404 - Not Found",
            status=404,
            headers={"Content-Type": mime, "Cache-Control": "public, max-age=60", **_CORS},
        )
    if ext == "html" and isinstance(content, str):
        try:
            content = await _render_template_source(content, env, req, {"path": urlparse(req.url).path if req else path})
            if '<div id="site-navbar"></div>' in content or '<div id="site-footer"></div>' in content:
                navbar = await _load_static_text(env, "partials/navbar.html")
                footer = await _load_static_text(env, "partials/footer.html")
                if navbar:
                    content = content.replace(
                        '<div id="site-navbar"></div>',
                        '<div id="site-navbar" data-inline="true">' + navbar + '</div>',
                    )
                if footer:
                    content = content.replace(
                        '<div id="site-footer"></div>',
                        '<div id="site-footer" data-inline="true">' + footer + '</div>',
                    )
        except Exception as exc:
            await capture_exception(exc, req, env, "serve_static.template")
    return Response(
        content,
        headers={
            "Content-Type": mime,
            "Cache-Control": _static_cache_control(ext),
            **_SECURITY_HEADERS,
            **_CORS,
        },
    )

class ClassroomDO(DurableObject):
    """WebSocket based virtual classroom Durable Object.

    Each room_id maps to one DO instance.  Connected clients share:
      - room_state   (participant list, broadcast on join/leave)
      - position_update (x/y movement relay)
      - chat_message  (basic text relay)
      - seat mgmt     (update_seat / leave_seat)
      - whiteboard_event / whiteboard_clear with persisted room replay
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
                    "can_interact":   bool(data.get("can_interact", True)),
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
        can_interact = authenticated_user is not None

        if authenticated_user:
            # Derive identity from the verified token, not from untrusted query params.
            participant_id = authenticated_user["id"]
            display_name = authenticated_user.get("username") or participant_id
        else:
            # Anonymous clients may view the classroom, but they are read-only.
            if token_param or not participant_param:
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
             if s.get("can_interact", True) and s["participant_id"] == participant_id),
            None,
        )
        already_connected = can_interact and existing is not None
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
            "can_interact":   can_interact,
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
            "can_interact":   can_interact,
        }

        try:
            server.send(json.dumps({
                "type":           "user_info",
                "session_id":     session_id,
                "participant_id": participant_id,
                "display_name":   display_name,
                "can_interact":   can_interact,
            }))
            whiteboard_events = await self.ctx.storage.get("whiteboard_events")
            if not isinstance(whiteboard_events, list):
                whiteboard_events = []
            server.send(json.dumps({
                "type": "whiteboard_state",
                "events": whiteboard_events[-1000:],
            }))
        except Exception as exc:
            await capture_exception(exc, request, self.env, "classroom_on_fetch.send_user_info")

        self._broadcast_room_state()

        if can_interact and not already_connected:
            self._broadcast(json.dumps({
                "type":           "participant_joined",
                "participant_id": participant_id,
                "display_name":   display_name,
            }), exclude_session_id=session_id)

        return Response(None, status=101, web_socket=client)

    async def on_webSocketMessage(self, ws, message):
        try:
            raw_message = message if isinstance(message, str) else message.decode("utf-8")
            if len(raw_message) > 8192:
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
        if not info.get("can_interact", True):
            if msg_type == "join":
                self._broadcast_room_state()
            return

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

        elif msg_type == "whiteboard_event":
            event = self._sanitize_whiteboard_event(data.get("event") if isinstance(data.get("event"), dict) else data)
            if not event:
                return
            event["participant_id"] = info["participant_id"]
            event["display_name"] = info["display_name"]
            event["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            try:
                events = await self.ctx.storage.get("whiteboard_events")
                if not isinstance(events, list):
                    events = []
                events.append(event)
                events = events[-1000:]
                await self.ctx.storage.put("whiteboard_events", events)
            except Exception as exc:
                await capture_exception(exc, None, self.env, "classroom.whiteboard_event.persist")
            self._broadcast(json.dumps({
                "type": "whiteboard_event",
                "event": event,
            }))

        elif msg_type == "whiteboard_clear":
            try:
                await self.ctx.storage.put("whiteboard_events", [])
            except Exception as exc:
                await capture_exception(exc, None, self.env, "classroom.whiteboard_clear.persist")
            self._broadcast(json.dumps({
                "type": "whiteboard_clear",
                "participant_id": info["participant_id"],
                "display_name": info["display_name"],
            }))

        elif msg_type == "whiteboard_undo":
            try:
                events = await self.ctx.storage.get("whiteboard_events")
                if not isinstance(events, list):
                    events = []
                for idx in range(len(events) - 1, -1, -1):
                    event = events[idx]
                    if isinstance(event, dict) and event.get("participant_id") == info["participant_id"]:
                        events.pop(idx)
                        break
                await self.ctx.storage.put("whiteboard_events", events)
                self._broadcast(json.dumps({
                    "type": "whiteboard_state",
                    "events": events[-1000:],
                    "participant_id": info["participant_id"],
                    "display_name": info["display_name"],
                }))
            except Exception as exc:
                await capture_exception(exc, None, self.env, "classroom.whiteboard_undo")

        
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
                if (other_info.get("can_interact", True)
                        and other_info["seat_id"] == seat_id
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
        if not info.get("can_interact", True):
            return

        still_connected = any(
            s.get("can_interact", True) and s["participant_id"] == pid for s in self.sessions.values()
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

    def _whiteboard_point(self, value):
        if not isinstance(value, dict):
            return None
        try:
            x = float(value.get("x", 0))
            y = float(value.get("y", 0))
        except (TypeError, ValueError):
            return None
        return {"x": max(0.0, min(1.0, x)), "y": max(0.0, min(1.0, y))}

    def _sanitize_whiteboard_event(self, value):
        if not isinstance(value, dict):
            return None
        start = self._whiteboard_point(value.get("from"))
        end = self._whiteboard_point(value.get("to")) or start
        if not start:
            return None
        kind = value.get("kind") or value.get("tool") or "stroke"
        if kind not in {"stroke", "line", "rectangle", "circle", "arrow", "text"}:
            kind = "stroke"
        if kind != "text" and not end:
            return None
        color = value.get("color", "#0f766e")
        if not isinstance(color, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
            color = "#0f766e"
        mode = value.get("mode") or ("text" if kind == "text" else "pen")
        if mode not in {"pen", "highlighter", "eraser", "shape", "text"}:
            mode = "pen"
        try:
            size = int(value.get("size", 4))
        except (TypeError, ValueError):
            size = 4
        try:
            alpha = float(value.get("alpha", 0.3 if mode == "highlighter" else 1))
        except (TypeError, ValueError):
            alpha = 1
        text = value.get("text", "")
        if not isinstance(text, str):
            text = ""
        event_id = value.get("event_id", "")
        if not isinstance(event_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", event_id):
            event_id = str(uuid.uuid4())
        return {
            "event_id": event_id,
            "kind": kind,
            "from": start,
            "to": end,
            "color": color,
            "size": max(1, min(32, size)),
            "mode": mode,
            "alpha": max(0.05, min(1.0, alpha)),
            "text": text[:240],
        }

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
            if not info.get("can_interact", True):
                continue
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
                "can_interact":   info.get("can_interact", True),
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
                    "can_interact": bool(data.get("can_interact", True)),
                }
                if self.sessions[session_id]["can_interact"] and user_id not in self.presence:
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

        authenticated_user = verify_token(token_param or "", self.env.JWT_SECRET) if token_param else None
        can_interact = authenticated_user is not None

        if authenticated_user:
            user_id = str(authenticated_user.get("id", ""))
            display_name = str(authenticated_user.get("username") or user_id)
        else:
            if token_param or not user_param:
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
        if not can_interact:
            existing = {
                "x": 0.5,
                "y": 0.5,
                "emoji": "",
                "hand_raised": False,
                "display_name": display_name,
            }
        elif existing is None:
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
            "can_interact": can_interact,
        })
        server.serializeAttachment(attachment)

        self.sessions[session_id] = {
            "ws": server,
            "user_id": user_id,
            "display_name": display_name,
            "can_interact": can_interact,
        }

        self._send_welcome(server, session_id, user_id)
        if can_interact:
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

        msg_type = data.get("type", "")
        if msg_type == "join":
            self._send_welcome(ws, sid, user_id)
            return

        if not info.get("can_interact", True):
            return

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
        if not info.get("can_interact", True):
            return

        still_connected = any(
            s.get("can_interact", True) and s["user_id"] == user_id
            for s in self.sessions.values()
        )
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
                    "can_interact": info.get("can_interact", True),
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
    admin_path_slash = admin_path + "/" if admin_path != "/" else admin_path
    admin_api_counts_path = admin_path.rstrip("/") + "/api/table-counts"

    if method == "OPTIONS":
        return Response("", status=204, headers=_CORS)

    language_target = _language_prefixed_target(path)
    if method == "GET" and language_target is not None:
        if language_target:
            return _redirect_to_current_route(request, language_target)
        return await render_404(request, env, path)

    route_path = path[:-5] if path.endswith(".html") else path
    if len(route_path) > 1 and route_path.endswith("/"):
        route_path = route_path.rstrip("/")
    if method == "GET" and route_path in ("/activity", "/activity.html"):
        activity_query = parse_qs(urlparse(request.url).query)
        if activity_query.get("slug") or activity_query.get("id"):
            return await serve_static("/activity-detail.html", env, request)
    if method == "GET" and re.fullmatch(r"/activity/[^/]+", route_path):
        return await serve_static("/activity-detail.html", env, request)
    m_blog_detail = re.fullmatch(r"/blog/([^/]+)", route_path)
    if method == "GET" and m_blog_detail:
        return await render_blog_detail(request, env, unquote(m_blog_detail.group(1)))
    m_forum_topic = re.fullmatch(r"/forum/topic/([^/]+)", route_path)
    if method == "GET" and m_forum_topic:
        return await render_forum_topic_detail(request, env, unquote(m_forum_topic.group(1)))
    m_forum_old_topic = re.fullmatch(r"/forum/[^/]+/([^/]+)", route_path)
    if method == "GET" and m_forum_old_topic:
        return await render_forum_topic_detail(request, env, unquote(m_forum_old_topic.group(1)))
    m_forum_category = re.fullmatch(r"/forum/([^/]+)", route_path)
    if method == "GET" and m_forum_category:
        return await serve_static("/forum.html", env, request)
    m_meme_detail = re.fullmatch(r"/memes/([^/]+)", route_path)
    if method == "GET" and m_meme_detail:
        return await render_meme_detail(request, env, unquote(m_meme_detail.group(1)))
    if method == "GET" and route_path in SSR_RECORD_PAGES:
        static_page = STATIC_CLEAN_ROUTES.get(route_path)
        if static_page:
            return await serve_static(static_page, env, request)
        return await render_ssr_record_page(request, env, route_path, SSR_RECORD_PAGES[route_path])

    if method == "GET" and route_path in STATIC_CLEAN_ROUTES:
        return await serve_static(STATIC_CLEAN_ROUTES[route_path], env, request)

    if path in (admin_path, admin_path_slash) and method == "GET":
        if not _is_basic_auth_valid(request, env):
            return _unauthorized_basic()
        return await serve_static("/admin.html", env, request)

    if path == admin_api_counts_path and method == "GET":
        return await api_admin_table_counts(request, env)

    if path in ("/legacy-features", "/legacy-features.html", "/features", "/features.html") and method == "GET":
        return await render_ssr_record_page(request, env, "/feature-votes", SSR_RECORD_PAGES["/feature-votes"])

    m_ref = re.fullmatch(r"/ref/([A-Za-z0-9_-]+)/?", path)
    if m_ref and method == "GET":
        location = "/login?" + urlencode({"tab": "register", "referral_code": m_ref.group(1)})
        return Response("", status=302, headers={"Location": location, **_CORS})

    if path.startswith("/media/") and method == "GET":
        return await serve_r2_media(path, env)

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

        if path == "/api/classes-near-me" and method == "GET":
            return await api_classes_near_me(request, env)

        if path == "/api/activities" and method == "GET":
            return await api_list_activities(request, env)

        if path == "/api/activities" and method == "POST":
            return await api_create_activity(request, env)

        m_complete = re.fullmatch(r"/api/activities/([A-Za-z0-9_-]+)/complete", path)
        if m_complete and method == "POST":
            return await api_complete_activity(m_complete.group(1), request, env)

        m_interest = re.fullmatch(r"/api/activities/([A-Za-z0-9_-]+)/interest", path)
        if m_interest and method == "POST":
            return await api_express_activity_interest(m_interest.group(1), request, env)

        m = re.fullmatch(r"/api/activities/([A-Za-z0-9_-]+)", path)
        if m and method == "GET":
            return await api_get_activity(m.group(1), request, env)

        if path == "/api/join" and method == "POST":
            return await api_join(request, env)

        if path == "/api/dashboard" and method == "GET":
            return await api_dashboard(request, env)

        if path == "/api/profile" and method in ("GET", "PATCH", "DELETE"):
            return await (api_delete_account(request, env) if method == "DELETE" else api_profile(request, env))

        if path == "/api/feedback" and method == "POST":
            return await api_feedback(request, env)

        if path == "/api/referral" and method == "GET":
            return await api_get_referral(request, env)

        if path == "/api/referral/leaderboard" and method == "GET":
            return await api_referral_leaderboard(request, env)

        if path == "/api/sessions" and method == "POST":
            return await api_create_session(request, env)

        if path == "/api/subjects" and method == "GET":
            return await api_list_subjects(request, env)

        if path == "/api/tags" and method == "GET":
            return await api_list_tags(request, env)

        if path == "/api/activity-tags" and method == "POST":
            return await api_add_activity_tags(request, env)

        if path == "/api/cart" and method == "GET":
            return await api_get_cart(request, env)
        if path == "/api/cart" and method == "DELETE":
            return await api_clear_cart(request, env)
        if path == "/api/cart/items" and method == "POST":
            return await api_add_cart_item(request, env)
        m_cart_item = re.fullmatch(r"/api/cart/items/([A-Za-z0-9_-]+)", path)
        if m_cart_item and method == "DELETE":
            return await api_remove_cart_item(request, env, m_cart_item.group(1))
        if path == "/api/checkout" and method == "POST":
            return await api_create_checkout(request, env)
        if path == "/api/checkout/complete" and method == "POST":
            return await api_complete_checkout(request, env)
        if path == "/api/intents" and method == "GET":
            return await api_list_learning_intents(request, env)
        if path == "/api/intents" and method == "POST":
            return await api_create_learning_intent(request, env)

        if path in ("/api/features", "/api/legacy-features") and method == "GET":
            return await api_features(request, env)

        if path == "/api/donations/checkout" and method == "POST":
            return await api_create_donation_checkout(request, env)

        if path == "/api/admin/table-counts" and method == "GET":
            return await api_admin_table_counts(request, env)

        if path.rstrip("/") == "/api/error" and method == "GET":
            exc = RuntimeError("Sentry test error from /api/error")
            await capture_exception(exc, request, env, "api_error_test")
            return ok(None, "Test error sent to Sentry v2")


        # Email verification and password reset
        if path == "/api/verify-email" and method == "GET":
            return await api_verify_email(request, env)
        if path == "/api/resend-verification" and method == "POST":
            return await api_resend_verification(request, env)
        if path == "/api/forgot-password" and method == "POST":
            return await api_forgot_password(request, env)
        if path == "/api/reset-password" and method == "POST":
            return await api_reset_password(request, env)

        # Notifications
        if path == "/api/notifications" and method == "GET":
            return await api_list_notifications(request, env)
        if path == "/api/notifications/unread-count" and method == "GET":
            return await api_unread_count(request, env)
        m_notif_read = re.fullmatch(r"/api/notifications/([A-Za-z0-9_-]+)/read", path)
        if m_notif_read and method == "POST":
            return await api_mark_notification_read(request, env, m_notif_read.group(1))
        if path == "/api/notifications/read-all" and method == "POST":
            return await api_mark_all_read(request, env)

        # Notification Preferences
        if path == "/api/notification-preferences" and method == "GET":
            return await api_get_notification_preferences(request, env)
        if path == "/api/notification-preferences" and method == "PATCH":
            return await api_patch_notification_preferences(request, env)

        return err("API endpoint not found", 404)

    return await serve_static(path, env, request)


async def on_fetch(request, env):
    try:
        init_sentry(env)
        return await _dispatch(request, env)
    except Exception as e:
        await capture_exception(e, request, env, "on_fetch_unhandled")
        if urlparse(request.url).path.startswith("/api/"):
            return err("Internal server error", 500)
        return await render_500(request, env)


# ---------------------------------------------------------------------------
# Notifications API
# ---------------------------------------------------------------------------

# Notification category → preference column mapping
_NOTIF_PREF_MAP = {
    "enrollment": "enrollment_notify",
    "session":    "session_notify",
    "system":     "system_notify",
}

_EVENT_HANDLERS = {}


def _event_handler(name: str):
    def decorator(fn):
        _EVENT_HANDLERS[name] = fn
        return fn
    return decorator


async def _seed_notification_preferences(env, user_id: str) -> None:
    try:
        await env.DB.prepare(
            "INSERT OR IGNORE INTO notification_preferences (user_id) VALUES (?)"
        ).bind(user_id).run()
    except Exception:
        pass


async def _activity_enrollee_ids(env, activity_id: str,
                                 exclude_user_id: Optional[str] = None) -> list:
    rows = await env.DB.prepare(
        "SELECT user_id FROM enrollments"
        " WHERE activity_id = ? AND status = 'active'"
    ).bind(activity_id).all()
    ids = [r.user_id for r in (rows.results or [])]
    if exclude_user_id:
        ids = [uid for uid in ids if uid != exclude_user_id]
    return ids


async def _get_pref_map(env, user_ids: list, pref_col: str) -> Optional[dict]:
    if not user_ids:
        return None
    allowed = {"enrollment_notify", "session_notify", "system_notify"}
    if pref_col not in allowed:
        pref_col = "system_notify"
    placeholders = ",".join(["?"] * len(user_ids))
    try:
        rows = await env.DB.prepare(
            f"SELECT user_id, {pref_col} AS enabled FROM notification_preferences"
            f" WHERE user_id IN ({placeholders})"
        ).bind(*user_ids).all()
        return {r.user_id: bool(r.enabled) for r in (rows.results or [])}
    except Exception:
        return None


async def emit_event(env, event: str, payload: dict) -> None:
    """Dispatch a domain event to registered notification handlers."""
    handler = _EVENT_HANDLERS.get(event)
    if handler:
        try:
            await handler(env, payload)
        except Exception as exc:
            print(f"[emit_event ERROR] {event}: {type(exc).__name__}: {exc}")


@_event_handler("USER_ENROLLED")
async def _on_user_enrolled(env, p: dict) -> None:
    title = p["activity_title"]
    act_id = p["activity_id"]
    await _create_notification(
        env, p["user_id"], "success", "Enrollment Confirmed",
        f"You have joined '{title}'.",
        related_id=act_id, category="enrollment",
    )
    host_id = p.get("host_id")
    if host_id and host_id != p["user_id"]:
        joiner = p.get("participant_name") or "A new participant"
        await _create_notification(
            env, host_id, "info", "New Participant",
            f"{joiner} joined '{title}'.",
            related_id=act_id, category="enrollment",
        )


@_event_handler("SESSION_CREATED")
async def _on_session_created(env, p: dict) -> None:
    recipient_ids = p.get("recipient_ids") or []
    pref_map = await _get_pref_map(env, recipient_ids, "session_notify")
    for uid in recipient_ids:
        if pref_map is not None and pref_map.get(uid) is False:
            continue
        await _create_notification(
            env, uid, "info", f"New Session: {p['session_title']}",
            f"A new session was added to '{p['activity_title']}'.",
            related_id=p["session_id"], category="session", skip_pref_check=True,
        )


@_event_handler("ACTIVITY_CREATED")
async def _on_activity_created(env, p: dict) -> None:
    await _create_notification(
        env, p["user_id"], "success", "Activity Published",
        f"Your activity '{p['title']}' is now live.",
        related_id=p["activity_id"], category="system",
    )


@_event_handler("ACTIVITY_TAGS_UPDATED")
async def _on_activity_tags_updated(env, p: dict) -> None:
    recipient_ids = p.get("recipient_ids") or []
    pref_map = await _get_pref_map(env, recipient_ids, "system_notify")
    for uid in recipient_ids:
        if pref_map is not None and pref_map.get(uid) is False:
            continue
        await _create_notification(
            env, uid, "info", f"Activity Updated: {p['activity_title']}",
            f"New tags were added to '{p['activity_title']}'.",
            related_id=p["activity_id"], category="system", skip_pref_check=True,
        )


async def _create_notification(env, user_id: str, type_: str, title: str,
                                message: str, related_id: Optional[str] = None,
                                category: str = "system",
                                skip_pref_check: bool = False) -> None:
    """Internal helper called by other handlers to create a notification.

    Respects user notification preferences.  Silently swallows errors so a
    notification failure never breaks the parent operation.
    """
    try:
        if not skip_pref_check:
            try:
                pref = await env.DB.prepare(
                    "SELECT enrollment_notify, session_notify, system_notify"
                    " FROM notification_preferences WHERE user_id = ?"
                ).bind(user_id).first()
                if pref:
                    col = _NOTIF_PREF_MAP.get(category, "system_notify")
                    if not bool(getattr(pref, col, 1)):
                        return
            except Exception:
                pass  # table may not exist yet; default to enabled

        enc = env.ENCRYPTION_KEY
        await env.DB.prepare(
            "INSERT INTO notifications (id, user_id, type, title, message, related_id)"
            " VALUES (?, ?, ?, ?, ?, ?)"
        ).bind(new_id(), user_id, type_,
               await encrypt_aes(title, enc),
               await encrypt_aes(message, enc),
               related_id).run()
    except Exception as exc:
        await capture_exception(exc, _env=env, where="_create_notification")
    return None


def _query_int(params: dict, key: str, default: int, min_val: int, max_val: int) -> int:
    raw = (params.get(key) or [None])[0]
    if raw is None:
        return default
    try:
        return max(min_val, min(int(raw), max_val))
    except (ValueError, TypeError):
        return default


async def api_list_notifications(req, env):
    """GET /api/notifications — list notifications for the authenticated user.

    Query params:
      - unread_only=true   return only unread notifications (default: false)
      - limit=N            max results, default 20, max 50
      - offset=N           skip N rows for pagination (default 0)
    """
    user = verify_token(req.headers.get("Authorization"), env.JWT_SECRET)
    if not user:
        return err("Authentication required", 401)

    parsed = urlparse(req.url)
    params = parse_qs(parsed.query)
    unread_only = (params.get("unread_only") or [""])[0].lower() == "true"
    limit  = _query_int(params, "limit",  20, 1, 50)
    offset = _query_int(params, "offset",  0, 0, 10_000)

    if unread_only:
        rows = await env.DB.prepare(
            "SELECT id, type, title, message, is_read, related_id, created_at"
            " FROM notifications"
            " WHERE user_id = ? AND is_read = 0"
            " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        ).bind(user["id"], limit, offset).all()
    else:
        rows = await env.DB.prepare(
            "SELECT id, type, title, message, is_read, related_id, created_at"
            " FROM notifications"
            " WHERE user_id = ?"
            " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        ).bind(user["id"], limit, offset).all()

    enc = env.ENCRYPTION_KEY
    key_bytes = _derive_aes_key_bytes(enc)
    crypto_key = await _import_aes_key(key_bytes)
    notifications = []
    for r in rows.results or []:
        notifications.append({
            "id":         r.id,
            "type":       r.type,
            "title":      await decrypt_aes_with_key(r.title or "", crypto_key, enc),
            "message":    await decrypt_aes_with_key(r.message or "", crypto_key, enc),
            "is_read":    bool(r.is_read),
            "related_id": r.related_id,
            "created_at": r.created_at,
        })

    unread_count = await env.DB.prepare(
        "SELECT COUNT(*) AS cnt FROM notifications WHERE user_id = ? AND is_read = 0"
    ).bind(user["id"]).first()

    return ok({
        "notifications": notifications,
        "unread_count":  unread_count.cnt if unread_count else 0,
        "limit":         limit,
        "offset":        offset,
    })


async def api_unread_count(req, env):
    """GET /api/notifications/unread-count — return unread badge count only."""
    user = verify_token(req.headers.get("Authorization"), env.JWT_SECRET)
    if not user:
        return err("Authentication required", 401)

    row = await env.DB.prepare(
        "SELECT COUNT(*) AS cnt FROM notifications WHERE user_id = ? AND is_read = 0"
    ).bind(user["id"]).first()

    return ok({"unread_count": row.cnt if row else 0})


async def api_mark_notification_read(req, env, notification_id: str):
    """POST /api/notifications/:id/read — mark a single notification as read."""
    user = verify_token(req.headers.get("Authorization"), env.JWT_SECRET)
    if not user:
        return err("Authentication required", 401)

    notif = await env.DB.prepare(
        "SELECT id FROM notifications WHERE id = ? AND user_id = ?"
    ).bind(notification_id, user["id"]).first()

    if not notif:
        return err("Notification not found", 404)

    await env.DB.prepare(
        "UPDATE notifications SET is_read = 1 WHERE id = ?"
    ).bind(notification_id).run()

    return ok(msg="Notification marked as read")


async def api_mark_all_read(req, env):
    """POST /api/notifications/read-all — mark all notifications as read."""
    user = verify_token(req.headers.get("Authorization"), env.JWT_SECRET)
    if not user:
        return err("Authentication required", 401)

    await env.DB.prepare(
        "UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0"
    ).bind(user["id"]).run()

    return ok(msg="All notifications marked as read")


async def api_get_notification_preferences(req, env):
    """GET /api/notification-preferences — return user notification settings."""
    user = verify_token(req.headers.get("Authorization"), env.JWT_SECRET)
    if not user:
        return err("Authentication required", 401)

    row = await env.DB.prepare(
        "SELECT enrollment_notify, session_notify, system_notify"
        " FROM notification_preferences WHERE user_id = ?"
    ).bind(user["id"]).first()

    if not row:
        return ok({
            "enrollment_notify": True,
            "session_notify":    True,
            "system_notify":     True,
        })

    return ok({
        "enrollment_notify": bool(row.enrollment_notify),
        "session_notify":    bool(row.session_notify),
        "system_notify":     bool(row.system_notify),
    })


async def api_patch_notification_preferences(req, env):
    """PATCH /api/notification-preferences — update user notification settings."""
    user = verify_token(req.headers.get("Authorization"), env.JWT_SECRET)
    if not user:
        return err("Authentication required", 401)

    body, bad_resp = await parse_json_object(req)
    if bad_resp:
        return bad_resp

    allowed = {"enrollment_notify", "session_notify", "system_notify"}
    updates = {}
    for key in allowed:
        if key in body:
            val = body[key]
            if not isinstance(val, bool):
                return err(f"{key} must be a boolean")
            updates[key] = 1 if val else 0

    if not updates:
        return err("Provide at least one of: enrollment_notify, session_notify, system_notify")

    # Read current prefs (or defaults)
    current = await env.DB.prepare(
        "SELECT enrollment_notify, session_notify, system_notify"
        " FROM notification_preferences WHERE user_id = ?"
    ).bind(user["id"]).first()

    en = updates.get("enrollment_notify",
                     current.enrollment_notify if current else 1)
    sn = updates.get("session_notify",
                     current.session_notify if current else 1)
    sy = updates.get("system_notify",
                     current.system_notify if current else 1)

    await env.DB.prepare(
        "INSERT INTO notification_preferences"
        " (user_id, enrollment_notify, session_notify, system_notify)"
        " VALUES (?, ?, ?, ?)"
        " ON CONFLICT(user_id) DO UPDATE SET"
        " enrollment_notify = excluded.enrollment_notify,"
        " session_notify = excluded.session_notify,"
        " system_notify = excluded.system_notify,"
        " updated_at = datetime('now')"
    ).bind(user["id"], en, sn, sy).run()

    return ok({
        "enrollment_notify": bool(en),
        "session_notify":    bool(sn),
        "system_notify":     bool(sy),
    }, "Preferences updated")


async def run_scheduled_reminders(env):
    """Send in-app and email reminders for sessions starting in the next day.

    Cloudflare cron invokes this daily. Notifications use type `session_reminder`
    and `related_id=session_id` so the job is idempotent for a given session/user.
    """
    enc = env.ENCRYPTION_KEY
    try:
        rows = await env.DB.prepare(
            "SELECT s.id AS session_id,s.title AS session_title,s.start_time,a.id AS activity_id,a.slug AS activity_slug,a.title AS activity_title,e.user_id,u.email,u.username"
            " FROM sessions s JOIN activities a ON a.id=s.activity_id"
            " JOIN enrollments e ON e.activity_id=a.id AND e.status='active'"
            " JOIN users u ON u.id=e.user_id"
            " WHERE s.start_time IS NOT NULL AND datetime(s.start_time) BETWEEN datetime('now') AND datetime('now', '+26 hours')"
            " ORDER BY s.start_time ASC LIMIT 500"
        ).all()
    except Exception as exc:
        if _is_no_such_table_error(exc):
            return {"sent": 0}
        raise

    sent = 0
    frontend_url = _frontend_url(env)
    for row in rows.results or []:
        try:
            existing = await env.DB.prepare(
                "SELECT id FROM notifications WHERE user_id=? AND type='session_reminder' AND related_id=? LIMIT 1"
            ).bind(row.user_id, row.session_id).first()
            if existing:
                continue
            await _create_notification(
                env,
                row.user_id,
                "session_reminder",
                "Upcoming Session",
                f"'{row.session_title or 'Session'}' for '{row.activity_title}' starts soon.",
                related_id=row.session_id,
                category="session",
            )
            pref = await env.DB.prepare(
                "SELECT session_notify FROM notification_preferences WHERE user_id=?"
            ).bind(row.user_id).first()
            if (not pref) or bool(getattr(pref, "session_notify", 1)):
                email = await decrypt_aes(row.email or "", enc)
                username = await decrypt_aes(row.username or "", enc)
                if email and email != "[decryption error]" and "@" in email:
                    ref = row.activity_slug or row.activity_id
                    link = frontend_url + "/activity/" + quote(str(ref), safe="")
                    html = _branded_email_html(
                        frontend_url,
                        "Upcoming session reminder",
                        f"Hi <strong>{_html_escape(username or 'there')}</strong>, your session <strong>{_html_escape(row.session_title or 'Session')}</strong> for <strong>{_html_escape(row.activity_title)}</strong> starts soon.",
                        "Open activity",
                        link,
                        "You can manage notification preferences from your Alpha One Labs account.",
                    )
                    await _send_email(email, "Upcoming Alpha One Labs session", html, env)
            sent += 1
        except Exception as exc:
            await capture_exception(exc, _env=env, where="run_scheduled_reminders.row")
    return {"sent": sent}


async def on_scheduled(event, env, ctx):
    try:
        init_sentry(env)
        result = await run_scheduled_reminders(env)
        print(json.dumps({"level": "info", "where": "on_scheduled", "result": result}))
    except Exception as exc:
        await capture_exception(exc, None, env, "on_scheduled")
