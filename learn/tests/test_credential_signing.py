"""Tests for the standalone Ed25519 JWS helpers.

These exercise real Ed25519 operations: the Web Crypto stub in conftest.py
delegates to the cryptography package, so a signature that verifies here would
verify in the Worker too (and a tampered one fails here for the same reason).
"""

import base64
import json
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import credential_signing as cs  # noqa: E402

PAYLOAD = {
    "id": "https://learn.alphaonelabs.com/credentials/1",
    "type": ["VerifiableCredential", "OpenBadgeCredential"],
    "issuer": "did:web:learn.alphaonelabs.com",
}


@pytest.fixture
async def key_pair():
    return await cs.generate_key_pair("test-key-1")


def _segments(token):
    parts = token.split(".")
    assert len(parts) == 3
    return parts


def _decode(segment):
    return json.loads(cs.b64url_decode(segment).decode("utf-8"))


# ---------------------------------------------------------------------------
# Signing
# ---------------------------------------------------------------------------


async def test_sign_and_verify_roundtrip(key_pair):
    token = await cs.sign_jws(PAYLOAD, key_pair["private_key_pkcs8"], key_pair["kid"])
    verified = await cs.verify_jws_json(token, key_pair["public_jwk"])

    assert verified == PAYLOAD
    header_segment, payload_segment, signature_segment = _segments(token)
    header = _decode(header_segment)
    assert header == {"alg": "EdDSA", "typ": "JWT", "kid": "test-key-1"}
    assert _decode(payload_segment) == PAYLOAD
    assert len(cs.b64url_decode(signature_segment)) == 64


async def test_sign_accepts_raw_bytes_payload(key_pair):
    token = await cs.sign_jws(b"not json", key_pair["private_key_pkcs8"], "test-key-1")
    payload = await cs.verify_jws(token, key_pair["public_jwk"])
    assert payload == b"not json"


async def test_sign_rejects_algorithm_override(key_pair):
    with pytest.raises(ValueError):
        await cs.sign_jws(
            PAYLOAD,
            key_pair["private_key_pkcs8"],
            "test-key-1",
            protected_headers={"alg": "none"},
        )


async def test_sign_requires_kid(key_pair):
    with pytest.raises(ValueError):
        await cs.sign_jws(PAYLOAD, key_pair["private_key_pkcs8"], "  ")


# ---------------------------------------------------------------------------
# Verification failures
# ---------------------------------------------------------------------------


async def test_verify_rejects_tampered_payload(key_pair):
    token = await cs.sign_jws(PAYLOAD, key_pair["private_key_pkcs8"], "test-key-1")
    header_segment, _, signature_segment = _segments(token)
    forged_payload = cs.b64url_encode(json.dumps({"id": "https://evil.example/1"}).encode())
    forged = f"{header_segment}.{forged_payload}.{signature_segment}"

    with pytest.raises(cs.JwsVerificationError):
        await cs.verify_jws(forged, key_pair["public_jwk"])


async def test_verify_rejects_wrong_public_key(key_pair):
    token = await cs.sign_jws(PAYLOAD, key_pair["private_key_pkcs8"], "test-key-1")
    other = await cs.generate_key_pair("test-key-2")

    with pytest.raises(cs.JwsVerificationError):
        await cs.verify_jws(token, other["public_jwk"])


async def test_verify_rejects_alg_none(key_pair):
    header = cs.b64url_encode(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    body = cs.b64url_encode(json.dumps(PAYLOAD).encode())
    unsigned = f"{header}.{body}."

    with pytest.raises(cs.JwsUnsupportedAlgorithmError):
        await cs.verify_jws(unsigned, key_pair["public_jwk"])


async def test_verify_rejects_other_algorithms(key_pair):
    header = cs.b64url_encode(json.dumps({"alg": "HS256"}).encode())
    body = cs.b64url_encode(json.dumps(PAYLOAD).encode())
    token = f"{header}.{body}.{cs.b64url_encode(b'x' * 64)}"

    with pytest.raises(cs.JwsUnsupportedAlgorithmError):
        await cs.verify_jws(token, key_pair["public_jwk"])


async def test_verify_rejects_unexpected_kid(key_pair):
    token = await cs.sign_jws(PAYLOAD, key_pair["private_key_pkcs8"], "test-key-1")

    with pytest.raises(cs.JwsVerificationError):
        await cs.verify_jws(token, key_pair["public_jwk"], expected_kid="other-key")


@pytest.mark.parametrize(
    "token",
    [
        "",
        "onlyonesegment",
        "two.segments",
        "a.b.c.d",
        "!!!.???.@@@",
        "eyJhbGciOiJFZERTQSJ9..",  # empty signature
        "eyJhbGciOiJFZERTQSJ9.eyJhIjoxfQ.",  # empty signature, alg EdDSA
    ],
)
async def test_verify_rejects_malformed_tokens(token, key_pair):
    with pytest.raises(cs.JwsMalformedError):
        await cs.verify_jws(token, key_pair["public_jwk"])


async def test_verify_rejects_header_that_is_not_json(key_pair):
    token = f"{cs.b64url_encode(b'not json')}.{cs.b64url_encode(b'{}')}.{cs.b64url_encode(b'x' * 64)}"
    with pytest.raises(cs.JwsMalformedError):
        await cs.verify_jws(token, key_pair["public_jwk"])


async def test_verify_rejects_short_signature(key_pair):
    header = cs.b64url_encode(json.dumps({"alg": "EdDSA", "kid": "test-key-1"}).encode())
    token = f"{header}.{cs.b64url_encode(b'{}')}.{cs.b64url_encode(b'short')}"
    with pytest.raises(cs.JwsMalformedError):
        await cs.verify_jws(token, key_pair["public_jwk"])


async def test_verify_rejects_invalid_public_jwk(key_pair):
    token = await cs.sign_jws(PAYLOAD, key_pair["private_key_pkcs8"], "test-key-1")

    with pytest.raises(cs.JwsVerificationError):
        await cs.verify_jws(token, {"kty": "RSA", "n": "..."})
    with pytest.raises(cs.JwsVerificationError):
        await cs.verify_jws(token, {"kty": "OKP", "crv": "Ed25519"})
    with pytest.raises(cs.JwsVerificationError):
        await cs.verify_jws(token, {"kty": "OKP", "crv": "Ed25519", "x": "AAAA"})


# ---------------------------------------------------------------------------
# Key generation utility
# ---------------------------------------------------------------------------


async def test_generate_key_pair_formats(key_pair):
    assert key_pair["alg"] == "EdDSA"
    assert key_pair["kid"] == "test-key-1"

    der = base64.b64decode(key_pair["private_key_pkcs8"], validate=True)
    assert der[:2] == b"0\x82"[:2] or der[0:1] == b"0"  # DER SEQUENCE
    assert len(der) > 40

    jwk = key_pair["public_jwk"]
    assert jwk["kty"] == "OKP"
    assert jwk["crv"] == "Ed25519"
    assert len(cs.b64url_decode(jwk["x"])) == 32

    env = key_pair["env"]
    assert env["ED25519_PRIVATE_KEY_PKCS8"] == key_pair["private_key_pkcs8"]
    assert json.loads(env["ED25519_PUBLIC_JWK"]) == jwk
    assert env["ED25519_SIGNING_KID"] == "test-key-1"


async def test_generate_requires_kid():
    with pytest.raises(ValueError):
        await cs.generate_key_pair("")


# ---------------------------------------------------------------------------
# Base64URL helpers
# ---------------------------------------------------------------------------


def test_b64url_encode_is_unpadded_and_url_safe():
    encoded = cs.b64url_encode(b"\xfb\xff\xfe")
    assert "=" not in encoded
    assert "+" not in encoded and "/" not in encoded
    assert cs.b64url_decode(encoded) == b"\xfb\xff\xfe"


@pytest.mark.parametrize("bad", ["a", "abcde", "ab+c", "ab/c", "ab c", "ab="])
def test_b64url_decode_rejects_invalid_input(bad):
    with pytest.raises(cs.JwsMalformedError):
        cs.b64url_decode(bad)


def test_b64url_rejects_non_bytes():
    with pytest.raises(TypeError):
        cs.b64url_encode("text")



# ---------------------------------------------------------------------------
# Protected-header overrides and unsupported critical headers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("header_name", ["kid", "typ"])
async def test_sign_rejects_protected_header_overrides(key_pair, header_name):
    with pytest.raises(ValueError):
        await cs.sign_jws(
            PAYLOAD,
            key_pair["private_key_pkcs8"],
            "test-key-1",
            protected_headers={header_name: "spoofed"},
        )


async def test_sign_rejects_critical_header(key_pair):
    with pytest.raises(ValueError):
        await cs.sign_jws(
            PAYLOAD,
            key_pair["private_key_pkcs8"],
            "test-key-1",
            protected_headers={"crit": ["b64"], "b64": False},
        )


async def test_sign_rejects_payload_that_would_exceed_verifier_limit(key_pair):
    oversized = b"x" * 49152
    with pytest.raises(ValueError):
        await cs.sign_jws(oversized, key_pair["private_key_pkcs8"], "test-key-1")


async def _sign_raw(signing_input, private_key_pkcs8):
    key = await cs._import_private_key(private_key_pkcs8)
    signature = await cs.js.crypto.subtle.sign(
        cs._algo(cs.ED25519_CURVE), key, cs._to_buffer(signing_input.encode("ascii"))
    )
    return signing_input + "." + cs.b64url_encode(cs._buffer_bytes(signature))


async def test_verify_rejects_unsupported_critical_header(key_pair):
    header = {
        "alg": "EdDSA",
        "typ": "JWT",
        "kid": "test-key-1",
        "crit": ["b64"],
        "b64": False,
    }
    signing_input = (
        cs.b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        + "."
        + cs.b64url_encode(b"{}")
    )
    token = await _sign_raw(signing_input, key_pair["private_key_pkcs8"])
    with pytest.raises(cs.JwsUnsupportedCriticalHeaderError):
        await cs.verify_jws(token, key_pair["public_jwk"])


async def test_invalid_jwk_coordinate_is_a_key_error(key_pair):
    token = await cs.sign_jws(PAYLOAD, key_pair["private_key_pkcs8"], "test-key-1")
    with pytest.raises(cs.JwsVerificationError):
        await cs.verify_jws(token, dict(key_pair["public_jwk"], x="%%"))
