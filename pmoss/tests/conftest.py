"""
Conftest – stub Cloudflare Workers JavaScript runtime modules (`js`) for testing.
"""

import hashlib
import hmac
import json
import sys
import types
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlparse


class _Headers:
    """Mock for Web API Headers."""

    @classmethod
    def new(cls, initial=None):
        return cls(initial)

    def __init__(self, initial=None):
        self._store = {}
        if initial:
            if isinstance(initial, dict):
                for k, v in initial.items():
                    self.set(k, v)
            elif isinstance(initial, (list, tuple)):
                for k, v in initial:
                    self.set(k, v)

    def set(self, key, value):
        self._store[str(key).lower()] = (str(key), str(value))

    def get(self, key, default=None):
        entry = self._store.get(str(key).lower())
        return entry[1] if entry else default

    def has(self, key):
        return str(key).lower() in self._store

    def items(self):
        return [(entry[0], entry[1]) for entry in self._store.values()]

    def __iter__(self):
        return iter(self._store)

    def __repr__(self):
        return f"<Headers {dict(self.items())}>"


class _Response:
    """Mock for Web API Response."""

    @classmethod
    def new(cls, body=None, status=200, headers=None):
        return cls(body, status=status, headers=headers)

    def __init__(self, body=None, status=200, headers=None):
        self.body = body
        self.status = status
        if headers is None:
            self.headers = _Headers.new()
        elif isinstance(headers, _Headers):
            self.headers = headers
        else:
            self.headers = _Headers.new(headers)

    @property
    def ok(self):
        return 200 <= self.status < 300

    async def text(self):
        if self.body is None:
            return ""
        if isinstance(self.body, bytes):
            return self.body.decode("utf-8")
        return str(self.body)

    def json(self):
        if self.body is None:
            return {}
        return json.loads(self.body)

    def __repr__(self):
        return f"<Response status={self.status}>"


class _URLSearchParams:
    def __init__(self, query_string):
        self._parsed = parse_qs(query_string, keep_blank_values=True)

    def get(self, key, default=None):
        values = self._parsed.get(key)
        return values[0] if values else default

    def getAll(self, key):
        return self._parsed.get(key, [])


class _URL:
    """Mock for Web API URL."""

    @classmethod
    def new(cls, url_str):
        return cls(url_str)

    def __init__(self, url_str):
        self.href = str(url_str)
        parsed = urlparse(self.href)
        self.pathname = parsed.path or "/"
        self.search = f"?{parsed.query}" if parsed.query else ""
        self.searchParams = _URLSearchParams(parsed.query)


class _TextEncoder:
    @classmethod
    def new(cls):
        return cls()

    def encode(self, text):
        if isinstance(text, bytes):
            return text
        return str(text).encode("utf-8")


class _CryptoSubtle:
    async def importKey(self, fmt, key_data, algo, extractable, usages):
        if isinstance(key_data, str):
            return key_data.encode("utf-8")
        return bytes(key_data)

    async def sign(self, algo, key, data):
        key_bytes = key if isinstance(key, bytes) else str(key).encode("utf-8")
        data_bytes = data if isinstance(data, bytes) else str(data).encode("utf-8")
        if isinstance(algo, str):
            algo_name = algo.upper()
        else:
            algo_name = algo.get("name", "HMAC").upper()
        if algo_name == "HMAC":
            return hmac.new(key_bytes, data_bytes, hashlib.sha256).digest()
        return b""


class _Uint8Array:
    @classmethod
    def new(cls, buf):
        if isinstance(buf, (bytes, bytearray)):
            return bytes(buf)
        return bytes(buf)


class _Crypto:
    TextEncoder = _TextEncoder
    subtle = _CryptoSubtle()
    Uint8Array = _Uint8Array


def _install_js_stubs():
    if "js" in sys.modules:
        return sys.modules["js"]

    js_mod = types.ModuleType("js")
    js_mod.Response = _Response
    js_mod.Headers = _Headers
    js_mod.URL = _URL
    js_mod.crypto = _Crypto()
    js_mod.fetch = AsyncMock(name="fetch")

    sys.modules["js"] = js_mod
    return js_mod


_install_js_stubs()
