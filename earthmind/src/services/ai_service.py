"""
EarthMind AI Analysis Service

Wraps Cloudflare Workers AI to generate ecological insights, risk assessments,
and trend narratives from environmental sensor data.
"""

import json


# Cloudflare Workers AI model identifiers
_CHAT_MODEL = "@cf/meta/llama-3.1-8b-instruct"

# System prompt shared by all analysis calls
_SYSTEM_PROMPT = (
    "You are EarthMind, an expert AI environmental scientist. "
    "Analyse the provided environmental data and respond concisely with "
    "actionable insights for researchers and community responders. "
    "Use clear language, avoid jargon where possible, and always note "
    "confidence levels. Keep responses under 300 words."
)


async def analyze_trends_with_ai(env, parameter: str, stats: dict) -> str:
    """
    Ask Cloudflare AI to narrate the trend statistics for a given parameter.

    Args:
        env:       Cloudflare Worker environment (provides env.AI binding)
        parameter: Environmental parameter name (e.g. 'pm2_5')
        stats:     Output from services.trends.analyze_trends()

    Returns:
        AI-generated narrative string.
    """
    user_msg = (
        f"Environmental parameter: {parameter}\n"
        f"Trend direction: {stats.get('linear', {}).get('direction', 'unknown')}\n"
        f"Trend strength: {stats.get('linear', {}).get('strength', 'unknown')}\n"
        f"R² = {stats.get('linear', {}).get('r_squared', 0):.2f}\n"
        f"Mean value: {stats.get('mean')}\n"
        f"Min / Max: {stats.get('min')} / {stats.get('max')}\n"
        f"Latest rate of change: {stats.get('roc')}%\n"
        f"Computed risk level: {stats.get('risk_level', 'unknown')}\n\n"
        "Please provide a 2–3 paragraph ecological trend analysis with "
        "potential causes and recommended actions."
    )
    return await _run_chat(env, user_msg)


async def assess_ecological_risk(env, readings: list[dict]) -> str:
    """
    Ask Cloudflare AI to assess the overall ecological risk from a set of readings.

    Args:
        env:      Cloudflare Worker environment
        readings: List of reading dicts (parameter, value, unit, location)

    Returns:
        AI-generated risk assessment string.
    """
    summary_lines = []
    for r in readings[:20]:  # cap prompt size
        summary_lines.append(
            f"- {r.get('parameter')}: {r.get('value')} {r.get('unit', '')} "
            f"at {r.get('location', 'unknown location')}"
        )
    summary = "\n".join(summary_lines) if summary_lines else "No readings provided."

    user_msg = (
        "Current environmental readings:\n"
        f"{summary}\n\n"
        "Based on these readings, please:\n"
        "1. Identify the most significant ecological risks.\n"
        "2. Rate overall risk as LOW, MEDIUM, HIGH, or CRITICAL.\n"
        "3. Suggest immediate actions for community responders."
    )
    return await _run_chat(env, user_msg)


async def explain_anomaly(env, parameter: str, anomaly: dict) -> str:
    """
    Ask Cloudflare AI to explain a detected anomaly in plain language.

    Args:
        env:       Cloudflare Worker environment
        parameter: Environmental parameter name
        anomaly:   Anomaly dict from services.anomaly.detect_anomalies()

    Returns:
        AI-generated anomaly explanation string.
    """
    user_msg = (
        f"An anomaly was detected in the '{parameter}' readings.\n"
        f"Detection method: {anomaly.get('method')}\n"
        f"Expected value: {anomaly.get('expected_value')}\n"
        f"Actual value: {anomaly.get('actual_value')}\n"
        f"Deviation: {anomaly.get('deviation')}\n"
        f"Severity: {anomaly.get('severity')}\n\n"
        "Please explain in 2–3 sentences what might have caused this anomaly "
        "and what environmental impact it could have."
    )
    return await _run_chat(env, user_msg)


async def generate_dashboard_summary(env, stats_by_parameter: dict) -> str:
    """
    Generate an executive summary for the dashboard from aggregated stats.

    Args:
        env:                  Cloudflare Worker environment
        stats_by_parameter:   Dict mapping parameter name → analyze_trends() result

    Returns:
        AI-generated summary string.
    """
    lines = []
    for param, stats in list(stats_by_parameter.items())[:6]:
        lines.append(
            f"- {param}: {stats.get('linear', {}).get('direction', 'stable')} trend, "
            f"risk={stats.get('risk_level', 'low')}, "
            f"mean={stats.get('mean')}"
        )
    overview = "\n".join(lines) if lines else "No data."

    user_msg = (
        "Environmental monitoring overview:\n"
        f"{overview}\n\n"
        "Write a 2–3 sentence executive summary of the current environmental "
        "health status suitable for a public dashboard, noting any urgent concerns."
    )
    return await _run_chat(env, user_msg)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

async def _run_chat(env, user_message: str) -> str:
    """Send a chat completion request to Cloudflare Workers AI."""
    try:
        result = await env.AI.run(
            _CHAT_MODEL,
            {
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": 400,
            },
        )
        # The result object is a JS proxy; extract the response text
        if hasattr(result, "response"):
            return str(result.response)
        # Fallback: try JSON deserialization
        if hasattr(result, "to_py"):
            data = result.to_py()
            if isinstance(data, dict):
                return data.get("response", str(data))
        return str(result)
    except Exception as exc:  # noqa: BLE001
        return f"AI analysis unavailable: {exc}"
