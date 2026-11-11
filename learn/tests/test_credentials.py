import sys
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
