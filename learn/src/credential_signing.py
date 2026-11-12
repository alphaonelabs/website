"""Ed25519 JWS signing and verification helpers for verifiable credentials.

This is a standalone module: it does not import worker.py and it does not touch
routes, the database, or any existing credential workflow. It exists so that
Open Badges 3.0 / verifiable-credential signing can be validated in isolation
before it is wired into the application.

Wire format (compact JWS, one line):

    <protected header>.<payload>.<signature>

* protected header - JSON, Base64URL-encoded, carries alg / typ / kid
* payload          - JSON (or raw bytes), Base64URL-encoded
* signature        - 64-byte Ed25519 signature over b"<header>.<payload>"

Key formats
-----------
* Signing key  - Ed25519 private key in PKCS#8 DER form.
* Verification - Ed25519 public key as a JWK:
  {"kty": "OKP", "crv": "Ed25519", "x": "..."}.

Security properties
-------------------
* alg is pinned to EdDSA. "none" and every HMAC/RSA/EC algorithm are rejected
  before any cryptography happens, so a caller cannot be tricked into
  algorithm confusion.
* verify_jws only returns a payload when the signature actually verified;
  every other outcome raises.
* Keys are never logged or persisted here. The key-generation helper only
  returns values for the caller to place in .dev.vars / Worker secrets.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
import sys
from typing import Any, Dict, Mapping, Optional, Tuple, Union

try:  # The Worker runtime (Pyodide) provides these; plain CPython does not.
    import js
    from pyodide.ffi import to_js
except ImportError:  # pragma: no cover - only on a workstation without the runtime
    js = None  # type: ignore[assignment]
    to_js = None  # type: ignore[assignment]

EdDSA_ALG = "EdDSA"
ED25519_CURVE = "Ed25519"

#: Base64URL alphabet; an empty segment is structurally allowed but useless.
_SEGMENT_RE = re.compile(r"^[A-Za-z0-9_-]*$")
_MAX_TOKEN_LENGTH = 64 * 1024

__all__ = [
    "EdDSA_ALG",
    "ED25519_CURVE",
    "JwsError",
    "JwsMalformedError",
    "JwsUnsupportedAlgorithmError",
    "JwsUnsupportedCriticalHeaderError",
    "JwsVerificationError",
    "b64url_encode",
    "b64url_decode",
    "sign_jws",
    "verify_jws",
    "verify_jws_json",
    "generate_key_pair",
]


class JwsError(ValueError):
    """Base class for every JWS failure mode."""


class JwsMalformedError(JwsError):
    """The token is not a structurally valid compact JWS."""


class JwsUnsupportedAlgorithmError(JwsError):
    """The protected header asks for an algorithm we do not support."""


class JwsVerificationError(JwsError):
    """The signature did not verify against the supplied public key."""


class JwsUnsupportedCriticalHeaderError(JwsError):
    """A protected header lists a RFC 7515 'crit' extension we do not implement."""


# ---------------------------------------------------------------------------
# Base64URL (RFC 7515 section 2: unpadded URL-safe base64)
# ---------------------------------------------------------------------------


def b64url_encode(data: bytes) -> str:
    """Encode bytes as unpadded Base64URL."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("b64url_encode expects bytes")
    return base64.urlsafe_b64encode(bytes(data)).rstrip(b"=").decode("ascii")


def b64url_decode(text: str) -> bytes:
    """Decode unpadded Base64URL, rejecting anything outside the alphabet."""
    if not isinstance(text, str):
        raise JwsMalformedError("Base64URL segment must be a string")
    if not _SEGMENT_RE.match(text):
        raise JwsMalformedError("Base64URL segment contains invalid characters")
    if len(text) % 4 == 1:
        raise JwsMalformedError("Base64URL segment has an impossible length")
    padded = text + "=" * (-len(text) % 4)
    try:
        return base64.urlsafe_b64decode(padded)
    except (binascii.Error, ValueError) as exc:
        raise JwsMalformedError("Base64URL segment could not be decoded") from exc


# ---------------------------------------------------------------------------
# Small runtime adapters (private, so the public API stays plain Python)
# ---------------------------------------------------------------------------


def _require_runtime() -> None:
    if js is None or to_js is None:
        raise RuntimeError(
            "Web Crypto is unavailable: this module must run inside the Cloudflare "
            "Python Worker runtime (or a test environment that provides a js stub)"
        )


def _algo(name: str) -> Any:
    return to_js({"name": name}, dict_converter=js.Object.fromEntries)


def _to_buffer(data: bytes) -> Any:
    return to_js(bytes(data), create_pyproxies=False)


def _buffer_bytes(buffer: Any) -> bytes:
    return bytes(js.Uint8Array.new(buffer))


def _to_plain(value: Any) -> Any:
    """Convert a JS object returned by Web Crypto into plain Python."""
    if isinstance(value, dict):
        return dict(value)
    converter = getattr(value, "to_py", None)
    if callable(converter):
        return converter()
    return dict(value)


def _json_bytes(value: Union[Mapping[str, Any], list]) -> bytes:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _payload_bytes(payload: Union[bytes, bytearray, Mapping[str, Any], list]) -> bytes:
    if isinstance(payload, (bytes, bytearray, memoryview)):
        return bytes(payload)
    if isinstance(payload, (dict, list)):
        return _json_bytes(payload)
    raise TypeError("payload must be bytes, dict, or list")


def _header_bytes(header: Mapping[str, Any]) -> bytes:
    return _json_bytes(header)


# ---------------------------------------------------------------------------
# Key import
# ---------------------------------------------------------------------------


async def _import_private_key(private_key_pkcs8: Union[bytes, bytearray, str]) -> Any:
    """Import a PKCS#8 DER Ed25519 private key for signing."""
    _require_runtime()
    if isinstance(private_key_pkcs8, str):
        material = base64.b64decode(private_key_pkcs8, validate=True)
    else:
        material = bytes(private_key_pkcs8)
    if not material:
        raise ValueError("private key material is empty")
    return await js.crypto.subtle.importKey(
        "pkcs8", _to_buffer(material), _algo(ED25519_CURVE), False, to_js(["sign"])
    )


def _normalise_public_jwk(public_key_jwk: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(public_key_jwk, Mapping):
        raise JwsVerificationError("public key must be a JWK mapping")
    if public_key_jwk.get("kty") != "OKP" or public_key_jwk.get("crv") != ED25519_CURVE:
        raise JwsVerificationError("public JWK must describe an Ed25519 (OKP) key")
    x = public_key_jwk.get("x")
    if not isinstance(x, str) or not x:
        raise JwsVerificationError("public JWK is missing the x coordinate")
    try:
        coordinate = b64url_decode(x)
    except JwsError as exc:
        # The offending value came from the caller's key, not from the token.
        raise JwsVerificationError(
            "public JWK x coordinate is not valid Base64URL"
        ) from exc
    if len(coordinate) != 32:
        raise JwsVerificationError("public JWK x coordinate is not 32 bytes")
    return {"kty": "OKP", "crv": ED25519_CURVE, "x": x}


async def _import_public_key(public_key_jwk: Mapping[str, Any]) -> Any:
    _require_runtime()
    jwk = _normalise_public_jwk(public_key_jwk)
    jwk_js = to_js(jwk, dict_converter=js.Object.fromEntries)
    return await js.crypto.subtle.importKey(
        "jwk", jwk_js, _algo(ED25519_CURVE), False, to_js(["verify"])
    )


# ---------------------------------------------------------------------------
# Signing
# ---------------------------------------------------------------------------


async def sign_jws(
    payload: Union[bytes, bytearray, Mapping[str, Any], list],
    private_key_pkcs8: Union[bytes, bytearray, str],
    kid: str,
    *,
    typ: str = "JWT",
    protected_headers: Optional[Mapping[str, Any]] = None,
) -> str:
    """Return a compact Ed25519 JWS for payload.

    private_key_pkcs8 accepts raw PKCS#8 DER bytes or a Base64 string.
    protected_headers may add extra claims but cannot change alg.
    """
    if not isinstance(kid, str) or not kid.strip():
        raise ValueError("kid must be a non-empty string")

    header: Dict[str, Any] = {"alg": EdDSA_ALG, "typ": typ, "kid": kid}
    if protected_headers:
        for name, value in protected_headers.items():
            if name == "alg":
                raise ValueError("alg is pinned to EdDSA and cannot be overridden")
            if name in ("kid", "typ"):
                raise ValueError(
                    f"{name} must be passed as an explicit argument, not via protected_headers"
                )
            if name == "crit":
                raise ValueError(
                    "crit is not supported: this module implements no critical extensions"
                )
            header[name] = value

    body = _payload_bytes(payload)
    signing_input = f"{b64url_encode(_header_bytes(header))}.{b64url_encode(body)}"
    # verify_jws rejects anything longer than _MAX_TOKEN_LENGTH, so refuse to
    # emit a token that this module would not accept back.
    signature_segment_length = len(b64url_encode(b"\x00" * 64))
    if len(signing_input) + 1 + signature_segment_length > _MAX_TOKEN_LENGTH:
        raise ValueError(
            "payload is too large: the resulting token would exceed the verifier limit"
        )

    key = await _import_private_key(private_key_pkcs8)
    signature = await js.crypto.subtle.sign(
        _algo(ED25519_CURVE), key, _to_buffer(signing_input.encode("ascii"))
    )
    return f"{signing_input}.{b64url_encode(_buffer_bytes(signature))}"


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def _split_token(token: str) -> Tuple[str, str, str]:
    if not isinstance(token, str) or not token:
        raise JwsMalformedError("token must be a non-empty string")
    if len(token) > _MAX_TOKEN_LENGTH:
        raise JwsMalformedError("token is unreasonably large")
    if token.count(".") != 2:
        raise JwsMalformedError("compact JWS must have exactly three segments")
    header_segment, payload_segment, signature_segment = token.split(".")
    for segment in (header_segment, payload_segment, signature_segment):
        if not _SEGMENT_RE.match(segment):
            raise JwsMalformedError("token contains characters outside Base64URL")
    return header_segment, payload_segment, signature_segment


def _decode_header(header_segment: str) -> Dict[str, Any]:
    try:
        header = json.loads(b64url_decode(header_segment).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JwsMalformedError("protected header is not valid JSON") from exc
    if not isinstance(header, dict):
        raise JwsMalformedError("protected header must be a JSON object")
    return header


async def verify_jws(
    token: str,
    public_key_jwk: Mapping[str, Any],
    *,
    expected_kid: Optional[str] = None,
    expected_typ: Optional[str] = None,
) -> bytes:
    """Verify token and return the raw payload bytes.

    Raises JwsUnsupportedAlgorithmError for anything other than EdDSA
    (including "none"), JwsMalformedError for structurally broken tokens, and
    JwsVerificationError when the signature does not verify. A payload is never
    returned on failure.
    """
    header_segment, payload_segment, signature_segment = _split_token(token)
    header = _decode_header(header_segment)

    algorithm = header.get("alg")
    if algorithm != EdDSA_ALG:
        raise JwsUnsupportedAlgorithmError(
            f"unsupported algorithm {algorithm!r}; only {EdDSA_ALG!r} is accepted"
        )
    crit = header.get("crit")
    if crit is not None:
        # RFC 7515 section 4.1.11: a verifier must reject any critical header it
        # does not understand, and this module implements none.
        raise JwsUnsupportedCriticalHeaderError(
            "token declares critical protected headers this verifier cannot honour"
        )
    if expected_kid is not None and header.get("kid") != expected_kid:
        raise JwsVerificationError("token was signed with an unexpected key id")
    if expected_typ is not None and header.get("typ") != expected_typ:
        raise JwsVerificationError("token has an unexpected typ")

    signature = b64url_decode(signature_segment)
    if len(signature) != 64:
        raise JwsMalformedError("Ed25519 signatures are 64 bytes")

    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    key = await _import_public_key(public_key_jwk)
    valid = await js.crypto.subtle.verify(
        _algo(ED25519_CURVE), key, _to_buffer(signature), _to_buffer(signing_input)
    )
    if not valid:
        raise JwsVerificationError("signature verification failed")

    return b64url_decode(payload_segment)


async def verify_jws_json(
    token: str,
    public_key_jwk: Mapping[str, Any],
    *,
    expected_kid: Optional[str] = None,
    expected_typ: Optional[str] = None,
) -> Any:
    """Like verify_jws, but decode the payload as JSON."""
    payload = await verify_jws(
        token, public_key_jwk, expected_kid=expected_kid, expected_typ=expected_typ
    )
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JwsMalformedError("payload is not valid JSON") from exc


# ---------------------------------------------------------------------------
# Key generation (development utility)
# ---------------------------------------------------------------------------


async def generate_key_pair(kid: str = "dev-local") -> Dict[str, Any]:
    """Generate an Ed25519 key pair and return export-ready values.

    The private key comes back as Base64-encoded PKCS#8 DER (put it in a Worker
    secret, never in git); the public key comes back as a JWK.
    """
    _require_runtime()
    if not isinstance(kid, str) or not kid.strip():
        raise ValueError("kid must be a non-empty string")

    pair = await js.crypto.subtle.generateKey(
        _algo(ED25519_CURVE), True, to_js(["sign", "verify"])
    )
    pkcs8 = await js.crypto.subtle.exportKey("pkcs8", pair.privateKey)
    public_jwk = _to_plain(await js.crypto.subtle.exportKey("jwk", pair.publicKey))

    private_b64 = base64.b64encode(_buffer_bytes(pkcs8)).decode("ascii")
    return {
        "kid": kid,
        "alg": EdDSA_ALG,
        "private_key_pkcs8": private_b64,
        "public_jwk": public_jwk,
        "env": {
            "ED25519_PRIVATE_KEY_PKCS8": private_b64,
            "ED25519_PUBLIC_JWK": json.dumps(public_jwk, separators=(",", ":")),
            "ED25519_SIGNING_KID": kid,
        },
    }


def _generate_key_pair_locally(kid: str) -> Dict[str, Any]:  # pragma: no cover - CLI only
    """Fallback for workstations without the Worker runtime (needs cryptography)."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    pkcs8 = key.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    raw_public = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    public_jwk = {"kty": "OKP", "crv": ED25519_CURVE, "x": b64url_encode(raw_public)}
    private_b64 = base64.b64encode(pkcs8).decode("ascii")
    return {
        "kid": kid,
        "alg": EdDSA_ALG,
        "private_key_pkcs8": private_b64,
        "public_jwk": public_jwk,
        "env": {
            "ED25519_PRIVATE_KEY_PKCS8": private_b64,
            "ED25519_PUBLIC_JWK": json.dumps(public_jwk, separators=(",", ":")),
            "ED25519_SIGNING_KID": kid,
        },
    }


def _main(argv: list) -> int:  # pragma: no cover - CLI only
    if len(argv) < 1 or argv[0] not in ("generate", "gen-key", "gen"):
        sys.stderr.write("usage: python credential_signing.py generate [kid]\n")
        return 2
    kid = argv[1] if len(argv) > 1 else "dev-local"
    if not isinstance(kid, str) or not kid.strip():
        sys.stderr.write("kid must be a non-empty string\n")
        return 2
    try:
        import asyncio

        result = asyncio.run(generate_key_pair(kid))
    except RuntimeError:
        # Only an unavailable Web Crypto runtime justifies the local fallback;
        # validation failures must surface instead of producing a useless key.
        result = _generate_key_pair_locally(kid)
    sys.stdout.write(json.dumps(result, indent=2) + "\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main(sys.argv[1:]))
