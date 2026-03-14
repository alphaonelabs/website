"""
QuantaLab — Interactive Virtual Laboratory
Main Cloudflare Python Worker entry point.

Routes:
  GET  /                          → serve main SPA (index.html via assets)
  GET  /api/experiments           → list all experiments (JSON)
  GET  /api/experiments/{domain}  → list experiments for a domain (JSON)
  POST /api/mentor                → ask the AI mentor (JSON)
  GET  /api/health                → health-check endpoint (JSON)
"""

import json

from js import Headers, Response

from experiments import get_all_experiments, get_experiment, list_domains
from ai_mentor import ask_mentor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _json_response(data, status: int = 200) -> Response:
    headers = Headers.new({"Content-Type": "application/json"}.items())
    return Response.new(json.dumps(data), status=status, headers=headers)


def _error(message: str, status: int = 400) -> Response:
    return _json_response({"error": message}, status=status)


def _cors_headers() -> dict:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

def handle_experiments_list(domain: str | None = None) -> Response:
    """Return the experiment catalogue (optionally filtered by domain)."""
    if domain:
        if domain not in list_domains():
            return _error(f"Unknown domain '{domain}'. Valid domains: {list_domains()}", 404)
        data = {"domain": domain, "experiments": get_all_experiments()[domain]}
    else:
        data = {"domains": list_domains(), "experiments": get_all_experiments()}
    return _json_response(data)


async def handle_mentor(request, env) -> Response:
    """Forward a student message to the AI mentor and return the reply."""
    try:
        body = await request.json()
    except Exception:
        return _error("Request body must be valid JSON.")

    user_message: str = (body.get("message") or "").strip()
    if not user_message:
        return _error("'message' field is required and must not be empty.")

    history: list[dict] = body.get("history") or []
    domain: str = body.get("domain") or ""
    experiment: str = body.get("experiment") or ""

    # Validate history format (best-effort)
    if not isinstance(history, list):
        history = []

    try:
        reply = await ask_mentor(env, user_message, history, domain, experiment)
    except Exception as exc:
        # Surface AI errors as a friendly message so the UI never breaks
        return _json_response(
            {
                "response": (
                    "I'm having trouble connecting to my knowledge base right now. "
                    "Please try again in a moment! 🔬"
                ),
                "error": str(exc),
            },
            status=200,  # keep 200 so the frontend still shows the message
        )

    return _json_response({"response": reply})


def handle_experiment_detail(domain: str, experiment_id: str) -> Response:
    """Return detailed information for a single experiment."""
    exp = get_experiment(domain, experiment_id)
    if exp is None:
        return _error(
            f"Experiment '{experiment_id}' not found in domain '{domain}'.", 404
        )
    return _json_response(exp)


def handle_health() -> Response:
    return _json_response({"status": "ok", "service": "quantalab"})


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def on_fetch(request, env):
    """Primary fetch handler — routes every incoming HTTP request."""
    method: str = request.method.upper()
    url: str = request.url

    # Strip query string for routing
    path = url.split("?")[0]
    # Normalise trailing slash
    if path.endswith("/") and len(path) > 1:
        path = path.rstrip("/")

    # Strip origin so we only match on the path component
    try:
        from js import URL as JsURL
        parsed = JsURL.new(url)
        path = parsed.pathname.rstrip("/") or "/"
    except Exception:
        # Fallback: strip origin manually
        for prefix in ("https://", "http://"):
            if url.startswith(prefix):
                rest = url[len(prefix):]
                slash_idx = rest.find("/")
                path = rest[slash_idx:] if slash_idx != -1 else "/"
                path = path.split("?")[0].rstrip("/") or "/"
                break

    # CORS pre-flight
    if method == "OPTIONS":
        headers = Headers.new(
            {**_cors_headers(), "Content-Length": "0"}.items()
        )
        return Response.new("", status=204, headers=headers)

    # ---- API routes --------------------------------------------------------
    if path == "/api/health":
        return handle_health()

    if path == "/api/experiments":
        return handle_experiments_list()

    # /api/experiments/{domain}
    if path.startswith("/api/experiments/"):
        parts = path.split("/")  # ['', 'api', 'experiments', domain, ...]
        domain = parts[3] if len(parts) > 3 else None
        experiment_id = parts[4] if len(parts) > 4 else None
        if experiment_id:
            return handle_experiment_detail(domain, experiment_id)
        return handle_experiments_list(domain)

    if path == "/api/mentor" and method == "POST":
        return await handle_mentor(request, env)

    # ---- Unknown API routes ------------------------------------------------
    if path.startswith("/api/"):
        return _error("API endpoint not found.", 404)

    # ---- All other paths: let the assets binding serve static files --------
    # (Cloudflare assets binding handles / → index.html automatically)
    return Response.new("Not Found", status=404)
