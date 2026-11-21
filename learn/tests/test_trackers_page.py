"""
Tests for the progress tracker pages (public/trackers.html).

The page is one static HTML file with inline JavaScript (the same pattern as
surveys.html), so these tests cover the route and guard the parts of the file
that would otherwise break silently: the API calls, the color list and the
escaping of user-supplied text.
"""

import re
from pathlib import Path

from tests.helpers import MockRequest, load_worker, make_env, set_static_content

worker = load_worker()

PAGE = Path(__file__).parent.parent / "public" / "trackers.html"


def _page() -> str:
    return PAGE.read_text(encoding="utf-8")


class TestTrackersRoute:
    def test_clean_route_maps_to_page(self):
        assert worker.STATIC_CLEAN_ROUTES["/trackers"] == "/trackers.html"

    async def test_trackers_route_is_served(self):
        env = make_env()
        set_static_content(env, "<html>trackers</html>")
        req = MockRequest(method="GET", url="http://localhost/trackers")
        r = await worker._dispatch(req, env)
        assert r.status == 200

    async def test_query_views_use_the_same_page(self):
        env = make_env()
        set_static_content(env, "<html>trackers</html>")
        for query in ("?id=abc123", "?create=1"):
            req = MockRequest(method="GET", url="http://localhost/trackers" + query)
            r = await worker._dispatch(req, env)
            assert r.status == 200


class TestTrackersPageFile:
    def test_page_extends_base_template(self):
        assert '{% extends "base.html" %}' in _page()

    def test_page_has_no_stray_template_tags(self):
        # The server renders {{ }} and {% %}; the inline script must not use them.
        html = _page()
        tags = re.findall(r"\{%.*?%\}|\{\{.*?\}\}", html)
        assert all(t.startswith("{% extends") or t.startswith("{% block") or t.startswith("{% endblock") for t in tags)

    def test_page_calls_every_tracker_endpoint(self):
        html = _page()
        assert "'/api/trackers'" in html
        assert "'/api/trackers/' + encodeURIComponent" in html
        assert "method: 'PATCH'" in html
        assert "method: 'DELETE'" in html
        assert "method: 'POST'" in html

    def test_page_colors_match_the_api(self):
        html = _page()
        block = re.search(r"const COLORS = \{(.*?)\n  \};", html, re.S).group(1)
        page_colors = set(re.findall(r"'((?:blue|green|yellow|red|gray)-600)':", block))
        assert page_colors == worker._TRACKER_COLORS

    def test_page_limits_match_the_api(self):
        assert f"const MAX_VALUE = {worker._TRACKER_MAX_VALUE};" in _page()

    def test_user_text_is_always_escaped(self):
        # Every use of the title or description either goes through esc() or is
        # only a truthiness check before an esc() call.
        html = _page()
        for field in ("t.title", "t.description"):
            for match in re.finditer(re.escape(field), html):
                before = html[max(0, match.start() - 4) : match.start()]
                after = html[match.end() : match.end() + 3]
                is_escaped = before.endswith("esc(")
                is_truthiness_check = before.endswith("(") and after.startswith(" ?")
                assert (
                    is_escaped or is_truthiness_check
                ), f"{field} used without esc() near: {html[match.start() - 40:match.end() + 10]!r}"

    def test_page_uses_the_login_token_not_a_hardcoded_one(self):
        html = _page()
        assert "localStorage.getItem('edu_token')" in html
        assert "Bearer " in html


class TestTrackersPageInputHandling:
    def test_number_inputs_are_read_with_valueAsNumber(self):
        # A number input accepts "1e3" as 1000, but parseInt("1e3", 10) is 1.
        html = _page()
        assert "input.valueAsNumber" in html
        assert "parseInt(valueInput.value" not in html
        assert "parseInt(document.getElementById('tracker-target')" not in html
        assert "parseInt(document.getElementById('tracker-current')" not in html

    def test_only_one_save_runs_at_a_time(self):
        # Controls are disabled while a PATCH is pending, so a late response
        # cannot redraw the page over newer progress.
        html = _page()
        assert "if (saving) return false;" in html
        assert "setBusy(true);" in html
        assert "setBusy(false);" in html

    def test_visibility_change_keeps_unsaved_progress(self):
        html = _page()
        assert "async function save(changes, okText, keepDraft)" in html
        assert "{ is_public: wanted }" in html
        assert "if (!saved) box.checked = !wanted;" in html
