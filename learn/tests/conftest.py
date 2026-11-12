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
        if _algo_name(algo) == "Ed25519":
            return _ed25519_import(fmt, key_data)
        return key_data  # return raw bytes as fake CryptoKey

    async def encrypt(self, algo, key, data):
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
        return b""

    async def decrypt(self, algo, key, data):
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
        return b""

    async def sign(self, algo, key, data):
        if _algo_name(algo) == "Ed25519":
            return _ed25519_sign(key, bytes(data))
        raise NotImplementedError("sign is only mocked for Ed25519")

    async def verify(self, algo, key, signature, data):
        if _algo_name(algo) == "Ed25519":
            return _ed25519_verify(key, bytes(signature), bytes(data))
        raise NotImplementedError("verify is only mocked for Ed25519")

    async def generateKey(self, algo, extractable, usages):
        if _algo_name(algo) == "Ed25519":
            return _ed25519_generate()
        raise NotImplementedError("generateKey is only mocked for Ed25519")

    async def exportKey(self, fmt, key):
        return _ed25519_export(fmt, key)


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

# ---------------------------------------------------------------------------
# Ed25519 support for the Web Crypto stub
# ---------------------------------------------------------------------------
#
# The Worker runtime offers Ed25519 through Web Crypto. CPython does not, so the
# stub delegates to the "cryptography" package, which keeps the tests honest:
# signatures produced here are real Ed25519 signatures and verification really
# fails for tampered input. cryptography is a test-only dependency, imported
# lazily so unrelated test files keep working without it.


def _algo_name(algo):
    """Return the algorithm name from a dict or a JS-like object."""
    if isinstance(algo, str):
        return algo
    try:
        return algo.get("name")
    except AttributeError:
        return getattr(algo, "name", None)


class _Ed25519PrivateHandle:
    def __init__(self, key):
        self.key = key


class _Ed25519PublicHandle:
    def __init__(self, key):
        self.key = key


def _require_cryptography():
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
            Ed25519PublicKey,
        )
    except ImportError as exc:  # pragma: no cover - environment guard
        raise RuntimeError(
            "cryptography is required to exercise the Ed25519 Web Crypto stub"
        ) from exc
    return Ed25519PrivateKey, Ed25519PublicKey


def _b64url_decode(text):
    import base64

    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _b64url_encode(data):
    import base64

    return base64.urlsafe_b64encode(bytes(data)).rstrip(b"=").decode("ascii")


def _ed25519_generate():
    from types import SimpleNamespace

    Ed25519PrivateKey, _ = _require_cryptography()
    private = Ed25519PrivateKey.generate()
    return SimpleNamespace(
        privateKey=_Ed25519PrivateHandle(private),
        publicKey=_Ed25519PublicHandle(private.public_key()),
    )


def _ed25519_import(fmt, key_data):
    Ed25519PrivateKey, Ed25519PublicKey = _require_cryptography()
    from cryptography.hazmat.primitives import serialization

    if fmt == "pkcs8":
        key = serialization.load_der_private_key(bytes(key_data), password=None)
        return _Ed25519PrivateHandle(key)
    if fmt == "jwk":
        raw = _b64url_decode(key_data["x"])
        return _Ed25519PublicHandle(Ed25519PublicKey.from_public_bytes(raw))
    if fmt == "raw":
        return _Ed25519PublicHandle(Ed25519PublicKey.from_public_bytes(bytes(key_data)))
    raise ValueError("unsupported key format: %s" % fmt)


def _ed25519_sign(handle, data):
    if not isinstance(handle, _Ed25519PrivateHandle):
        raise TypeError("signing requires an Ed25519 private key")
    return handle.key.sign(data)


def _ed25519_verify(handle, signature, data):
    from cryptography.exceptions import InvalidSignature

    if not isinstance(handle, _Ed25519PublicHandle):
        raise TypeError("verification requires an Ed25519 public key")
    try:
        handle.key.verify(signature, data)
        return True
    except InvalidSignature:
        return False


def _ed25519_export(fmt, handle):
    from cryptography.hazmat.primitives import serialization

    if fmt == "pkcs8":
        if not isinstance(handle, _Ed25519PrivateHandle):
            raise TypeError("pkcs8 export requires a private key")
        return handle.key.private_bytes(
            serialization.Encoding.DER,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    if fmt == "jwk":
        public = handle.key if isinstance(handle, _Ed25519PublicHandle) else handle.key.public_key()
        raw = public.public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        return {"kty": "OKP", "crv": "Ed25519", "x": _b64url_encode(raw)}
    raise ValueError("unsupported export format: %s" % fmt)
