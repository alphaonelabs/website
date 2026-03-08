"""
Syntharia — Creative AI Studio
Cloudflare Python Worker entry point.

Routes:
  GET  /                        → Serve the web UI
  POST /api/art/generate        → Generate an image from a text prompt
  POST /api/art/style-transfer  → Apply artistic style to an uploaded image
  POST /api/music/compose       → Compose music (ABC notation + chord progression)
  POST /api/poetry/generate     → Write a poem
  POST /api/refine              → Iteratively refine any previous output
"""

import json
from urllib.parse import urlparse

from workers import WorkerEntrypoint, Response

from handlers.art import handle_art_generate
from handlers.music import handle_music_compose
from handlers.poetry import handle_poetry_generate
from handlers.style_transfer import handle_style_transfer
from handlers.refine import handle_refine
from ui import get_html


class Default(WorkerEntrypoint):
    """Main Cloudflare Python Worker for Syntharia."""

    async def fetch(self, request):
        parsed = urlparse(request.url)
        path = parsed.path.rstrip("/") or "/"
        method = request.method.upper()

        # ── CORS pre-flight ──────────────────────────────────────────────
        if method == "OPTIONS":
            return _cors_preflight()

        # ── Static UI ────────────────────────────────────────────────────
        if path in ("/", "/index.html"):
            if method == "GET":
                return Response(
                    get_html(),
                    headers={"content-type": "text/html; charset=utf-8"},
                )
            return _json_error("Method not allowed", 405)

        # ── API routes (POST only) ────────────────────────────────────────
        if not path.startswith("/api/"):
            return _json_error("Not found", 404)

        if method != "POST":
            return _json_error("Method not allowed", 405)

        body = await _parse_body(request)
        if body is None:
            return _json_error("Request body must be valid JSON", 400)

        try:
            if path == "/api/art/generate":
                return await handle_art_generate(self.env, body)

            if path == "/api/art/style-transfer":
                return await handle_style_transfer(self.env, body)

            if path == "/api/music/compose":
                return await handle_music_compose(self.env, body)

            if path == "/api/poetry/generate":
                return await handle_poetry_generate(self.env, body)

            if path == "/api/refine":
                return await handle_refine(self.env, body)

        except Exception as exc:
            return _json_error(f"Internal error: {exc}", 500)

        return _json_error("Not found", 404)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _parse_body(request) -> dict | None:
    """Parse the request body as JSON; return None on failure."""
    try:
        text = await request.text()
        return json.loads(text) if text else {}
    except Exception:
        return None


def _json_error(message: str, status: int = 400) -> Response:
    return Response.json({"success": False, "error": message}, status=status)


def _cors_preflight() -> Response:
    return Response(
        "",
        status=204,
        headers={
            "access-control-allow-origin": "*",
            "access-control-allow-methods": "GET, POST, OPTIONS",
            "access-control-allow-headers": "content-type",
        },
    )
