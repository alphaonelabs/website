import base64
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("cryptography")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

import credentials  # noqa: E402
from tests.helpers import MockDB, MockRequest, MockRow, load_worker, make_env, make_stmt  # noqa: E402

worker = load_worker()

ENC_KEY = "test-encryption-key"
ISSUER = "https://learn.example.org"
KID = "k1"


def _keypair():
    key = Ed25519PrivateKey.generate()
    pkcs8 = key.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    pub = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return pkcs8, pub


def _env(db, *, configured=True, jwks_kid=KID):
    env = make_env(db=db)
    env.SENTRY_DSN = ""
    env.CREDENTIAL_ISSUER_URL = ISSUER if configured else ""
    env.CREDENTIAL_SIGNING_KID = KID if configured else ""
    env.CREDENTIAL_SIGNING_KEY = ""
    env.CREDENTIAL_PUBLIC_JWKS = None
    pub = b""
    if configured:
        pkcs8, pub = _keypair()
        env.CREDENTIAL_SIGNING_KEY = base64.b64encode(pkcs8).decode()
        env.CREDENTIAL_PUBLIC_JWKS = json.dumps([{
            "kty": "OKP", "crv": "Ed25519",
            "x": credentials.b64url_encode(pub), "kid": jwks_kid,
        }])
    return env, pub


def _enrollment(**kw):
    row = dict(id="enr-1", user_id="u1", host_id="h1", activity_id="a1", status="completed")
    row.update(kw)
    return MockRow(**row)


def _activity():
    return MockRow(id="a1", title="Intro to Python", description="")


def _learner_name():
    # Legacy XOR ciphertext is accepted by decrypt_aes, so no AES stub is needed.
    return MockRow(name=worker._encrypt_xor("Jane Doe", ENC_KEY))


def _generate_request(user_id, body):
    token = worker.create_token(user_id, "someone", "member", "test-jwt-secret")
    return MockRequest(
        method="POST",
        url="http://localhost/api/certificates/generate/enr-1",
        headers={"Authorization": "Bearer " + token},
        body=None if body is None else json.dumps(body),
    )


def _data(resp):
    return json.loads(resp.body)["data"]


# ---- the hook on its own -------------------------------------------------------

async def test_hook_issues_signed_credential_with_consented_name():
    insert = make_stmt()
    db = MockDB([make_stmt(first=_activity()), make_stmt(first=_learner_name()),
                 make_stmt(first=None), make_stmt(first=MockRow(idx=1)),insert,])
    env, pub = _env(db)

    cred_id = await worker._issue_credential_for_certificate(
        env, MockRequest(), _enrollment(), "cert-1", "u1", True
    )

    args = insert.bind.call_args.args
    assert cred_id == args[0]
    assert args[1:4] == ("cert-1", "u1", "a1")
    assert args[5] == 1 and args[7] == KID
    header = json.loads(credentials.b64url_decode(args[6].split(".")[0]))
    assert header["typ"] == "vc+jwt" and header["kid"] == KID
    payload = await credentials.verify_jws(args[6], pub)
    subject = payload["credentialSubject"]
    assert subject["id"] == args[4]  # stored subject_id
    assert subject["id"].startswith("urn:uuid:")
    assert subject["identifier"] == [{
    "type": "IdentityObject",
    "identityType": "name",
    "hashed": False,
    "identityHash": "Jane Doe",
}]


async def test_hook_without_consent_signs_no_name():
    insert = make_stmt()
    db = MockDB([make_stmt(first=_activity()), make_stmt(first=None), make_stmt(first=MockRow(idx=1)),insert,])
    env, pub = _env(db)

    await worker._issue_credential_for_certificate(
        env, MockRequest(), _enrollment(), "cert-1", "u1", False
    )

    args = insert.bind.call_args.args
    payload = await credentials.verify_jws(args[6], pub)
    assert args[5] == 0
    assert "identifier" not in payload["credentialSubject"]
    assert "Jane" not in json.dumps(payload)


async def test_hook_ignores_host_caller():
    db = MockDB([])
    env, _ = _env(db)
    out = await worker._issue_credential_for_certificate(
        env, MockRequest(), _enrollment(), "cert-1", "h1", True
    )
    assert out == "" and db._idx == 0


async def test_hook_skips_when_not_configured():
    db = MockDB([])
    env, _ = _env(db, configured=False)
    out = await worker._issue_credential_for_certificate(
        env, MockRequest(), _enrollment(), "cert-1", "u1", True
    )
    assert out == "" and db._idx == 0


async def test_hook_refuses_when_kid_not_published():
    db = MockDB([])
    env, _ = _env(db, jwks_kid="other")
    out = await worker._issue_credential_for_certificate(
        env, MockRequest(), _enrollment(), "cert-1", "u1", True
    )
    assert out == "" and db._idx == 0


async def test_hook_returns_existing_credential():
    db = MockDB([make_stmt(first=_activity()), make_stmt(first=MockRow(id="cred-0"))])
    env, _ = _env(db)
    out = await worker._issue_credential_for_certificate(
        env, MockRequest(), _enrollment(), "cert-1", "u1", False
    )
    assert out == "cred-0" and db._idx == 2


async def test_hook_never_raises_when_signing_fails(monkeypatch):
    async def boom(*_a, **_k):
        raise RuntimeError("no key")

    monkeypatch.setattr(credentials, "sign_jws", boom)
    db = MockDB([make_stmt(first=_activity()), make_stmt(first=None)])
    env, _ = _env(db)
    out = await worker._issue_credential_for_certificate(
        env, MockRequest(), _enrollment(), "cert-1", "u1", False
    )
    assert out == ""


# ---- through api_generate_certificate (consent plumbing) -------------------------

async def test_generate_issues_named_credential_when_learner_consents():
    insert = make_stmt()
    db = MockDB([
        make_stmt(first=_enrollment()),    # enrollment lookup
        make_stmt(first=None),             # existing certificate?
        make_stmt(),                       # INSERT certificate
        make_stmt(first=_activity()),      # hook: activity
        make_stmt(first=_learner_name()),  # hook: learner name
        make_stmt(first=None),             # hook: existing credential?
        make_stmt(first=MockRow(idx=1)),
        insert,                            # hook: INSERT credential
    ])
    env, pub = _env(db)

    resp = await worker.api_generate_certificate(
        _generate_request("u1", {"include_name": True}), env, "enr-1"
    )

    assert resp.status == 200
    args = insert.bind.call_args.args
    assert _data(resp)["credential_id"] == args[0]
    assert args[5] == 1
    verified = await credentials.verify_jws(args[6], pub)
    assert verified["credentialSubject"]["id"] == args[4]
    assert verified["credentialSubject"]["identifier"][0]["identityHash"] == "Jane Doe"


@pytest.mark.parametrize("body", [None, {}, {"include_name": False},
                                  {"include_name": "yes"}, {"include_name": 1}])
async def test_generate_without_explicit_true_never_discloses_name(body):
    insert = make_stmt()
    db = MockDB([
        make_stmt(first=_enrollment()),
        make_stmt(first=None),
        make_stmt(),
        make_stmt(first=_activity()),
        make_stmt(first=None),
        make_stmt(first=MockRow(idx=1)),
        insert,
    ])
    env, pub = _env(db)

    resp = await worker.api_generate_certificate(_generate_request("u1", body), env, "enr-1")

    assert resp.status == 200
    args = insert.bind.call_args.args
    assert args[5] == 0
    payload = await credentials.verify_jws(args[6], pub)
    assert "identifier" not in payload["credentialSubject"]
    assert payload["credentialSubject"]["id"] == args[4]


async def test_generate_by_host_creates_certificate_but_no_credential():
    db = MockDB([make_stmt(first=_enrollment()), make_stmt(first=None), make_stmt()])
    env, _ = _env(db)

    resp = await worker.api_generate_certificate(
        _generate_request("h1", {"include_name": True}), env, "enr-1"
    )

    assert resp.status == 200
    assert _data(resp)["uuid"]
    assert "credential_id" not in _data(resp)


async def test_generate_issues_credential_for_pre_existing_certificate():
    insert = make_stmt()
    db = MockDB([
        make_stmt(first=_enrollment()),
        make_stmt(first=MockRow(id="cert-0")),   # certificate already exists
        make_stmt(first=_activity()),
        make_stmt(first=_learner_name()),
        make_stmt(first=None),
        make_stmt(first=MockRow(idx=1)),
        insert,
    ])
    env, _ = _env(db)

    resp = await worker.api_generate_certificate(
        _generate_request("u1", {"include_name": True}), env, "enr-1"
    )

    assert _data(resp)["uuid"] == "cert-0"
    assert _data(resp)["credential_id"] == insert.bind.call_args.args[0]

@pytest.mark.parametrize("url", [
    "https://learn.example.org?tenant=x",
    "https://learn.example.org#frag",
    "https://learn.example.org/sub",
])
def test_issuer_url_rejects_query_fragment_and_path(url):
    env = make_env()
    env.CREDENTIAL_ISSUER_URL = url
    assert worker._credential_issuer_url(env) == ""


def test_issuer_url_accepts_plain_origin():
    env = make_env()
    env.CREDENTIAL_ISSUER_URL = "https://learn.example.org/"
    assert worker._credential_issuer_url(env) == "https://learn.example.org"


async def test_generate_issues_credential_when_certificate_insert_races():
    losing_insert = make_stmt()
    losing_insert.bind.return_value.run.side_effect = Exception("UNIQUE constraint failed")
    insert = make_stmt()
    db = MockDB([
        make_stmt(first=_enrollment()),
        make_stmt(first=None),                    # no certificate yet
        losing_insert,                            # host inserted it first
        make_stmt(first=MockRow(id="cert-0")),    # existing_after
        make_stmt(first=_activity()),
        make_stmt(first=_learner_name()),
        make_stmt(first=None),
        make_stmt(first=MockRow(idx=1)),
        insert,
    ])
    env, _ = _env(db)

    resp = await worker.api_generate_certificate(
        _generate_request("u1", {"include_name": True}), env, "enr-1"
    )

    assert _data(resp)["uuid"] == "cert-0"
    assert _data(resp)["credential_id"] == insert.bind.call_args.args[0]