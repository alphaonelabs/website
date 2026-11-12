
"""Generate an Ed25519 signing key for verifiable credentials.

Usage: python scripts/generate_signing_key.py <key-id>

Prints values for `wrangler secret put` / .dev.vars. Never commit the output.

First key: use the three printed lines as they are.

Rotating: keep the existing keys in CREDENTIAL_PUBLIC_JWKS and append the new JWK
(the single object inside the printed array). Every key needs a unique id, because
duplicate ids are rejected. Publish the new public key first, then switch
CREDENTIAL_SIGNING_KID and CREDENTIAL_SIGNING_KEY to the new key. Keep old public
keys published for as long as credentials signed with them exist.
"""
import base64
import json
import re
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


_SAFE_KID = re.compile(r"[A-Za-z0-9._:-]{1,64}")


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def main(kid: str) -> None:
    if not _SAFE_KID.fullmatch(kid):
        raise SystemExit(
            "Key id may only contain letters, digits, '.', '_', ':' and '-' (max 64)."
        )

    key = Ed25519PrivateKey.generate()
    pkcs8 = key.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    raw_public = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    jwk = {
        "kty": "OKP",
        "crv": "Ed25519",
        "x": b64url(raw_public),
        "kid": kid,
        "use": "sig",
        "alg": "EdDSA",
    }
    print(f"CREDENTIAL_SIGNING_KID={kid}")
    print(f"CREDENTIAL_SIGNING_KEY={base64.b64encode(pkcs8).decode('ascii')}")
    print(f"CREDENTIAL_PUBLIC_JWKS={json.dumps([jwk], separators=(',', ':'))}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dev-key-1")
