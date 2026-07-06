-- Migration 0010: Per-activity waiting room / interest tracking.

CREATE TABLE IF NOT EXISTS activity_interest (
    id          TEXT PRIMARY KEY,
    activity_id TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    message     TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'interested',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(activity_id, user_id),
    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_activity_interest_activity ON activity_interest(activity_id, status);
CREATE INDEX IF NOT EXISTS idx_activity_interest_user ON activity_interest(user_id);
