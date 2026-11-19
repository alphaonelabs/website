-- Create the credentials table
CREATE TABLE IF NOT EXISTS credentials (
    id                TEXT PRIMARY KEY,
    certificate_id    TEXT,   -- nullable: cleared on account deletion
    user_id           TEXT,   -- nullable: cleared on account deletion
    activity_id       TEXT NOT NULL,
    subject_id        TEXT NOT NULL,
    name_disclosed    INTEGER NOT NULL DEFAULT 0 CHECK (name_disclosed IN (0, 1)),
    credential_jws    TEXT NOT NULL,
    kid               TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'revoked')),
    status_list_index INTEGER,
    issued_at         TEXT NOT NULL,
    revoked_at        TEXT,
    revoked_reason    TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (certificate_id) REFERENCES certificates(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_credentials_active_user_activity
    ON credentials (user_id, activity_id)
    WHERE user_id IS NOT NULL AND status = 'active';