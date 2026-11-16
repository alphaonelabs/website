"""Open Badges 3.0 credential building and issuance.

Builds an OpenBadgeCredential, signs it with the Ed25519 helpers from
credentials.py, and stores it next to the existing certificate row.

Design rules:
  * The learner's name is included only when they explicitly opted in.
  * No email address or internal user id ever appears in the credential.
  * subject_id is a random per-credential urn:uuid, so credentials of one
    learner cannot be linked to each other by third parties.
  * A stored credential is never modified; changes mean revoke + reissue.
"""

import re
import base64
import os
import uuid
from datetime import datetime, timezone

OB3_CONTEXTS = [
    "https://www.w3.org/ns/credentials/v2",
    "https://purl.imsglobal.org/spec/ob/v3p0/context-3.0.3.json",
]

MAX_LEARNER_NAME_LEN = 200
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def utc_now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_credential_token():
    """Unguessable id used in the public URL (128 bits)."""
    return base64.urlsafe_b64encode(os.urandom(16)).rstrip(b"=").decode("ascii")

def new_subject_id():
    return f"urn:uuid:{uuid.uuid4()}"


def credential_url(base_url, token):
    return f"{base_url.rstrip('/')}/credentials/{token}"


def clean_learner_name(name):
    """Normalise a display name. Returns None for blank input; raises on abuse."""
    if not isinstance(name, str):
        return None
    cleaned = " ".join(_CONTROL_CHARS.sub(" ", name).split())
    if not cleaned:
        return None
    if len(cleaned) > MAX_LEARNER_NAME_LEN:
        raise ValueError("learner name is too long")
    return cleaned


def build_open_badge_credential(
    *,
    base_url,
    token,
    issuer_name,
    achievement_id,
    achievement_name,
    achievement_description,
    criteria_narrative,
    issued_at,
    subject_id,
    learner_name=None,
):
    """Return an unsigned OpenBadgeCredential as a plain dict.

    Pass learner_name only if the learner consented to a publicly
    identifiable credential.
    """
    base = base_url.rstrip("/")

    subject = {
        "id": subject_id,
        "type": ["AchievementSubject"],
        "achievement": {
            "id": achievement_id,
            "type": ["Achievement"],
            "name": achievement_name,
            "description": achievement_description,
            "criteria": {"narrative": criteria_narrative},
        },
    }

    name = clean_learner_name(learner_name) if learner_name else None
    if name:
        subject["identifier"] = [
            {
                "type": "IdentityObject",
                "identityType": "name",
                "hashed": False,
                "identityHash": name,
            }
        ]

    return {
        "@context": list(OB3_CONTEXTS),
        "id": credential_url(base, token),
        "type": ["VerifiableCredential", "OpenBadgeCredential"],
        "issuer": {
            "id": base,
            "type": ["Profile"],
            "name": issuer_name,
            "url": base,
        },
        "name": achievement_name,
        "validFrom": issued_at,
        "credentialSubject": subject,
    }


# ---- storage (Cloudflare D1) -------------------------------------------------
# ADAPT: if the repo has its own D1 helpers, use those instead of these calls.

async def _find_active_credential(db, user_id, activity_id):
    return await (
        db.prepare(
            "SELECT id FROM credentials "
            "WHERE user_id = ? AND activity_id = ? AND status = 'active'"
        )
        .bind(user_id, activity_id)
        .first()
    )


async def _insert_credential(db, row):
    await (
        db.prepare(
            "INSERT INTO credentials "
            "(id, certificate_id, user_id, activity_id, subject_id, name_disclosed, "
            " credential_jws, kid, status, issued_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)"
        )
        .bind(
            row["id"],
            row["certificate_id"],
            row["user_id"],
            row["activity_id"],
            row["subject_id"],
            1 if row["name_disclosed"] else 0,
            row["credential_jws"],
            row["kid"],
            row["issued_at"],
        )
        .run()
    )


async def issue_open_badge(
    *,
    db,
    sign_fn,
    kid,
    base_url,
    issuer_name,
    user_id,
    certificate_id,
    activity_id,
    achievement_name,
    achievement_description,
    criteria_narrative,
    learner_name=None,
    include_name=False,
):
    """Issue (or return the existing) credential. Returns the credential token.

    sign_fn: async callable (payload: dict, kid: str) -> compact JWS string.
    Idempotent: a second call for the same learner and activity returns the
    existing active credential instead of creating a duplicate.
    """
    existing = await _find_active_credential(db, user_id, activity_id)
    if existing is not None:
        return existing.id  # ADAPT: use existing["id"] if your rows are dicts

    token = new_credential_token()
    subject_id = new_subject_id()
    issued_at = utc_now_iso()
    disclosed_name = clean_learner_name(learner_name) if include_name else None

    credential = build_open_badge_credential(
        base_url=base_url,
        token=token,
        issuer_name=issuer_name,
        achievement_id=f"{base_url.rstrip('/')}/achievements/{activity_id}",
        achievement_name=achievement_name,
        achievement_description=achievement_description,
        criteria_narrative=criteria_narrative,
        issued_at=issued_at,
        subject_id=subject_id,
        learner_name=disclosed_name,
    )

    jws = await sign_fn(credential, kid)

    try:
        await _insert_credential(
            db,
            {
                "id": token,
                "certificate_id": certificate_id,
                "user_id": user_id,
                "activity_id": activity_id,
                "subject_id": subject_id,
                "name_disclosed": disclosed_name is not None,
                "credential_jws": jws,
                "kid": kid,
                "issued_at": issued_at,
            },
        )
    except Exception:
        # Lost a race against a concurrent issue for the same learner/activity:
        # the unique index rejected us, so return the winner.
        winner = await _find_active_credential(db, user_id, activity_id)
        if winner is None:
            raise
        return winner.id  # ADAPT as above

    return token