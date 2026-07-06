-- Migration 0007: Learn/teach intent requests.

CREATE TABLE IF NOT EXISTS learning_intents (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    kind        TEXT NOT NULL,
    title       TEXT NOT NULL,
    subject     TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'open',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_learning_intents_kind_status ON learning_intents(kind, status);
CREATE INDEX IF NOT EXISTS idx_learning_intents_user ON learning_intents(user_id);
