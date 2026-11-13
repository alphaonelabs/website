"""
Device authentication and rate limiting for EarthMind sensor ingestion.
"""
import hashlib
import secrets
from datetime import datetime, timezone, timedelta

RATE_LIMIT_WINDOW_SECONDS = 60   # 1-minute sliding window
RATE_LIMIT_MAX_REQUESTS = 30     # max 30 readings per device per minute


def generate_api_key() -> tuple[str, str]:
    """Generate a new API key and return (raw_key, sha256_hash)."""
    raw = secrets.token_urlsafe(32)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


async def register_device(env, device_id: str, owner_name: str = "", location: str = "",
                           latitude: float = None, longitude: float = None) -> dict:
    """Register a new device and return its API key (shown only once)."""
    raw_key, key_hash = generate_api_key()
    await env.DB.prepare(
        "INSERT INTO device_keys (device_id, api_key_hash, owner_name, location, latitude, longitude) "
        "VALUES (?, ?, ?, ?, ?, ?)"
    ).bind(device_id, key_hash, owner_name, location, latitude, longitude).run()
    return {"device_id": device_id, "api_key": raw_key,
            "message": "Save this key — it will not be shown again."}


async def authenticate_device(env, device_id: str, api_key: str) -> bool:
    """Verify api_key matches stored hash for device_id. Returns True if valid and active."""
    result = await env.DB.prepare(
        "SELECT api_key_hash, is_active FROM device_keys WHERE device_id = ?"
    ).bind(device_id).first()
    if not result:
        return False
    row = result.to_py() if hasattr(result, "to_py") else result
    if not row.get("is_active"):
        return False
    provided_hash = hashlib.sha256(api_key.encode()).hexdigest()
    return secrets.compare_digest(provided_hash, row["api_key_hash"])


async def check_rate_limit(env, device_id: str) -> tuple[bool, dict]:
    """
    Check if device is within rate limit.
    Returns (allowed: bool, info: dict with count and window_start).
    Uses a fixed 60-second window stored in D1.
    """
    now = datetime.now(timezone.utc)
    window_start = now.replace(second=0, microsecond=0).isoformat()

    result = await env.DB.prepare(
        "SELECT window_start, request_count FROM device_rate_limits WHERE device_id = ?"
    ).bind(device_id).first()

    row = (result.to_py() if hasattr(result, "to_py") else result) if result else None

    if row is None or row["window_start"] < window_start:
        # New window
        await env.DB.prepare(
            "INSERT OR REPLACE INTO device_rate_limits (device_id, window_start, request_count) VALUES (?, ?, 1)"
        ).bind(device_id, window_start).run()
        return True, {"count": 1, "window_start": window_start, "limit": RATE_LIMIT_MAX_REQUESTS}

    count = row["request_count"]
    if count >= RATE_LIMIT_MAX_REQUESTS:
        return False, {"count": count, "window_start": row["window_start"], "limit": RATE_LIMIT_MAX_REQUESTS}

    await env.DB.prepare(
        "UPDATE device_rate_limits SET request_count = request_count + 1 WHERE device_id = ?"
    ).bind(device_id).run()
    return True, {"count": count + 1, "window_start": row["window_start"], "limit": RATE_LIMIT_MAX_REQUESTS}


async def update_device_last_seen(env, device_id: str):
    """Update the last_seen_at timestamp for a device after a successful reading."""
    now = datetime.now(timezone.utc).isoformat()
    await env.DB.prepare(
        "UPDATE device_keys SET last_seen_at = ? WHERE device_id = ?"
    ).bind(now, device_id).run()
