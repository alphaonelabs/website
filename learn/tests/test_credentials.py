import sys
import json
from pathlib import Path

import pytest

pytest.importorskip("cryptography")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import credentials  # noqa: E402
from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402


def _keypair():
    key = Ed25519PrivateKey.generate()
    pkcs8 = key.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8,
                              serialization.NoEncryption())
    pub = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return pkcs8, pub


def test_b64url_roundtrip():
    for data in (b"", b"a", b"ab", b"\xff\xfe\x00\x01"):
        assert credentials.b64url_decode(credentials.b64url_encode(data)) == data


async def test_sign_then_verify():
    pkcs8, pub = _keypair()
    token = await credentials.sign_jws({"sub": "x"}, pkcs8, "k1")
    assert token.count(".") == 2
    assert await credentials.verify_jws(token, pub) == {"sub": "x"}


async def test_tampered_payload_rejected():
    pkcs8, pub = _keypair()
    token = await credentials.sign_jws({"sub": "x"}, pkcs8, "k1")
    head, _, sig = token.split(".")
    forged = f"{head}.{credentials._json_b64({'sub': 'evil'})}.{sig}"
    assert await credentials.verify_jws(forged, pub) is None


async def test_wrong_key_rejected():
    pkcs8, _ = _keypair()
    _, other_pub = _keypair()
    token = await credentials.sign_jws({"sub": "x"}, pkcs8, "k1")
    assert await credentials.verify_jws(token, other_pub) is None


async def test_alg_none_rejected():
    _, pub = _keypair()
    head = credentials._json_b64({"alg": "none", "typ": "JWT"})
    token = f"{head}.{credentials._json_b64({'sub': 'x'})}."
    assert await credentials.verify_jws(token, pub) is None


@pytest.mark.parametrize("bad", ["", "a.b", "not.a.jws", "a.b.c.d"])
async def test_malformed_token_returns_none(bad):
    _, pub = _keypair()
    assert await credentials.verify_jws(bad, pub) is None


def _sign_raw(header, payload, pkcs8):
    key = serialization.load_der_private_key(pkcs8, password=None)
    head = credentials._json_b64(header)
    body = credentials._json_b64(payload)
    sig = key.sign(f"{head}.{body}".encode("ascii"))
    return f"{head}.{body}.{credentials.b64url_encode(sig)}"


async def test_helper_produces_valid_token():
    # control: proves the negative tests below fail for the reason they claim
    pkcs8, pub = _keypair()
    token = _sign_raw({"alg": "EdDSA", "typ": "JWT"}, {"sub": "x"}, pkcs8)
    assert await credentials.verify_jws(token, pub) == {"sub": "x"}


@pytest.mark.parametrize("alg", ["none", "HS256", "RS256", "eddsa", ""])
async def test_validly_signed_token_with_unsupported_alg_rejected(alg):
    pkcs8, pub = _keypair()
    token = _sign_raw({"alg": alg, "typ": "JWT"}, {"sub": "x"}, pkcs8)
    assert await credentials.verify_jws(token, pub) is None


async def test_validly_signed_token_with_crit_header_rejected():
    pkcs8, pub = _keypair()
    header = {"alg": "EdDSA", "crit": ["custom"], "custom": True}
    token = _sign_raw(header, {"sub": "x"}, pkcs8)
    assert await credentials.verify_jws(token, pub) is None


@pytest.mark.parametrize("payload", [[], "text", 123, True])
async def test_validly_signed_non_object_payload_rejected(payload):
    pkcs8, pub = _keypair()
    token = _sign_raw({"alg": "EdDSA", "typ": "JWT"}, payload, pkcs8)
    assert await credentials.verify_jws(token, pub) is None


async def test_trailing_garbage_on_signature_rejected():
    pkcs8, pub = _keypair()
    token = await credentials.sign_jws({"sub": "x"}, pkcs8, "k1")
    assert await credentials.verify_jws(token + "!!!!", pub) is None


@pytest.mark.parametrize("bad", ["AB", "A", "ab+/", "a=b", "ab\n"])
def test_b64url_decode_rejects_non_canonical_input(bad):
    with pytest.raises(ValueError):
        credentials.b64url_decode(bad)


def _jwk(kid="k1"):
    _, pub = _keypair()
    return {
        "kty": "OKP",
        "crv": "Ed25519",
        "x": credentials.b64url_encode(pub),
        "kid": kid,
    }


def test_load_public_jwks_empty_when_unconfigured():
    assert credentials.load_public_jwks("") == []


def test_load_public_jwks_valid_and_normalized():
    jwk = {**_jwk("k1"), "extra": "ignored"}
    out = credentials.load_public_jwks(json.dumps([jwk]))
    assert out == [{"kty": "OKP", "crv": "Ed25519", "x": jwk["x"],
                    "kid": "k1", "use": "sig", "alg": "EdDSA"}]


@pytest.mark.parametrize("mutate", [
    lambda j: {**j, "d": "secret"},                  # private key material
    lambda j: {**j, "kty": "RSA"},
    lambda j: {**j, "crv": "P-256"},
    lambda j: {**j, "kid": "bad#id"},
    lambda j: {**j, "x": "AAAA"},                    # wrong length
])
def test_load_public_jwks_rejects_bad_keys(mutate):
    with pytest.raises(ValueError):
        credentials.load_public_jwks(json.dumps([mutate(_jwk())]))


def test_load_public_jwks_rejects_duplicate_kid():
    with pytest.raises(ValueError):
        credentials.load_public_jwks(json.dumps([_jwk("k1"), _jwk("k1")]))
