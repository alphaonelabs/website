-- Migration 0016: progress trackers (ported from the Django site)

CREATE TABLE IF NOT EXISTS progress_trackers (
    id            TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL,
    title         TEXT NOT NULL,
    description   TEXT,
    current_value INTEGER NOT NULL DEFAULT 0 CHECK (current_value >= 0),
    target_value  INTEGER NOT NULL CHECK (target_value >= 1),
    color         TEXT NOT NULL DEFAULT 'blue-600',
    is_public     INTEGER NOT NULL DEFAULT 0,
    embed_code    TEXT NOT NULL UNIQUE,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_progress_trackers_user ON progress_trackers(user_id);
