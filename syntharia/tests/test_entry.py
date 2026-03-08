"""
Unit tests for the Syntharia worker entry point (``src/entry.py``).

Tests cover URL routing, CORS handling, and request body parsing.
"""

import json
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import AsyncMock, MagicMock, patch, call
from tests.conftest import MockRequest


# ---------------------------------------------------------------------------
# Helpers to build a worker instance with a mocked env
# ---------------------------------------------------------------------------

def make_worker(ai_return=None):
    """Create a Default worker instance with mocked env.AI.run."""
    from entry import Default

    worker = Default()
    worker.env = MagicMock()
    worker.env.AI = MagicMock()
    worker.env.AI.run = AsyncMock(return_value=ai_return or b"fakepng")
    return worker


# ===========================================================================
# UI route
# ===========================================================================

class TestUIRoute:
    @pytest.mark.asyncio
    async def test_root_returns_html(self):
        worker = make_worker()
        req = MockRequest("http://localhost/", "GET")
        resp = await worker.fetch(req)

        assert resp.status == 200
        html = resp.body.decode()
        assert "Syntharia" in html
        assert "<!DOCTYPE html>" in html

    @pytest.mark.asyncio
    async def test_index_html_alias_returns_html(self):
        worker = make_worker()
        req = MockRequest("http://localhost/index.html", "GET")
        resp = await worker.fetch(req)

        assert resp.status == 200
        assert b"Syntharia" in resp.body

    @pytest.mark.asyncio
    async def test_unknown_path_returns_404(self):
        worker = make_worker()
        req = MockRequest("http://localhost/does-not-exist", "GET")
        resp = await worker.fetch(req)

        data = json.loads(resp.body)
        assert resp.status == 404
        assert data["success"] is False


# ===========================================================================
# CORS pre-flight
# ===========================================================================

class TestCORS:
    @pytest.mark.asyncio
    async def test_options_returns_204(self):
        worker = make_worker()
        req = MockRequest("http://localhost/api/art/generate", "OPTIONS")
        resp = await worker.fetch(req)

        assert resp.status == 204
        assert "access-control-allow-methods" in resp.headers

    @pytest.mark.asyncio
    async def test_options_allows_post(self):
        worker = make_worker()
        req = MockRequest("http://localhost/api/poetry/generate", "OPTIONS")
        resp = await worker.fetch(req)

        assert "POST" in resp.headers.get("access-control-allow-methods", "")


# ===========================================================================
# Method validation
# ===========================================================================

class TestMethodValidation:
    @pytest.mark.asyncio
    async def test_get_on_api_returns_405(self):
        worker = make_worker()
        req = MockRequest("http://localhost/api/art/generate", "GET")
        resp = await worker.fetch(req)

        data = json.loads(resp.body)
        assert resp.status == 405
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_put_on_api_returns_405(self):
        worker = make_worker()
        req = MockRequest("http://localhost/api/poetry/generate", "PUT")
        resp = await worker.fetch(req)

        assert resp.status == 405


# ===========================================================================
# Request body parsing
# ===========================================================================

class TestBodyParsing:
    @pytest.mark.asyncio
    async def test_invalid_json_returns_400(self):
        worker = make_worker()
        req = MockRequest(
            "http://localhost/api/poetry/generate",
            "POST",
            body=b"this is not json",
        )
        resp = await worker.fetch(req)

        data = json.loads(resp.body)
        assert resp.status == 400
        assert "JSON" in data["error"]

    @pytest.mark.asyncio
    async def test_empty_body_treated_as_empty_dict(self):
        worker = make_worker()
        req = MockRequest("http://localhost/api/art/generate", "POST", body=b"")
        resp = await worker.fetch(req)

        # Handler should return 400 with "prompt is required"
        data = json.loads(resp.body)
        assert resp.status == 400
        assert "prompt" in data["error"]


# ===========================================================================
# Route delegation
# ===========================================================================

class TestRouteDelegation:
    @pytest.mark.asyncio
    async def test_art_generate_route(self):
        worker = make_worker(ai_return=b"\x89PNG fake")
        body = json.dumps({"prompt": "a mountain at sunrise"}).encode()
        req = MockRequest("http://localhost/api/art/generate", "POST", body=body)
        resp = await worker.fetch(req)

        assert resp.status == 200
        assert resp.headers.get("content-type") == "image/png"

    @pytest.mark.asyncio
    async def test_music_compose_route(self):
        import json as _json
        music_json = _json.dumps({
            "title": "Test",
            "abc_notation": "X:1\nT:Test\nK:C\nCDEF|",
            "chords": ["C", "G"],
            "tempo": 120,
            "time_signature": "4/4",
            "key": "C major",
            "style_notes": "Bright.",
        })
        worker = make_worker(ai_return={"response": music_json})
        body = json.dumps({"prompt": "upbeat jazz"}).encode()
        req = MockRequest("http://localhost/api/music/compose", "POST", body=body)
        resp = await worker.fetch(req)

        data = json.loads(resp.body)
        assert resp.status == 200
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_poetry_generate_route(self):
        import json as _json
        poem_json = _json.dumps({
            "title": "Test Poem",
            "poem": "Line one\nLine two",
            "form": "free",
            "notes": "Simple.",
        })
        worker = make_worker(ai_return={"response": poem_json})
        body = json.dumps({"prompt": "the ocean"}).encode()
        req = MockRequest("http://localhost/api/poetry/generate", "POST", body=body)
        resp = await worker.fetch(req)

        data = json.loads(resp.body)
        assert resp.status == 200
        assert data["success"] is True
        assert data["data"]["title"] == "Test Poem"
