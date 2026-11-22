import base64
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("cryptography")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

import credentials  # noqa: E402
import open_badges as ob  # noqa: E402
import status_list as sl  # noqa: E402
from tests.helpers import MockDB, MockRequest, MockRow, load_worker, make_env, make_stmt  # noqa: E402

worker = load_worker()

ISSUER = "https://learn.example.org"
LIST_URL = f"{ISSUER}/status-lists/revocation/1"
KID = "k1"
TOKEN = "B" * 22

_key = Ed25519PrivateKey.generate()
PKCS8 = _key.private_bytes(
    serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
)
PUB = _key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def _env(db, configured=True):
    env = make_env(db=db)
    env.SENTRY_DSN = ""
    env.CREDENTIAL_ISSUER_URL = ISSUER if configured else ""
    env.CREDENTIAL_SIGNING_KID = KID
    env.CREDENTIAL_SIGNING_KEY = base64.b64encode(PKCS8).decode()
    return env


def _auth_request(method, path, body=None):
    tok = worker.create_token("u1", "someone", "member", "test-jwt-secret")
    return MockRequest(method=method, url=f"http://localhost{path}",
                       headers={"Authorization": "Bearer " + tok},
                       body=None if body is None else json.dumps(body))


# ---- bitstring helpers ---------------------------------------------------------

def test_bit_zero_is_the_leftmost_bit_of_the_first_byte():
    bits = sl.decode_list(sl.encode_list([0, 9]))
    assert bits[0] == 0b10000000
    assert bits[1] == 0b01000000
    assert len(bits) == sl.STATUS_LIST_SIZE // 8


def test_only_requested_indexes_are_set_and_out_of_range_is_ignored():
    revoked = {3, 100, 131071}
    bits = sl.decode_list(sl.encode_list(list(revoked) + [-1, 131072]))
    assert {i for i in range(sl.STATUS_LIST_SIZE) if sl.is_set(bits, i)} == revoked


def test_encoded_list_is_multibase_base64url_without_padding():
    encoded = sl.encode_list([])
    assert encoded.startswith("u") and "=" not in encoded


def test_status_entry_shape():
    assert sl.build_status_entry(LIST_URL, 7) == {
        "id": f"{LIST_URL}#7",
        "type": "BitstringStatusListEntry",
        "statusPurpose": "revocation",
        "statusListIndex": "7",
        "statusListCredential": LIST_URL,
    }


# ---- issuance embeds the entry ---------------------------------------------------

async def test_issued_credential_carries_status_entry_and_stores_index():
    insert = make_stmt()
    db = MockDB([make_stmt(first=None), make_stmt(first=MockRow(idx=5)), insert])
    seen = {}

    async def sign(payload, kid):
        seen["payload"] = payload
        return "h.p.s"

    await ob.issue_open_badge(
        db=db, sign_fn=sign, kid=KID, base_url=ISSUER, issuer_name="Alpha One Labs",
        user_id="u1", certificate_id="c1", activity_id="a1",
        achievement_name="Intro", achievement_description="d", criteria_narrative="n",
        status_list_url=LIST_URL,
    )
    assert seen["payload"]["credentialStatus"] == sl.build_status_entry(LIST_URL, 5)
    assert insert.bind.call_args.args[9] == 5


async def test_full_status_list_aborts_issuance():
    db = MockDB([make_stmt(first=None), make_stmt(first=MockRow(idx=sl.STATUS_LIST_SIZE))])

    async def sign(payload, kid):
        raise AssertionError("must not sign")

    with pytest.raises(ValueError):
        await ob.issue_open_badge(
            db=db, sign_fn=sign, kid=KID, base_url=ISSUER, issuer_name="x",
            user_id="u1", certificate_id="c1", activity_id="a1",
            achievement_name="n", achievement_description="d", criteria_narrative="c",
            status_list_url=LIST_URL,
        )


# ---- status list endpoint --------------------------------------------------------

async def test_status_list_is_signed_and_marks_exactly_the_revoked_slots():
    rows = [MockRow(status_list_index=3), MockRow(status_list_index=12)]
    r = await worker.api_get_status_list(MockRequest(), _env(MockDB([make_stmt(all_results=rows)])))
    assert r.status == 200
    assert r.headers["Content-Type"] == "application/vc+jwt"
    assert r.headers["Cache-Control"] == "no-store"
    payload = await credentials.verify_jws(r.body, PUB)
    assert payload["type"] == ["VerifiableCredential", "BitstringStatusListCredential"]
    assert payload["id"] == LIST_URL
    subject = payload["credentialSubject"]
    assert subject["statusPurpose"] == "revocation"
    bits = sl.decode_list(subject["encodedList"])
    assert {i for i in range(64) if sl.is_set(bits, i)} == {3, 12}


async def test_status_list_404_when_unconfigured():
    r = await worker.api_get_status_list(MockRequest(), _env(MockDB([]), configured=False))
    assert r.status == 404


# ---- revoke ----------------------------------------------------------------------

async def test_holder_can_revoke_and_binds_reason_token_and_user():
    stmt = make_stmt()
    env = _env(MockDB([stmt]))
    r = await worker.api_revoke_credential(
        _auth_request("POST", f"/api/credentials/{TOKEN}/revoke", {"reason": "x" * 500}), env, TOKEN)
    assert r.status == 200
    reason, tok, uid = stmt.bind.call_args.args
    assert (tok, uid) == (TOKEN, "u1") and len(reason) == 200


async def test_revoke_defaults_reason_when_body_is_empty():
    stmt = make_stmt()
    r = await worker.api_revoke_credential(
        _auth_request("POST", f"/api/credentials/{TOKEN}/revoke"), _env(MockDB([stmt])), TOKEN)
    assert r.status == 200
    assert stmt.bind.call_args.args[0] == "learner_request"


async def test_revoke_of_someone_elses_or_already_revoked_credential_is_404():
    stmt = make_stmt()
    stmt.bind.return_value.run.return_value = SimpleNamespace(meta={"changes": 0})
    r = await worker.api_revoke_credential(
        _auth_request("POST", f"/api/credentials/{TOKEN}/revoke", {}), _env(MockDB([stmt])), TOKEN)
    assert r.status == 404


async def test_revoke_requires_login_and_valid_body():
    anon = MockRequest(method="POST", url="http://localhost/x", headers={})
    assert (await worker.api_revoke_credential(anon, _env(MockDB([])), TOKEN)).status == 401
    bad = _auth_request("POST", "/x", {"reason": 5})
    assert (await worker.api_revoke_credential(bad, _env(MockDB([])), TOKEN)).status == 400


# ---- wallet list -----------------------------------------------------------------

async def test_wallet_lists_only_the_callers_credentials():
    stmt = make_stmt(all_results=[MockRow(id=TOKEN, status="active", name_disclosed=1,
                                          issued_at="2026-11-21T00:00:00Z", title="Intro")])
    r = await worker.api_list_my_credentials(_auth_request("GET", "/api/credentials"),
                                             _env(MockDB([stmt])))
    assert r.status == 200
    item = json.loads(r.body)["data"]["credentials"][0]
    assert item["url"] == f"{ISSUER}/credentials/{TOKEN}" and item["name_disclosed"] is True
    assert stmt.bind.call_args.args == ("u1",)


async def test_wallet_requires_login():
    anon = MockRequest(method="GET", url="http://localhost/api/credentials", headers={})
    assert (await worker.api_list_my_credentials(anon, _env(MockDB([])))).status == 401


def test_revoke_route_regex_and_view_skip():
    assert worker._CREDENTIAL_REVOKE_RE.fullmatch(f"/api/credentials/{TOKEN}/revoke")
    assert not worker._CREDENTIAL_REVOKE_RE.fullmatch("/api/credentials/short/revoke")
    req = MockRequest(method="GET", url="http://localhost/status-lists/revocation/1",
                      headers={"User-Agent": "Mozilla/5.0 (X11; Linux) Firefox/120"})
    assert worker._page_view_path(req, make_env()) is None