import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import open_badges as ob  # noqa: E402

BASE = "https://learn.alphaonelabs.com"


def _build(**kw):
    args = dict(
        base_url=BASE,
        token="tok123",
        issuer_name="Alpha One Labs",
        achievement_id=f"{BASE}/achievements/7",
        achievement_name="Intro to Python",
        achievement_description="Learn Python basics",
        criteria_narrative="Completed all lessons.",
        issued_at="2026-11-15T10:00:00Z",
        subject_id="urn:uuid:11111111-1111-1111-1111-111111111111",
    )
    args.update(kw)
    return ob.build_open_badge_credential(**args)


def test_shape():
    credential = _build()
    assert credential["@context"][0] == "https://www.w3.org/ns/credentials/v2"
    assert credential["type"] == ["VerifiableCredential", "OpenBadgeCredential"]
    assert credential["id"] == f"{BASE}/credentials/tok123"
    assert credential["credentialSubject"]["type"] == ["AchievementSubject"]
    assert credential["credentialSubject"]["achievement"]["name"] == "Intro to Python"


def test_name_absent_without_consent():
    credential = _build()
    assert "identifier" not in credential["credentialSubject"]
    assert "Jane" not in json.dumps(credential)


def test_name_present_with_consent():
    credential = _build(learner_name="  Jane   Doe ")
    identifier = credential["credentialSubject"]["identifier"][0]
    assert identifier["identityType"] == "name"
    assert identifier["identityHash"] == "Jane Doe"
    assert identifier["hashed"] is False


def test_no_email_or_user_id_leak():
    credential_json = json.dumps(_build(learner_name="Jane Doe"))
    assert "@" not in credential_json.replace("@context", "")
    assert "user_id" not in credential_json


def test_name_validation():
    assert ob.clean_learner_name("   ") is None
    with pytest.raises(ValueError):
        ob.clean_learner_name("x" * 201)


class _Stmt:
    def __init__(self, db, sql):
        self.db = db
        self.sql = sql
        self.args = ()

    def bind(self, *args):
        self.args = args
        return self

    async def first(self):
        # Active-credential lookup: bind(user_id, activity_id)
        for row in self.db.rows:
            if (
                row["user_id"] == self.args[0]
                and row["activity_id"] == self.args[1]
                and row["status"] == "active"
            ):
                return type("R", (), {"id": row["id"]})()
        return None

    async def run(self):
        a = self.args
        self.db.rows.append(
            dict(
                id=a[0], certificate_id=a[1], user_id=a[2], activity_id=a[3],
                subject_id=a[4], name_disclosed=a[5], credential_jws=a[6],
                kid=a[7], status="active", issued_at=a[8],
            )
        )


class FakeDB:
    def __init__(self):
        self.rows = []

    def prepare(self, sql):
        return _Stmt(self, sql)


async def _fake_sign(payload, kid):
    return f"hdr.{payload['id']}.sig"


async def _issue(db, **kw):
    args = dict(
        db=db, sign_fn=_fake_sign, kid="k1", base_url=BASE,
        issuer_name="Alpha One Labs", user_id="u1", certificate_id="c1",
        activity_id="a7", achievement_name="Intro to Python",
        achievement_description="Learn Python basics",
        criteria_narrative="Completed all lessons.",
        learner_name="Jane Doe", include_name=False,
    )
    args.update(kw)
    return await ob.issue_open_badge(**args)


@pytest.mark.asyncio
async def test_issue_is_idempotent():
    db = FakeDB()
    first = await _issue(db)
    second = await _issue(db)
    assert first == second
    assert len(db.rows) == 1


@pytest.mark.asyncio
async def test_consent_flag_stored():
    db = FakeDB()
    await _issue(db, include_name=True)
    assert db.rows[0]["name_disclosed"] == 1


@pytest.mark.asyncio
async def test_name_not_signed_without_consent():
    seen = {}

    async def capture(payload, kid):
        seen["payload"] = payload
        return "h.p.s"

    db = FakeDB()
    await _issue(db, sign_fn=capture, include_name=False, learner_name="Jane Doe")
    assert "Jane" not in json.dumps(seen["payload"])
    assert db.rows[0]["name_disclosed"] == 0


@pytest.mark.asyncio
async def test_name_signed_with_consent():
    seen = {}

    async def capture(payload, kid):
        seen["payload"] = payload
        return "h.p.s"

    await _issue(FakeDB(), sign_fn=capture, include_name=True, learner_name="Jane Doe")
    assert "Jane Doe" in json.dumps(seen["payload"])


@pytest.mark.asyncio
async def test_sign_failure_propagates_and_stores_nothing():
    async def boom(payload, kid):
        raise RuntimeError("no key")

    db = FakeDB()
    with pytest.raises(RuntimeError):
        await _issue(db, sign_fn=boom)
    assert db.rows == []