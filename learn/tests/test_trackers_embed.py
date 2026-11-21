"""
Tests for the public tracker embed.

Covers:
- GET /api/trackers/embed/:code (public, read-only, public trackers only)
- the embeddable page (public/tracker-embed.html) and its route
- the embed page is the only page that may be shown inside another site's iframe
- the "Embed on another site" snippet on the tracker detail page
"""

import json
import re
from pathlib import Path

from tests.helpers import MockDB, MockRequest, MockRow, load_worker, make_env, make_stmt, set_static_content

worker = load_worker()

PUBLIC_DIR = Path(__file__).parent.parent / "public"
CODE = "123e4567-e89b-42d3-a456-426614174000"


def _parse(resp):
    return json.loads(resp.body)


def _get(path):
    return MockRequest(method="GET", url=f"http://localhost{path}")


def _public_row(**overrides):
    values = dict(title="Read books", description="One a week", current_value=3, target_value=10, color="green-600")
    values.update(overrides)
    return MockRow(**values)


class SqlRecordingDB(MockDB):
    """MockDB that also remembers the SQL it was asked to prepare."""

    def __init__(self, stmts=None):
        super().__init__(stmts)
        self.sql = []

    def prepare(self, sql):
        self.sql.append(" ".join(sql.split()))
        return super().prepare(sql)


class TestEmbedApi:
    async def test_public_tracker_is_returned_without_login(self):
        stmt = make_stmt(first=_public_row())
        r = await worker.api_get_tracker_embed(_get(f"/api/trackers/embed/{CODE}"), make_env(db=MockDB([stmt])), CODE)
        assert r.status == 200
        data = _parse(r)["data"]
        assert data["title"] == "Read books"
        assert data["percentage"] == 30
        assert stmt.bind.call_args.args == (CODE,)

    async def test_only_public_fields_are_exposed(self):
        stmt = make_stmt(first=_public_row())
        r = await worker.api_get_tracker_embed(_get(f"/api/trackers/embed/{CODE}"), make_env(db=MockDB([stmt])), CODE)
        assert set(_parse(r)["data"]) == {
            "title",
            "description",
            "current_value",
            "target_value",
            "percentage",
            "color",
        }

    async def test_query_only_matches_public_trackers(self):
        db = SqlRecordingDB([make_stmt(first=None)])
        await worker.api_get_tracker_embed(_get(f"/api/trackers/embed/{CODE}"), make_env(db=db), CODE)
        assert "WHERE embed_code = ? AND is_public = 1" in db.sql[0]
        # the query must never select the owner or the tracker id
        assert "user_id" not in db.sql[0].split("FROM")[0]

    async def test_private_or_unknown_tracker_is_404(self):
        r = await worker.api_get_tracker_embed(
            _get(f"/api/trackers/embed/{CODE}"), make_env(db=MockDB([make_stmt(first=None)])), CODE
        )
        assert r.status == 404
        assert "Tracker not found" in _parse(r)["error"]

    async def test_malformed_code_is_404_without_touching_the_database(self):
        db = SqlRecordingDB([make_stmt(first=_public_row())])
        for bad in ("abc", "t-1", CODE.upper(), CODE + "0", "../" + CODE):
            r = await worker.api_get_tracker_embed(_get(f"/api/trackers/embed/{bad}"), make_env(db=db), bad)
            assert r.status == 404
        assert db.sql == []

    async def test_percentage_is_capped_at_100(self):
        stmt = make_stmt(first=_public_row(current_value=250, target_value=100))
        r = await worker.api_get_tracker_embed(_get(f"/api/trackers/embed/{CODE}"), make_env(db=MockDB([stmt])), CODE)
        assert _parse(r)["data"]["percentage"] == 100

    async def test_route_is_wired_in_the_dispatcher(self):
        stmt = make_stmt(first=_public_row())
        r = await worker._dispatch(_get(f"/api/trackers/embed/{CODE}"), make_env(db=MockDB([stmt])))
        assert r.status == 200
        assert _parse(r)["data"]["title"] == "Read books"

    async def test_embed_route_does_not_shadow_the_owner_routes(self):
        # "/api/trackers/<id>" still needs a login
        r = await worker._dispatch(_get("/api/trackers/t-1"), make_env())
        assert r.status == 401


class TestEmbedCodeFormat:
    def test_generated_codes_are_accepted_by_the_embed_endpoint(self):
        # api_create_tracker uses new_id() for embed_code; if its format ever
        # changes, every embed link would silently 404.
        for _ in range(500):
            assert worker._EMBED_CODE_RE.fullmatch(worker.new_id())


class TestEmbedPage:
    def test_route_maps_to_the_embed_page(self):
        assert worker.STATIC_CLEAN_ROUTES["/trackers/embed"] == "/tracker-embed.html"

    async def test_embed_page_can_be_framed(self):
        env = make_env()
        set_static_content(env, "<html>embed</html>")
        r = await worker._dispatch(_get("/trackers/embed?code=" + CODE), env)
        assert r.status == 200
        assert "X-Frame-Options" not in r.headers
        # the other protections stay on
        assert r.headers["X-Content-Type-Options"] == "nosniff"

    async def test_other_pages_still_refuse_framing(self):
        env = make_env()
        set_static_content(env, "<html>page</html>")
        for path in ("/trackers", "/surveys", "/about"):
            r = await worker._dispatch(_get(path), env)
            assert r.headers.get("X-Frame-Options") == "DENY", path

    def test_page_reads_the_public_endpoint(self):
        html = (PUBLIC_DIR / "tracker-embed.html").read_text(encoding="utf-8")
        assert "/api/trackers/embed/" in html
        assert "encodeURIComponent(code)" in html

    def test_page_never_writes_api_text_as_html(self):
        html = (PUBLIC_DIR / "tracker-embed.html").read_text(encoding="utf-8")
        assert "innerHTML" not in html
        assert "document.write" not in html

    def test_page_has_no_template_tags(self):
        # The server renders {{ }} and {% %} in html files; this page has none.
        html = (PUBLIC_DIR / "tracker-embed.html").read_text(encoding="utf-8")
        assert not re.search(r"\{%|\{\{", html)

    def test_page_colors_match_the_api(self):
        html = (PUBLIC_DIR / "tracker-embed.html").read_text(encoding="utf-8")
        block = re.search(r"var COLORS = \{(.*?)\};", html, re.S).group(1)
        assert set(re.findall(r"'((?:blue|green|yellow|red|gray)-600)':", block)) == worker._TRACKER_COLORS


class TestEmbedSnippetOnDetailPage:
    def test_snippet_only_for_public_trackers(self):
        html = (PUBLIC_DIR / "trackers.html").read_text(encoding="utf-8")
        assert "t.is_public && t.embed_code" in html
        assert "/trackers/embed?code=" in html
        assert "encodeURIComponent(t.embed_code)" in html
