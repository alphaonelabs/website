"""Tests for POST /api/feedback (api_feedback)."""

import base64
import json
from unittest.mock import AsyncMock, patch

from tests.helpers import (
    load_worker, MockRequest, make_env, json_request, StrictD1, row_as_dict,
)

worker = load_worker()

JWT_SEC = "test-jwt-secret"
PAYLOAD = {"name": "Bob", "email": "bob@example.com", "message": "Nice site"}


def _parse(resp):
    return json.loads(resp.body)


def _enc(val: str) -> str:
    """Match the stub encrypt_aes output: 'v1:' + base64(12_zero_iv + plaintext)."""
    return "v1:" + base64.b64encode(b"\x00" * 12 + val.encode()).decode()


def _auth(uid="uid-alice", username="alice", role="member"):
    return {"Authorization": f"Bearer {worker.create_token(uid, username, role, JWT_SEC)}"}


class TestApiFeedback:
    async def test_non_post_returns_405(self):
        env = make_env(db=StrictD1())
        r = await worker.api_feedback(
            MockRequest(method="GET", url="http://localhost/api/feedback"), env
        )
        assert r.status == 405

    async def test_anonymous_feedback_saves_null_user_id(self):
        db = StrictD1()
        r = await worker.api_feedback(json_request("/api/feedback", PAYLOAD), make_env(db=db))
        assert r.status == 200
        assert len(db.writes) == 1
        row = row_as_dict(*db.writes[0])
        assert row["id"]
        assert row["user_id"] is None
        assert row["name"] == _enc("Bob")
        assert row["email"] == _enc("bob@example.com")
        assert row["message"] == _enc("Nice site")

    async def test_authenticated_feedback_saves_user_id(self):
        db = StrictD1()
        r = await worker.api_feedback(
            json_request("/api/feedback", PAYLOAD, headers=_auth("uid-alice")), make_env(db=db)
        )
        assert r.status == 200
        row = row_as_dict(*db.writes[0])
        assert row["user_id"] == "uid-alice"
        assert row["message"] == _enc("Nice site")

    async def test_missing_message_returns_400_without_insert(self):
        db = StrictD1()
        r = await worker.api_feedback(
            json_request("/api/feedback", {"name": "Bob", "message": "  "}), make_env(db=db)
        )
        assert r.status == 400
        assert db.writes == []

    async def test_message_too_long_returns_400(self):
        db = StrictD1()
        r = await worker.api_feedback(
            json_request("/api/feedback", {"message": "x" * 5001}), make_env(db=db)
        )
        assert r.status == 400
        assert db.writes == []

    async def test_honeypot_field_skips_insert(self):
        db = StrictD1()
        r = await worker.api_feedback(
            json_request("/api/feedback", {**PAYLOAD, "company_website": "spam.example"}),
            make_env(db=db),
        )
        assert r.status == 200
        assert db.writes == []

    async def test_db_failure_returns_500(self):
        db = StrictD1(run_error=Exception("boom"))
        with patch.object(worker, "capture_exception", new=AsyncMock()) as cap:
            r = await worker.api_feedback(
                json_request("/api/feedback", PAYLOAD), make_env(db=db)
            )
        assert r.status == 500
        cap.assert_awaited_once()