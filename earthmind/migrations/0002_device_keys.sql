-- Migration 0002: Per-device API keys and rate limiting

-- Per-device API keys for authenticated sensor ingestion
CREATE TABLE IF NOT EXISTS device_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL UNIQUE,
    api_key_hash TEXT NOT NULL,
    owner_name TEXT,
    location TEXT,
    latitude REAL,
    longitude REAL,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    last_seen_at TEXT
);

-- Per-device rate limit tracking
CREATE TABLE IF NOT EXISTS device_rate_limits (
    device_id TEXT PRIMARY KEY,
    window_start TEXT NOT NULL,
    request_count INTEGER DEFAULT 0
);
