import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("cryptography")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

import credentials  # noqa: E402
import open_badges as ob  # noqa: E402
from tests.helpers import MockDB, MockRequest, MockRow, load_worker, make_env, make_stmt  # noqa: E402

worker = load_worker()

ISSUER = "https://learn.example.org"
KID = "k1"
TOKEN = "A" * 22

_key = Ed25519PrivateKey.generate()
PKCS8 = _key.private_bytes(
    serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
)
PUB = _key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
JWKS = json.dumps([{"kty": "OKP", "crv": "Ed25519", "x": credentials.b64url_encode(PUB), "kid": KID}])


async def _jws(name=None, token=TOKEN):
    cred = ob.build_open_badge_credential(
        base_url=ISSUER, token=token, issuer_name="Alpha One Labs",
        achievement_id=f"{ISSUER}/achievements/a1", achievement_name="Intro to Python",
        achievement_description="Learn Python basics", criteria_narrative="Completed.",
        issued_at="2026-11-15T10:00:00Z", subject_id="urn:uuid:11111111-1111-1111-1111-111111111111",
        learner_name=name,
    )
    return await credentials.sign_jws(cred, PKCS8, KID, typ="vc+jwt")


def _env(row, configured=True, jwks=JWKS):
    env = make_env(db=MockDB([make_stmt(first=row)]))
    env.SENTRY_DSN = ""
    env.CREDENTIAL_ISSUER_URL = ISSUER if configured else ""
    env.CREDENTIAL_PUBLIC_JWKS = jwks
    return env


def _row(jws, status="active"):
    return MockRow(id=TOKEN, credential_jws=jws, kid=KID, status=status, issued_at="2026-11-15T10:00:00Z")


def _req(accept=None):
    return MockRequest(method="GET", url=f"http://localhost/credentials/{TOKEN}",
                       headers={"Accept": accept} if accept else {})


async def test_html_page_shows_valid_credential_with_name():
    env = _env(_row(await _jws("Jane Doe")))
    r = await worker.api_get_credential(_req(), env, TOKEN)
    assert r.status == 200
    assert "Signature valid" in r.body and "Jane Doe" in r.body


async def test_html_page_without_name_says_not_disclosed():
    env = _env(_row(await _jws()))
    r = await worker.api_get_credential(_req(), env, TOKEN)
    assert "Name not disclosed" in r.body


async def test_name_is_html_escaped():
    env = _env(_row(await _jws("<script>alert(1)</script>")))
    r = await worker.api_get_credential(_req(), env, TOKEN)
    assert "<script>alert(1)" not in r.body
    assert "&lt;script&gt;" in r.body


async def test_json_accept_returns_credential():
    env = _env(_row(await _jws()))
    r = await worker.api_get_credential(_req("application/json"), env, TOKEN)
    assert r.status == 200
    assert r.headers["Content-Type"] == "application/ld+json"
    assert json.loads(r.body)["id"] == f"{ISSUER}/credentials/{TOKEN}"


async def test_jwt_suffix_returns_stored_jws():
    jws = await _jws()
    env = _env(_row(jws))
    r = await worker.api_get_credential(_req(), env, TOKEN, ".jwt")
    assert r.status == 200 and r.body == jws
    assert r.headers["Content-Type"] == "application/vc+jwt"


async def test_revoked_is_410_for_machines_and_flagged_in_html():
    jws = await _jws()
    r = await worker.api_get_credential(_req(), _env(_row(jws, "revoked")), TOKEN, ".json")
    assert r.status == 410
    page = await worker.api_get_credential(_req(), _env(_row(jws, "revoked")), TOKEN)
    assert page.status == 200 and "revoked" in page.body


async def test_unknown_token_is_404():
    r = await worker.api_get_credential(_req(), _env(None), TOKEN)
    assert r.status == 404


async def test_unconfigured_issuer_is_404():
    r = await worker.api_get_credential(_req(), _env(_row(await _jws()), configured=False), TOKEN)
    assert r.status == 404

async def test_tampered_signature_is_reported_invalid():
    jws = await _jws()
    head, payload, sig = jws.split(".")
    raw = bytearray(credentials.b64url_decode(sig))
    raw[0] ^= 0x01
    bad = ".".join([head, payload, credentials.b64url_encode(bytes(raw))])
    page = await worker.api_get_credential(_req(), _env(_row(bad)), TOKEN)
    assert "could not be verified" in page.body
    assert "signature does not match" in page.body
    machine = await worker.api_get_credential(_req(), _env(_row(bad)), TOKEN, ".json")
    assert machine.status == 500


async def test_key_missing_from_jwks_is_invalid():
    other = json.dumps([{"kty": "OKP", "crv": "Ed25519",
                         "x": credentials.b64url_encode(PUB), "kid": "other"}])
    page = await worker.api_get_credential(_req(), _env(_row(await _jws()), jwks=other), TOKEN)
    assert "could not be verified" in page.body


def test_credential_pages_are_not_counted_as_page_views():
    env = make_env()
    req = MockRequest(method="GET", url=f"http://localhost/credentials/{TOKEN}",
                      headers={"User-Agent": "Mozilla/5.0 (X11; Linux) Firefox/120"})
    assert worker._page_view_path(req, env) is None


def test_route_regex_only_accepts_22_char_tokens():
    assert worker._CREDENTIAL_PATH_RE.fullmatch(f"/credentials/{TOKEN}.json")
    assert not worker._CREDENTIAL_PATH_RE.fullmatch("/credentials/short")
    assert not worker._CREDENTIAL_PATH_RE.fullmatch(f"/credentials/{TOKEN}/extra")

async def test_responses_are_not_cacheable_and_vary_on_accept():
    jws = await _jws()
    for suffix in (None, ".json", ".jwt"):
        r = await worker.api_get_credential(_req(), _env(_row(jws)), TOKEN, suffix)
        assert r.headers["Cache-Control"] == "no-store"
        assert r.headers["Vary"] == "Accept"
    revoked = await worker.api_get_credential(_req(), _env(_row(jws, "revoked")), TOKEN, ".json")
    assert revoked.status == 410
    assert revoked.headers["Cache-Control"] == "no-store"