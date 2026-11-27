-- Migration 0016: Add oauth_identities table for Google and external OAuth sign-in

CREATE TABLE IF NOT EXISTS oauth_identities (
    id                TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL,
    provider          TEXT NOT NULL,
    provider_user_id  TEXT NOT NULL,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (provider, provider_user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_oauth_identities_user_id ON oauth_identities(user_id);
