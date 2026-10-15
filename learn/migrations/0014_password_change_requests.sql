CREATE TABLE IF NOT EXISTS password_change_requests (
    id                TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL,
    token_hash        TEXT NOT NULL UNIQUE,
    new_password_hash TEXT NOT NULL,
    expires_at        TEXT NOT NULL,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pcreq_user ON password_change_requests(user_id);