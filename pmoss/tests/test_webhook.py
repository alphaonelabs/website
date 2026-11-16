"""
Unit tests for pmoss/src/webhook.py.
"""

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch
import pytest

from webhook import verify_webhook_signature, handle_webhook, handle_issue_event
from helpers import MockEnv, MockRequest, MockDB, make_stmt


def _compute_signature(secret: str, body: str) -> str:
    """Compute sha256=<hex> signature matching GitHub Webhooks."""
    digest = hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"sha256={digest}"


class TestVerifyWebhookSignature:
    async def test_missing_signature_header_returns_false(self):
        req = MockRequest(headers={})
        env = MockEnv(webhook_secret="supersecret")
        assert await verify_webhook_signature(req, env) is False

    async def test_no_secret_configured_returns_true(self):
        req = MockRequest(
            headers={"X-Hub-Signature-256": "sha256=abcdef"},
            body="{}",
        )
        env = MockEnv(webhook_secret=None)
        assert await verify_webhook_signature(req, env) is True

    async def test_valid_signature_returns_true(self):
        secret = "my_webhook_secret_123"
        body = json.dumps({"action": "opened", "issue": {"number": 1}})
        sig = _compute_signature(secret, body)

        req = MockRequest(
            headers={"X-Hub-Signature-256": sig},
            body=body,
        )
        env = MockEnv(webhook_secret=secret)
        assert await verify_webhook_signature(req, env) is True

    async def test_invalid_signature_returns_false(self):
        secret = "my_webhook_secret_123"
        body = json.dumps({"action": "opened", "issue": {"number": 1}})

        req = MockRequest(
            headers={"X-Hub-Signature-256": "sha256=0000000000000000000000000000000000000000000000000000000000000000"},
            body=body,
        )
        env = MockEnv(webhook_secret=secret)
        assert await verify_webhook_signature(req, env) is False


class TestHandleWebhook:
    async def test_invalid_signature_returns_401(self):
        req = MockRequest(
            method="POST",
            headers={"X-Hub-Signature-256": "sha256=invalid"},
            body="{}",
        )
        env = MockEnv(webhook_secret="secret")
        resp = await handle_webhook(req, env)
        assert resp.status == 401
        assert "Invalid signature" in await resp.text()

    async def test_ping_event_returns_200_message(self):
        secret = "test_secret"
        body = json.dumps({"zen": "Keep it logically awesome."})
        sig = _compute_signature(secret, body)

        req = MockRequest(
            method="POST",
            headers={
                "X-Hub-Signature-256": sig,
                "X-GitHub-Event": "ping",
            },
            body=body,
        )
        env = MockEnv(webhook_secret=secret)
        resp = await handle_webhook(req, env)
        assert resp.status == 200
        data = resp.json()
        assert data.get("message") == "Webhook configured successfully"

    async def test_issues_event_triggers_handler(self):
        secret = "test_secret"
        payload = {
            "action": "opened",
            "repository": {"full_name": "owner/repo"},
            "issue": {
                "id": 101,
                "number": 1,
                "title": "Bug report",
                "body": "Something crashed",
                "state": "open",
                "created_at": "2026-01-01T10:00:00Z",
                "updated_at": "2026-01-01T10:00:00Z",
                "html_url": "https://github.com/owner/repo/issues/1",
                "labels": [{"name": "bug", "color": "d73a4a"}],
                "assignees": [{"login": "alice"}],
            },
        }
        body = json.dumps(payload)
        sig = _compute_signature(secret, body)

        req = MockRequest(
            method="POST",
            headers={
                "X-Hub-Signature-256": sig,
                "X-GitHub-Event": "issues",
            },
            body=body,
        )
        env = MockEnv(webhook_secret=secret)

        with patch("webhook.handle_issue_event", new=AsyncMock()) as mock_issue_handler:
            resp = await handle_webhook(req, env)
            assert resp.status == 200
            data = resp.json()
            assert data.get("status") == "processed"
            mock_issue_handler.assert_awaited_once_with(payload, env)

    async def test_unhandled_event_returns_processed(self):
        secret = "test_secret"
        body = json.dumps({"action": "created"})
        sig = _compute_signature(secret, body)

        req = MockRequest(
            method="POST",
            headers={
                "X-Hub-Signature-256": sig,
                "X-GitHub-Event": "star",
            },
            body=body,
        )
        env = MockEnv(webhook_secret=secret)
        resp = await handle_webhook(req, env)
        assert resp.status == 200
        assert resp.json().get("status") == "processed"

    async def test_webhook_processing_error_returns_500(self):
        secret = "test_secret"
        body = json.dumps({"action": "opened", "issue": {}})
        sig = _compute_signature(secret, body)

        req = MockRequest(
            method="POST",
            headers={
                "X-Hub-Signature-256": sig,
                "X-GitHub-Event": "issues",
            },
            body=body,
        )
        env = MockEnv(webhook_secret=secret)

        with patch("webhook.handle_issue_event", side_effect=Exception("DB Failure")):
            resp = await handle_webhook(req, env)

        assert resp.status == 500
        data = resp.json()
        assert "DB Failure" in data.get("error", "")


class TestHandleIssueEvent:
    async def test_handle_opened_issue_event(self):
        upsert_stmt = make_stmt()
        del_labels_stmt = make_stmt()
        ins_label_stmt = make_stmt()
        del_assignees_stmt = make_stmt()
        ins_assignee_stmt = make_stmt()

        db = MockDB([
            upsert_stmt,
            del_labels_stmt,
            ins_label_stmt,
            del_assignees_stmt,
            ins_assignee_stmt,
        ])
        env = MockEnv(db=db)

        payload = {
            "action": "opened",
            "repository": {"full_name": "owner/repo"},
            "issue": {
                "id": 555,
                "number": 42,
                "title": "Fix memory leak",
                "body": "Leak description",
                "state": "open",
                "created_at": "2026-03-01T12:00:00Z",
                "updated_at": "2026-03-01T12:00:00Z",
                "closed_at": None,
                "html_url": "https://github.com/owner/repo/issues/42",
                "assignee": {"login": "dev1"},
                "milestone": {"title": "v1.0"},
                "labels": [{"name": "perf", "color": "ffffff"}],
                "assignees": [{"login": "dev1"}],
            },
        }

        with patch("webhook.update_repository_metrics", new=AsyncMock()) as mock_metrics:
            await handle_issue_event(payload, env)
            mock_metrics.assert_awaited_once_with("owner/repo", env)

        # Verify DB calls were executed
        assert len(db.queries) == 5
        # Verify upsert bind parameters
        bind_args = upsert_stmt.bind.call_args[0]
        assert bind_args[0] == 555
        assert bind_args[1] == 42
        assert bind_args[2] == "Fix memory leak"
        assert bind_args[4] == "open"
        assert bind_args[9] == "owner/repo"
        assert bind_args[10] == "dev1"
        assert bind_args[11] == "v1.0"
        assert bind_args[12] is None  # time_to_close is None for open issue

    async def test_handle_closed_issue_event_calculates_time_to_close(self):
        upsert_stmt = make_stmt()
        del_labels_stmt = make_stmt()
        del_assignees_stmt = make_stmt()

        db = MockDB([upsert_stmt, del_labels_stmt, del_assignees_stmt])
        env = MockEnv(db=db)

        payload = {
            "action": "closed",
            "repository": {"full_name": "owner/repo"},
            "issue": {
                "id": 777,
                "number": 99,
                "title": "Closed issue",
                "body": "Done",
                "state": "closed",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-02T12:00:00Z",
                "closed_at": "2026-01-02T12:00:00Z",  # 36 hours later
                "html_url": "https://github.com/owner/repo/issues/99",
                "labels": [],
                "assignees": [],
            },
        }

        with patch("webhook.update_repository_metrics", new=AsyncMock()):
            await handle_issue_event(payload, env)

        # Check that time_to_close was calculated and passed (36 hours)
        bind_args = upsert_stmt.bind.call_args[0]
        assert bind_args[12] == 36
