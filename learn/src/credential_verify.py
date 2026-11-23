"""Verify a stored Open Badges credential against the published public keys."""

import json
from typing import Any, Optional, TypedDict
import credentials

class VerifyResult(TypedDict):
    valid: bool
    reason: str
    payload: Optional[dict[str, Any]]
    kid: str

async def verify_credential_jws(
    jws: str, expected_id: str, expected_kid: str, jwks_raw: str
) -> VerifyResult:
    """Return {"valid", "reason", "payload", "kid"}. Reasons are fixed strings."""
    result = {"valid": False, "reason": "", "payload": None, "kid": expected_kid}
    try:
        header = json.loads(credentials.b64url_decode(jws.split(".")[0]))
        if not isinstance(header, dict) or header.get("typ") != "vc+jwt":
            result["reason"] = "unexpected credential type"
            return result
        if header.get("kid") != expected_kid:
            result["reason"] = "signing key mismatch"
            return result

        keys = {k["kid"]: k for k in credentials.load_public_jwks(jwks_raw)}
        key = keys.get(expected_kid)
        if key is None:
            result["reason"] = "signing key is not published"
            return result

        payload = await credentials.verify_jws(jws, credentials.b64url_decode(key["x"]))
        if payload is None:
            result["reason"] = "signature does not match"
            return result
        if payload.get("id") != expected_id:
            result["reason"] = "credential id mismatch"
            return result

        result.update(valid=True, payload=payload)
        return result
    except Exception:
        result["reason"] = "malformed credential"
        return result