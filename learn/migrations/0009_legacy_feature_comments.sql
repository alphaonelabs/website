-- Migration 0009: Legacy feature comment implementation support.

CREATE TABLE IF NOT EXISTS activity_completions (
    id           TEXT PRIMARY KEY,
    activity_id  TEXT NOT NULL,
    user_id      TEXT NOT NULL,
    kind         TEXT NOT NULL DEFAULT 'completed',
    completed_at TEXT NOT NULL DEFAULT (datetime('now')),
    notes        TEXT NOT NULL DEFAULT '',
    UNIQUE(activity_id, user_id, kind),
    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_activity_completions_user ON activity_completions(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_completions_activity ON activity_completions(activity_id);

CREATE TABLE IF NOT EXISTS donation_checkout_sessions (
    id                TEXT PRIMARY KEY,
    user_id           TEXT,
    stripe_session_id TEXT NOT NULL UNIQUE,
    status            TEXT NOT NULL DEFAULT 'pending',
    amount_total      INTEGER NOT NULL DEFAULT 0,
    currency          TEXT NOT NULL DEFAULT 'USD',
    message           TEXT NOT NULL DEFAULT '',
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at      TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_donation_checkout_sessions_user ON donation_checkout_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_donation_checkout_sessions_stripe ON donation_checkout_sessions(stripe_session_id);
