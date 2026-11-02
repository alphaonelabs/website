"""
Tests for page-view counting (_page_view_path, record_page_view) and api_admin_views().
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, AsyncMock

from tests.helpers import (
    load_worker, MockRequest, MockRow, MockDB, make_env, make_stmt, basic_auth_header,
)

worker = load_worker()

BROWSER = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 Chrome/130 Safari/537.36"


def _req(url, ua=BROWSER, method="GET", **headers):
    if ua:
        headers["User-Agent"] = ua
    return MockRequest(method=method, url="https://learn.alphaonelabs.com" + url, headers=headers)


def _html(status=200, ctype="text/html; charset=utf-8"):
    return SimpleNamespace(status=status, headers={"Content-Type": ctype})


class TestPageViewPath:
    def test_counts_plain_pages(self):
        env = make_env()
        assert worker._page_view_path(_req("/"), env) == "/"
        assert worker._page_view_path(_req("/teach/"), env) == "/teach"
        assert worker._page_view_path(_req("/about.html"), env) == "/about"

    def test_activity_query_is_normalized_to_a_path(self):
        env = make_env()
        assert worker._page_view_path(_req("/activity?slug=gsoc-2027"), env) == "/activity/gsoc-2027"
        assert worker._page_view_path(_req("/activity/gsoc-2027"), env) == "/activity/gsoc-2027"
        assert worker._page_view_path(_req("/activity"), env) == "/activity"

    def test_skips_api_assets_and_admin(self):
        env = make_env()
        for url in ("/api/activities", "/media/x.webp", "/js/app.js", "/favicon.ico", "/admin", "/admin/api/views"):
            assert worker._page_view_path(_req(url), env) is None, url

    def test_skips_bots_prefetch_and_non_get(self):
        env = make_env()
        assert worker._page_view_path(_req("/", ua="Googlebot/2.1"), env) is None
        assert worker._page_view_path(_req("/", ua=""), env) is None
        assert worker._page_view_path(_req("/", **{"Sec-Purpose": "prefetch"}), env) is None
        assert worker._page_view_path(_req("/", method="POST"), env) is None


class TestRecordPageView:
    async def test_counts_html_200(self):
        stmt = make_stmt()
        db = MagicMock()
        db.prepare = MagicMock(return_value=stmt)
        env = make_env(db=db)
        await worker.record_page_view(_req("/activity/react"), env, _html())
        sql = db.prepare.call_args[0][0]
        assert "INSERT INTO page_views" in sql and "ON CONFLICT" in sql
        args = stmt.bind.call_args[0]
        assert args[1] == "/activity/react"
        stmt.bind.return_value.run.assert_awaited()

    async def test_ignores_errors_and_non_html(self):
        db = MagicMock()
        db.prepare = MagicMock()
        env = make_env(db=db)
        await worker.record_page_view(_req("/"), env, _html(status=404))
        await worker.record_page_view(_req("/"), env, _html(ctype="application/json"))
        db.prepare.assert_not_called()

    async def test_never_raises(self):
        db = MagicMock()
        db.prepare = MagicMock(side_effect=RuntimeError("D1 down"))
        env = make_env(db=db)
        await worker.record_page_view(_req("/"), env, _html())


class TestApiAdminViews:
    async def test_requires_basic_auth(self):
        r = await worker.api_admin_views(MockRequest(url="http://localhost/api/admin/views"), make_env())
        assert r.status == 401

    async def test_returns_totals_series_and_top_lists(self):
        env = make_env(db=MockDB([
            make_stmt(first=MockRow(today=4, last7=20, last30=90, all_time=120, since="2026-11-01")),
            make_stmt(all_results=[MockRow(day="2026-11-01", views=7)]),
            make_stmt(all_results=[MockRow(path="/", views=50), MockRow(path="/activity/react", views=9)]),
            make_stmt(all_results=[MockRow(path="/activity/react", views=9, title="React", slug="react", id="a1")]),
        ]))
        req = MockRequest(url="http://localhost/api/admin/views",
                          headers={"Authorization": basic_auth_header("admin", "adminpass")})
        r = await worker.api_admin_views(req, env)
        assert r.status == 200
        data = json.loads(r.body)
        assert data["totals"]["last30"] == 90
        assert len(data["daily"]) == 30
        assert data["top_pages"][0] == {"path": "/", "views": 50}
        assert data["top_activities"][0]["title"] == "React"
