
"""Generate an Ed25519 signing key for verifiable credentials.

Usage: python scripts/generate_signing_key.py my-key-2026-01
Prints values for `wrangler secret put` / .dev.vars. Never commit the output.
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
    print(f"PUBLIC_JWK={json.dumps(jwk, separators=(',', ':'))}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dev-key-1")
