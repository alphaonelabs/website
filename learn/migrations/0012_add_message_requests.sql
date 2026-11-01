-- Migration: add message_requests table for privacy-first direct messaging

CREATE TABLE IF NOT EXISTS message_requests (
    id TEXT PRIMARY KEY,
    from_user_id TEXT NOT NULL,
    to_user_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    source TEXT NOT NULL DEFAULT 'email',
    activity_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (from_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (to_user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_message_requests_to_user ON message_requests(to_user_id, status);
CREATE INDEX IF NOT EXISTS idx_message_requests_from_user ON message_requests(from_user_id);
CREATE INDEX IF NOT EXISTS idx_message_requests_activity ON message_requests(activity_id);
