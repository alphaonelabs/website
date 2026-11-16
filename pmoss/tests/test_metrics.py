"""
Unit tests for pmoss/src/metrics.py.
"""

import json
import pytest

from metrics import handle_get_metrics
from helpers import MockEnv, MockRequest, MockDB, make_stmt


CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
}

SESSION = {
    "id": "session-123",
    "username": "octocat",
    "accessToken": "gho_test_token",
}


class TestHandleGetMetrics:
    async def test_missing_repository_returns_400(self):
        req = MockRequest(url="https://example.com/api/metrics")
        env = MockEnv()
        resp = await handle_get_metrics(req, env, SESSION, CORS_HEADERS)
        assert resp.status == 400
        assert "repository parameter required" in resp.json().get("error", "")

    async def test_get_metrics_success(self):
        current_stats_stmt = make_stmt(first={
            "total_issues": 20,
            "open_issues": 15,
            "closed_issues": 5,
            "avg_time_to_close_hours": 48.0,
            "oldest_issue_date": "2026-01-01T00:00:00Z",
            "latest_update_date": "2026-03-01T00:00:00Z",
        })
        label_stats_stmt = make_stmt(all_results=[{"name": "bug", "color": "f00", "count": 10}])
        assignee_stats_stmt = make_stmt(all_results=[{"username": "alice", "assigned_issues": 8, "open_assigned": 6, "closed_assigned": 2}])
        historical_stmt = make_stmt(all_results=[{"metric_date": "2026-03-01", "total_issues": 20, "open_issues": 15, "closed_issues": 5, "avg_time_to_close": 48.0}])
        ttc_dist_stmt = make_stmt(all_results=[{"bucket": "1-7 days", "count": 5}])
        velocity_stmt = make_stmt(all_results=[{"date": "2026-03-01", "opened": 2}])
        closed_velocity_stmt = make_stmt(all_results=[{"date": "2026-03-01", "closed": 1}])

        db = MockDB([
            current_stats_stmt,
            label_stats_stmt,
            assignee_stats_stmt,
            historical_stmt,
            ttc_dist_stmt,
            velocity_stmt,
            closed_velocity_stmt,
        ])
        env = MockEnv(db=db)

        req = MockRequest(url="https://example.com/api/metrics?repository=owner/repo")
        resp = await handle_get_metrics(req, env, SESSION, CORS_HEADERS)

        assert resp.status == 200
        data = resp.json()
        assert data["current"]["total_issues"] == 20
        assert data["current"]["avg_time_to_close_days"] == "2.0"
        assert len(data["labels"]) == 1
        assert len(data["assignees"]) == 1
        assert len(data["historical"]) == 1
        assert data["time_to_close_distribution"] == [{"bucket": "1-7 days", "count": 5}]
        assert data["velocity"]["opened"] == [{"date": "2026-03-01", "opened": 2}]
        assert data["velocity"]["closed"] == [{"date": "2026-03-01", "closed": 1}]

    async def test_metrics_error_returns_500(self):
        stmt = make_stmt()
        stmt.bind.return_value.first.side_effect = Exception("Metrics calculation failed")
        env = MockEnv(db=MockDB([stmt]))

        req = MockRequest(url="https://example.com/api/metrics?repository=owner/repo")
        resp = await handle_get_metrics(req, env, SESSION, CORS_HEADERS)

        assert resp.status == 500
        assert "Metrics calculation failed" in resp.json().get("error", "")
