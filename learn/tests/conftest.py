"""
Conftest – install module-level stubs before any test file imports worker.py.

The Cloudflare Worker runtime provides three packages that do not exist in a
standard CPython environment:

  * ``workers``      – exposes ``Response``
  * ``js``           – exposes ``crypto.subtle`` (Web Crypto API) and ``Uint8Array``
  * ``pyodide.ffi``  – exposes ``to_js`` (Python→JS conversion)

We install lightweight stubs into ``sys.modules`` here (conftest is loaded
first by pytest) so that ``import worker`` succeeds in tests.
"""

import sys


# ---------------------------------------------------------------------------
# workers stub
# ---------------------------------------------------------------------------

class _Response:
    """Minimal stub for workers.Response."""

    def __init__(self, body="", *, status=200, headers=None, web_socket=None, **_kwargs):
        self.body = body
        self.status = status
        self.headers = dict(headers or {})
        self.web_socket = web_socket

    def json(self):
        import json
        return json.loads(self.body)

    def __repr__(self):
        return f"<Response status={self.status}>"


class _DurableObject:
    """Stub for workers.DurableObject base class."""

    def __init__(self, ctx=None, env=None):
        self.ctx = ctx
        self.env = env


class _WorkersModule:
    Response = _Response
    DurableObject = _DurableObject


sys.modules["workers"] = _WorkersModule()


# ---------------------------------------------------------------------------
# pyodide / pyodide.ffi stub
# ---------------------------------------------------------------------------

class _ToJs:
    """Identity ``to_js`` – returns the Python object unchanged."""

    def __call__(self, obj, **kwargs):
        if isinstance(obj, bytearray):
            return bytes(obj)
        return obj


class _PyodideFFIModule:
    to_js = _ToJs()


class _PyodideModule:
    ffi = _PyodideFFIModule()


sys.modules["pyodide"] = _PyodideModule()
sys.modules["pyodide.ffi"] = _PyodideFFIModule()


# ---------------------------------------------------------------------------
# js stub (Web Crypto API)
# ---------------------------------------------------------------------------

class _Uint8Array:
    """Stub for ``js.Uint8Array``."""

    @staticmethod
    def new(buf):
        if isinstance(buf, (bytes, bytearray)):
            return buf
        return bytes(buf)


class _CryptoSubtle:
    """
    Stub for ``js.crypto.subtle``.

    ``encrypt`` and ``decrypt`` are *identity* operations so that
    ``encrypt_aes`` / ``decrypt_aes`` round-trip correctly in tests.
    """

    async def importKey(self, fmt, key_data, algo, extractable, usages):
        return key_data  # return raw bytes as fake CryptoKey

    async def encrypt(self, algo, key, data):
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
        return b""

    async def decrypt(self, algo, key, data):
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
        return b""


class _Crypto:
    subtle = _CryptoSubtle()

    @staticmethod
    def getRandomValues(buf):
        # Return a fixed 12-byte IV so tests are deterministic.
        return b"\x00" * 12


class _WebSocketPair:
    """Stub for js.WebSocketPair."""

    @staticmethod
    def new() -> "MagicMock":
        from unittest.mock import MagicMock
        client, server = MagicMock(name="ws_client"), MagicMock(name="ws_server")
        pair = MagicMock(name="ws_pair")
        pair.object_values.return_value = (client, server)
        # Expose for tests that want to assert on server.send(...) etc.
        pair.client = client
        pair.server = server
        return pair


class _WebSocketRequestResponsePair:
    """Stub for js.WebSocketRequestResponsePair."""

    @staticmethod
    def new(request, response):
        from unittest.mock import MagicMock
        return MagicMock()


class _JsModule:
    crypto = _Crypto()
    Uint8Array = _Uint8Array()
    WebSocketPair = _WebSocketPair()
    WebSocketRequestResponsePair = _WebSocketRequestResponsePair()

    class Object:
        @staticmethod
        def fromEntries(entries):
            return dict(entries)


sys.modules["js"] = _JsModule()
