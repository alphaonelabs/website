"""
Unit tests for pmoss/src/api.py.
"""

import json
from unittest.mock import AsyncMock, patch
import pytest

from api import (
    handle_get_issues,
    handle_get_issue,
    handle_update_issue,
    handle_bulk_update,
    handle_sync_repository,
)
from helpers import MockEnv, MockRequest, MockDB, make_stmt


CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
}

SESSION = {
    "id": "session-123",
    "username": "octocat",
    "accessToken": "gho_test_token",
}


class TestHandleGetIssues:
    async def test_get_issues_default_params(self):
        issues_data = [
            {"id": 1, "number": 10, "title": "First Issue", "state": "open"},
            {"id": 2, "number": 11, "title": "Second Issue", "state": "closed"},
        ]
        issues_stmt = make_stmt(all_results=issues_data)
        labels_stmt_1 = make_stmt(all_results=[{"name": "bug", "color": "red"}])
        assignees_stmt_1 = make_stmt(all_results=[{"username": "alice"}])
        labels_stmt_2 = make_stmt(all_results=[])
        assignees_stmt_2 = make_stmt(all_results=[{"username": "bob"}])
        count_stmt = make_stmt(first={"total": 2})

        db = MockDB([
            issues_stmt,
            labels_stmt_1,
            assignees_stmt_1,
            labels_stmt_2,
            assignees_stmt_2,
            count_stmt,
        ])
        env = MockEnv(db=db)

        req = MockRequest(url="https://example.com/api/issues")
        resp = await handle_get_issues(req, env, SESSION, CORS_HEADERS)

        assert resp.status == 200
        data = resp.json()
        assert len(data["issues"]) == 2
        assert data["issues"][0]["labels"] == [{"name": "bug", "color": "red"}]
        assert data["issues"][0]["assignees"] == ["alice"]
        assert data["issues"][1]["assignees"] == ["bob"]
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["per_page"] == 50
        assert data["pagination"]["total"] == 2
        assert data["pagination"]["total_pages"] == 1

    async def test_get_issues_with_filters(self):
        issues_stmt = make_stmt(all_results=[{"id": 1, "number": 5, "title": "Filtered"}])
        labels_stmt = make_stmt(all_results=[])
        assignees_stmt = make_stmt(all_results=[])
        count_stmt = make_stmt(first={"total": 1})

        db = MockDB([issues_stmt, labels_stmt, assignees_stmt, count_stmt])
        env = MockEnv(db=db)

        req = MockRequest(
            url="https://example.com/api/issues?repository=owner/repo&state=open&label=enhancement&assignee=none&sort=created_at&order=asc&page=2&per_page=10"
        )
        resp = await handle_get_issues(req, env, SESSION, CORS_HEADERS)

        assert resp.status == 200
        data = resp.json()
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["per_page"] == 10
        # Check that conditions were added to SQL
        query = db.queries[0]
        assert "i.repository = ?" in query
        assert "i.state = ?" in query
        assert "INNER JOIN labels l" in query
        assert "i.assignee IS NULL" in query
        assert "ORDER BY i.created_at ASC" in query
        assert "LIMIT ? OFFSET ?" in query

    async def test_get_issues_with_named_assignee(self):
        issues_stmt = make_stmt(all_results=[])
        count_stmt = make_stmt(first={"total": 0})
        db = MockDB([issues_stmt, count_stmt])
        env = MockEnv(db=db)

        req = MockRequest(url="https://example.com/api/issues?assignee=charlie")
        resp = await handle_get_issues(req, env, SESSION, CORS_HEADERS)

        assert resp.status == 200
        assert "INNER JOIN assignees a" in db.queries[0]

    async def test_get_issues_db_error_returns_500(self):
        stmt = make_stmt()
        stmt.bind.return_value.all.side_effect = Exception("DB Query Failed")
        env = MockEnv(db=MockDB([stmt]))

        req = MockRequest(url="https://example.com/api/issues")
        resp = await handle_get_issues(req, env, SESSION, CORS_HEADERS)

        assert resp.status == 500
        assert "DB Query Failed" in resp.json().get("error", "")


class TestHandleGetIssue:
    async def test_missing_repository_returns_400(self):
        req = MockRequest(url="https://example.com/api/issues/42")
        env = MockEnv()
        resp = await handle_get_issue(req, env, SESSION, "42", CORS_HEADERS)
        assert resp.status == 400
        assert "repository parameter required" in resp.json().get("error", "")

    async def test_issue_not_found_returns_404(self):
        select_stmt = make_stmt(first=None)
        env = MockEnv(db=MockDB([select_stmt]))
        req = MockRequest(url="https://example.com/api/issues/999?repository=owner/repo")
        resp = await handle_get_issue(req, env, SESSION, "999", CORS_HEADERS)
        assert resp.status == 404
        assert "Issue not found" in resp.json().get("error", "")

    async def test_issue_found_returns_issue_with_details(self):
        issue_data = {
            "id": 42,
            "number": 42,
            "title": "Existing issue",
            "repository": "owner/repo",
            "state": "open",
        }
        issue_stmt = make_stmt(first=issue_data)
        labels_stmt = make_stmt(all_results=[{"name": "documentation", "color": "0075ca"}])
        assignees_stmt = make_stmt(all_results=[{"username": "dave"}])

        db = MockDB([issue_stmt, labels_stmt, assignees_stmt])
        env = MockEnv(db=db)

        req = MockRequest(url="https://example.com/api/issues/42?repository=owner/repo")
        resp = await handle_get_issue(req, env, SESSION, "42", CORS_HEADERS)

        assert resp.status == 200
        data = resp.json()
        assert data["id"] == 42
        assert data["labels"] == [{"name": "documentation", "color": "0075ca"}]
        assert data["assignees"] == ["dave"]

    async def test_get_issue_db_error_returns_500(self):
        stmt = make_stmt()
        stmt.bind.return_value.first.side_effect = Exception("DB error")
        env = MockEnv(db=MockDB([stmt]))

        req = MockRequest(url="https://example.com/api/issues/42?repository=owner/repo")
        resp = await handle_get_issue(req, env, SESSION, "42", CORS_HEADERS)

        assert resp.status == 500
        assert "DB error" in resp.json().get("error", "")


class TestHandleUpdateIssue:
    async def test_missing_repository_returns_400(self):
        req = MockRequest(
            method="PATCH",
            url="https://example.com/api/issues/12",
            body={"state": "closed"},
        )
        env = MockEnv()
        resp = await handle_update_issue(req, env, SESSION, "12", CORS_HEADERS)
        assert resp.status == 400
        assert "repository parameter required" in resp.json().get("error", "")

    async def test_update_issue_success(self):
        req = MockRequest(
            method="PATCH",
            url="https://example.com/api/issues/12?repository=owner/repo",
            body={"state": "closed"},
        )
        env = MockEnv()
        updated_gh_issue = {"id": 100, "number": 12, "state": "closed"}

        with patch("api.update_github_issue", new=AsyncMock(return_value=updated_gh_issue)) as mock_gh:
            with patch("api.sync_issue", new=AsyncMock()) as mock_sync:
                resp = await handle_update_issue(req, env, SESSION, "12", CORS_HEADERS)

        assert resp.status == 200
        data = resp.json()
        assert data["success"] is True
        assert data["issue"] == updated_gh_issue
        mock_gh.assert_awaited_once_with("owner", "repo", "12", {"state": "closed"}, "gho_test_token")
        mock_sync.assert_awaited_once_with(updated_gh_issue, "owner/repo", env)

    async def test_update_issue_github_error_returns_500(self):
        req = MockRequest(
            method="PATCH",
            url="https://example.com/api/issues/12?repository=owner/repo",
            body={"title": "New Title"},
        )
        env = MockEnv()

        with patch("api.update_github_issue", side_effect=Exception("GitHub Rate Limit")):
            resp = await handle_update_issue(req, env, SESSION, "12", CORS_HEADERS)

        assert resp.status == 500
        assert "GitHub Rate Limit" in resp.json().get("error", "")


class TestHandleBulkUpdate:
    async def test_missing_required_fields_returns_400(self):
        req = MockRequest(
            method="PATCH",
            url="https://example.com/api/issues/bulk",
            body={"repository": "owner/repo"},  # missing issue_numbers, updates
        )
        env = MockEnv()
        resp = await handle_bulk_update(req, env, SESSION, CORS_HEADERS)
        assert resp.status == 400
        assert "required" in resp.json().get("error", "")

    async def test_bulk_update_success_and_partial_failure(self):
        req = MockRequest(
            method="PATCH",
            url="https://example.com/api/issues/bulk",
            body={
                "repository": "owner/repo",
                "issue_numbers": [1, 2],
                "updates": {"state": "closed"},
            },
        )
        env = MockEnv()

        async def fake_update(owner, repo, num, updates, token):
            if num == 1:
                return {"number": 1, "state": "closed"}
            raise Exception("Cannot close locked issue")

        with patch("api.update_github_issue", side_effect=fake_update):
            with patch("api.sync_issue", new=AsyncMock()):
                resp = await handle_bulk_update(req, env, SESSION, CORS_HEADERS)

        assert resp.status == 200
        data = resp.json()
        results = data["results"]
        assert len(results) == 2
        assert results[0] == {"issue_number": 1, "success": True}
        assert results[1]["issue_number"] == 2
        assert results[1]["success"] is False
        assert "Cannot close locked issue" in results[1]["error"]

    async def test_bulk_update_json_parse_error_returns_500(self):
        req = MockRequest(
            method="PATCH",
            url="https://example.com/api/issues/bulk",
            body="invalid-json",
        )
        env = MockEnv()
        resp = await handle_bulk_update(req, env, SESSION, CORS_HEADERS)
        assert resp.status == 500


class TestHandleSyncRepository:
    async def test_missing_repository_returns_400(self):
        req = MockRequest(
            method="POST",
            url="https://example.com/api/sync",
            body={},
        )
        env = MockEnv()
        resp = await handle_sync_repository(req, env, SESSION, CORS_HEADERS)
        assert resp.status == 400
        assert "repository parameter required" in resp.json().get("error", "")

    async def test_sync_repository_success(self):
        req = MockRequest(
            method="POST",
            url="https://example.com/api/sync",
            body={"repository": "owner/repo"},
        )
        env = MockEnv()

        sync_result = {"success": True, "count": 25}
        with patch("api.sync_repository", new=AsyncMock(return_value=sync_result)) as mock_sync:
            resp = await handle_sync_repository(req, env, SESSION, CORS_HEADERS)

        assert resp.status == 200
        assert resp.json() == sync_result
        mock_sync.assert_awaited_once_with("owner", "repo", "gho_test_token", env)

    async def test_sync_repository_error_returns_500(self):
        req = MockRequest(
            method="POST",
            url="https://example.com/api/sync",
            body={"repository": "owner/repo"},
        )
        env = MockEnv()

        with patch("api.sync_repository", side_effect=Exception("Sync failed")):
            resp = await handle_sync_repository(req, env, SESSION, CORS_HEADERS)

        assert resp.status == 500
        assert "Sync failed" in resp.json().get("error", "")
