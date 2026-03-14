"""
EarthMind — Main Cloudflare Python Worker Entry Point

Handles all HTTP routing for the environmental monitoring platform.
"""

import json
from urllib.parse import urlparse, parse_qs

from workers import WorkerEntrypoint, Response

from services.anomaly import detect_anomalies
from services.trends import analyze_trends
from services.ai_service import (
    analyze_trends_with_ai,
    assess_ecological_risk,
    explain_anomaly,
    generate_dashboard_summary,
)


# ---------------------------------------------------------------------------
# CORS / JSON helpers
# ---------------------------------------------------------------------------

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
}


def _json_response(data, status: int = 200) -> Response:
    return Response(
        json.dumps(data, default=str),
        headers={**_CORS_HEADERS, "Content-Type": "application/json"},
        status=status,
    )


def _error(message: str, status: int = 400) -> Response:
    return _json_response({"error": message}, status)


# ---------------------------------------------------------------------------
# Worker entry point
# ---------------------------------------------------------------------------

class EarthMind(WorkerEntrypoint):
    async def fetch(self, request):
        parsed = urlparse(request.url)
        path = parsed.path.rstrip("/") or "/"
        method = request.method.upper()

        # Preflight
        if method == "OPTIONS":
            return Response("", headers=_CORS_HEADERS, status=204)

        # Dashboard
        if path == "/":
            return _serve_dashboard()

        # Health check
        if path == "/api/health":
            return _json_response({"status": "ok", "service": "earthmind"})

        # Data ingestion / retrieval
        if path == "/api/data":
            if method == "POST":
                return await _ingest_reading(request, self.env)
            return await _query_readings(request, self.env, parsed)

        # Anomaly detection
        if path == "/api/anomalies":
            return await _get_anomalies(request, self.env, parsed)

        # Trend analysis
        if path == "/api/trends":
            return await _get_trends(request, self.env, parsed)

        # Alerts
        if path == "/api/alerts":
            if method == "POST":
                return await _create_alert(request, self.env)
            return await _list_alerts(self.env, parsed)

        if path.startswith("/api/alerts/") and path.endswith("/resolve"):
            alert_id = path.split("/")[3]
            return await _resolve_alert(self.env, alert_id)

        # AI-powered analysis
        if path == "/api/analytics/trends":
            return await _analytics_trends(request, self.env, parsed)

        if path == "/api/analytics/risk":
            return await _analytics_risk(request, self.env, parsed)

        if path == "/api/analytics/anomaly-explain":
            return await _analytics_explain_anomaly(request, self.env, parsed)

        if path == "/api/analytics/summary":
            return await _analytics_summary(request, self.env, parsed)

        # Geospatial GeoJSON endpoint
        if path == "/api/geo":
            return await _get_geojson(self.env, parsed)

        return _error("Not found", 404)


# ---------------------------------------------------------------------------
# Environmental data handlers
# ---------------------------------------------------------------------------

async def _ingest_reading(request, env) -> Response:
    try:
        body = await request.json()
    except Exception:
        return _error("Invalid JSON body")

    required = ("source", "source_type", "parameter", "value", "timestamp")
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _error(f"Missing required fields: {', '.join(missing)}")

    try:
        float(body["value"])
    except (TypeError, ValueError):
        return _error("'value' must be a number")

    stmt = env.DB.prepare(
        "INSERT INTO readings "
        "(source, source_type, location, latitude, longitude, parameter, value, unit, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
    ).bind(
        body["source"],
        body["source_type"],
        body.get("location"),
        body.get("latitude"),
        body.get("longitude"),
        body["parameter"],
        float(body["value"]),
        body.get("unit"),
        body["timestamp"],
    )
    result = await stmt.run()
    reading_id = result.meta.last_row_id if hasattr(result, "meta") else None

    # Auto-check thresholds and create alert if exceeded
    threshold = _get_threshold(body["parameter"])
    if threshold is not None and float(body["value"]) > threshold:
        await _auto_create_threshold_alert(env, body, threshold)

    return _json_response({"id": reading_id, "status": "created"}, 201)


async def _query_readings(request, env, parsed) -> Response:
    params = parse_qs(parsed.query)
    parameter = _first(params, "parameter")
    source = _first(params, "source")
    location = _first(params, "location")
    limit = min(int(_first(params, "limit") or 100), 1000)
    since = _first(params, "since")

    conditions = []
    bindings = []

    if parameter:
        conditions.append("parameter = ?")
        bindings.append(parameter)
    if source:
        conditions.append("source = ?")
        bindings.append(source)
    if location:
        conditions.append("location = ?")
        bindings.append(location)
    if since:
        conditions.append("timestamp >= ?")
        bindings.append(since)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"SELECT * FROM readings {where} ORDER BY timestamp DESC LIMIT ?"
    bindings.append(limit)

    stmt = env.DB.prepare(sql).bind(*bindings)
    result = await stmt.all()
    rows = _rows_to_list(result)
    return _json_response({"data": rows, "count": len(rows)})


# ---------------------------------------------------------------------------
# Anomaly detection handler
# ---------------------------------------------------------------------------

async def _get_anomalies(request, env, parsed) -> Response:
    params = parse_qs(parsed.query)
    parameter = _first(params, "parameter")
    limit = min(int(_first(params, "limit") or 200), 1000)
    zscore_threshold = float(_first(params, "zscore_threshold") or 2.5)

    if not parameter:
        return _error("'parameter' query param is required")

    stmt = env.DB.prepare(
        "SELECT value, timestamp FROM readings WHERE parameter = ? "
        "ORDER BY timestamp ASC LIMIT ?"
    ).bind(parameter, limit)
    result = await stmt.all()
    rows = _rows_to_list(result)

    if len(rows) < 3:
        return _json_response({"anomalies": {}, "message": "Insufficient data"})

    values = [float(r["value"]) for r in rows]
    timestamps = [r["timestamp"] for r in rows]

    anomaly_report = detect_anomalies(
        values, timestamps, zscore_threshold=zscore_threshold
    )
    return _json_response({"parameter": parameter, "anomalies": anomaly_report})


# ---------------------------------------------------------------------------
# Trend analysis handler
# ---------------------------------------------------------------------------

async def _get_trends(request, env, parsed) -> Response:
    params = parse_qs(parsed.query)
    parameter = _first(params, "parameter")
    limit = min(int(_first(params, "limit") or 200), 1000)

    if not parameter:
        return _error("'parameter' query param is required")

    stmt = env.DB.prepare(
        "SELECT value, timestamp FROM readings WHERE parameter = ? "
        "ORDER BY timestamp ASC LIMIT ?"
    ).bind(parameter, limit)
    result = await stmt.all()
    rows = _rows_to_list(result)

    if not rows:
        return _json_response({"trend": {}, "message": "No data"})

    values = [float(r["value"]) for r in rows]
    timestamps = [r["timestamp"] for r in rows]

    trend = analyze_trends(values, timestamps)
    return _json_response({"parameter": parameter, "trend": trend})


# ---------------------------------------------------------------------------
# Alert handlers
# ---------------------------------------------------------------------------

async def _list_alerts(env, parsed) -> Response:
    params = parse_qs(parsed.query)
    active_only = _first(params, "active") != "false"
    severity = _first(params, "severity")

    conditions = []
    bindings = []

    if active_only:
        conditions.append("is_active = 1")
    if severity:
        conditions.append("severity = ?")
        bindings.append(severity)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"SELECT * FROM alerts {where} ORDER BY created_at DESC LIMIT 100"

    stmt = env.DB.prepare(sql).bind(*bindings) if bindings else env.DB.prepare(sql)
    result = await stmt.all()
    rows = _rows_to_list(result)
    return _json_response({"alerts": rows, "count": len(rows)})


async def _create_alert(request, env) -> Response:
    try:
        body = await request.json()
    except Exception:
        return _error("Invalid JSON body")

    required = ("type", "severity", "message")
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _error(f"Missing required fields: {', '.join(missing)}")

    if body["severity"] not in ("low", "medium", "high", "critical"):
        return _error("severity must be one of: low, medium, high, critical")

    stmt = env.DB.prepare(
        "INSERT INTO alerts "
        "(type, severity, message, location, latitude, longitude, parameter, "
        "threshold_value, actual_value) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
    ).bind(
        body["type"],
        body["severity"],
        body["message"],
        body.get("location"),
        body.get("latitude"),
        body.get("longitude"),
        body.get("parameter"),
        body.get("threshold_value"),
        body.get("actual_value"),
    )
    result = await stmt.run()
    alert_id = result.meta.last_row_id if hasattr(result, "meta") else None
    return _json_response({"id": alert_id, "status": "created"}, 201)


async def _resolve_alert(env, alert_id: str) -> Response:
    try:
        int(alert_id)
    except ValueError:
        return _error("Invalid alert id")

    stmt = env.DB.prepare(
        "UPDATE alerts SET is_active = 0, resolved_at = datetime('now') WHERE id = ?"
    ).bind(int(alert_id))
    await stmt.run()
    return _json_response({"id": int(alert_id), "status": "resolved"})


# ---------------------------------------------------------------------------
# AI analytics handlers
# ---------------------------------------------------------------------------

async def _analytics_trends(request, env, parsed) -> Response:
    params = parse_qs(parsed.query)
    parameter = _first(params, "parameter")

    if not parameter:
        return _error("'parameter' query param is required")

    stmt = env.DB.prepare(
        "SELECT value, timestamp FROM readings WHERE parameter = ? "
        "ORDER BY timestamp ASC LIMIT 200"
    ).bind(parameter)
    result = await stmt.all()
    rows = _rows_to_list(result)

    if not rows:
        return _json_response({"analysis": "No data available for this parameter."})

    values = [float(r["value"]) for r in rows]
    stats = analyze_trends(values)
    narrative = await analyze_trends_with_ai(env, parameter, stats)
    return _json_response({"parameter": parameter, "stats": stats, "analysis": narrative})


async def _analytics_risk(request, env, parsed) -> Response:
    stmt = env.DB.prepare(
        "SELECT parameter, value, unit, location FROM readings "
        "ORDER BY timestamp DESC LIMIT 50"
    )
    result = await stmt.all()
    readings = _rows_to_list(result)
    assessment = await assess_ecological_risk(env, readings)
    return _json_response({"risk_assessment": assessment})


async def _analytics_explain_anomaly(request, env, parsed) -> Response:
    params = parse_qs(parsed.query)
    parameter = _first(params, "parameter")

    if not parameter:
        return _error("'parameter' query param is required")

    stmt = env.DB.prepare(
        "SELECT value, timestamp FROM readings WHERE parameter = ? "
        "ORDER BY timestamp ASC LIMIT 100"
    ).bind(parameter)
    result = await stmt.all()
    rows = _rows_to_list(result)

    if len(rows) < 3:
        return _json_response({"explanation": "Insufficient data for anomaly detection."})

    values = [float(r["value"]) for r in rows]
    timestamps = [r["timestamp"] for r in rows]
    anomaly_report = detect_anomalies(values, timestamps)

    top_anomaly = None
    if anomaly_report["summary"]:
        top_anomaly = anomaly_report["summary"][0]
    elif anomaly_report["zscore"]:
        top_anomaly = anomaly_report["zscore"][0]

    if not top_anomaly:
        return _json_response({"explanation": "No anomalies detected."})

    explanation = await explain_anomaly(env, parameter, top_anomaly)
    return _json_response({
        "parameter": parameter,
        "anomaly": top_anomaly,
        "explanation": explanation,
    })


async def _analytics_summary(request, env, parsed) -> Response:
    stmt = env.DB.prepare(
        "SELECT DISTINCT parameter FROM readings ORDER BY parameter"
    )
    result = await stmt.all()
    parameters = [r["parameter"] for r in _rows_to_list(result)]

    stats_by_param = {}
    for param in parameters[:8]:  # limit to avoid slow responses
        stmt2 = env.DB.prepare(
            "SELECT value FROM readings WHERE parameter = ? "
            "ORDER BY timestamp ASC LIMIT 100"
        ).bind(param)
        res2 = await stmt2.all()
        vals = [float(r["value"]) for r in _rows_to_list(res2)]
        if vals:
            stats_by_param[param] = analyze_trends(vals)

    summary = await generate_dashboard_summary(env, stats_by_param)
    return _json_response({
        "summary": summary,
        "parameters_analysed": list(stats_by_param.keys()),
    })


# ---------------------------------------------------------------------------
# Geospatial GeoJSON endpoint
# ---------------------------------------------------------------------------

async def _get_geojson(env, parsed) -> Response:
    params = parse_qs(parsed.query)
    parameter = _first(params, "parameter")

    if parameter:
        stmt = env.DB.prepare(
            "SELECT source, location, latitude, longitude, parameter, value, unit, timestamp "
            "FROM readings WHERE parameter = ? AND latitude IS NOT NULL "
            "ORDER BY timestamp DESC LIMIT 500"
        ).bind(parameter)
    else:
        stmt = env.DB.prepare(
            "SELECT source, location, latitude, longitude, parameter, value, unit, timestamp "
            "FROM readings WHERE latitude IS NOT NULL "
            "ORDER BY timestamp DESC LIMIT 500"
        )

    result = await stmt.all()
    rows = _rows_to_list(result)

    features = []
    for row in rows:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [row["longitude"], row["latitude"]],
            },
            "properties": {
                "source": row["source"],
                "location": row["location"],
                "parameter": row["parameter"],
                "value": row["value"],
                "unit": row["unit"],
                "timestamp": row["timestamp"],
            },
        })

    geojson = {"type": "FeatureCollection", "features": features}
    return Response(
        json.dumps(geojson),
        headers={**_CORS_HEADERS, "Content-Type": "application/geo+json"},
    )


# ---------------------------------------------------------------------------
# Threshold configuration
# ---------------------------------------------------------------------------

_THRESHOLDS = {
    "pm2_5": 35.0,       # µg/m³ (WHO 24-hour guideline)
    "pm10": 50.0,        # µg/m³
    "co2": 1000.0,       # ppm (indoor concern level)
    "no2": 40.0,         # µg/m³ (WHO annual mean)
    "o3": 100.0,         # µg/m³
    "temperature": 40.0, # °C (extreme heat)
    "ph": 9.0,           # High pH in water bodies
    "noise_db": 85.0,    # dB (occupational exposure limit)
}


def _get_threshold(parameter: str):
    return _THRESHOLDS.get(parameter)


async def _auto_create_threshold_alert(env, reading: dict, threshold: float) -> None:
    severity = "high" if float(reading["value"]) > threshold * 1.5 else "medium"
    message = (
        f"{reading['parameter']} reading of {reading['value']} {reading.get('unit', '')} "
        f"exceeds threshold of {threshold} at {reading.get('location', 'unknown location')}"
    )
    stmt = env.DB.prepare(
        "INSERT INTO alerts "
        "(type, severity, message, location, latitude, longitude, parameter, "
        "threshold_value, actual_value) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
    ).bind(
        "threshold",
        severity,
        message,
        reading.get("location"),
        reading.get("latitude"),
        reading.get("longitude"),
        reading["parameter"],
        threshold,
        float(reading["value"]),
    )
    await stmt.run()


# ---------------------------------------------------------------------------
# Dashboard HTML (served inline)
# ---------------------------------------------------------------------------

def _serve_dashboard() -> Response:
    from static.index import DASHBOARD_HTML
    return Response(
        DASHBOARD_HTML,
        headers={**_CORS_HEADERS, "Content-Type": "text/html; charset=utf-8"},
    )


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _first(params: dict, key: str):
    vals = params.get(key, [])
    return vals[0] if vals else None


def _rows_to_list(result) -> list[dict]:
    """Convert a D1 result object to a plain list of dicts."""
    try:
        if hasattr(result, "results"):
            raw = result.results
            if hasattr(raw, "to_py"):
                return raw.to_py()
            return list(raw) if raw else []
        return []
    except Exception:
        return []
