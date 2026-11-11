import base64
import json
import re

import js
from pyodide.ffi import to_js

_ED25519_ALGO = {"name": "Ed25519"}
_B64URL_RE = re.compile(r"[A-Za-z0-9_-]*")


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(text: str) -> bytes:
    """Strict, canonical base64url (no padding). Raises ValueError on anything else."""
    if not isinstance(text, str) or not _B64URL_RE.fullmatch(text):
        raise ValueError("invalid base64url characters")
    try:
        raw = base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    except Exception as exc:
        raise ValueError("invalid base64url") from exc
    if b64url_encode(raw) != text:      # rejects non-zero trailing bits (malleable encodings)
        raise ValueError("non-canonical base64url")
    return raw


def _json_b64(obj) -> str:
    return b64url_encode(json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def _algo():
    return to_js(_ED25519_ALGO, dict_converter=js.Object.fromEntries)


async def sign_jws(payload: dict, private_pkcs8: bytes, kid: str) -> str:
    """Return a compact JWS (header.payload.signature) signed with Ed25519."""
    header = {"alg": "EdDSA", "typ": "JWT", "kid": kid}
    signing_input = f"{_json_b64(header)}.{_json_b64(payload)}"
    key = await js.crypto.subtle.importKey(
        "pkcs8", to_js(private_pkcs8, create_pyproxies=False), _algo(), False, to_js(["sign"])
    )
    sig = await js.crypto.subtle.sign(
        _algo(), key, to_js(signing_input.encode("ascii"), create_pyproxies=False)
    )
    return f"{signing_input}.{b64url_encode(bytes(js.Uint8Array.new(sig)))}"


async def verify_jws(token: str, public_raw: bytes):
    """Return the payload dict if the signature is valid, otherwise None."""
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
        header = json.loads(b64url_decode(header_b64))
        # Only EdDSA; reject "none", anything else, and any critical extension
        # (we implement none, so RFC 7515 says to reject).
        if not isinstance(header, dict) or header.get("alg") != "EdDSA" or "crit" in header:
            return None
        key = await js.crypto.subtle.importKey(
            "raw", to_js(public_raw, create_pyproxies=False), _algo(), False, to_js(["verify"])
        )
        valid = await js.crypto.subtle.verify(
            _algo(), key,
            to_js(b64url_decode(sig_b64), create_pyproxies=False),
            to_js(f"{header_b64}.{payload_b64}".encode("ascii"), create_pyproxies=False),
        )
        if not valid:
            return None
        payload = json.loads(b64url_decode(payload_b64))
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None
