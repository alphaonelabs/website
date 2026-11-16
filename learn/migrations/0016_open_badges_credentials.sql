CREATE TABLE IF NOT EXISTS credentials (
    id                TEXT PRIMARY KEY,            -- unguessable token used in the public URL
    certificate_id    INTEGER,                     -- nullable: cleared on account deletion
    user_id           INTEGER,                     -- nullable: cleared on account deletion
    activity_id       INTEGER NOT NULL,
    subject_id        TEXT NOT NULL,               -- random urn:uuid, never the user id
    name_disclosed    INTEGER NOT NULL DEFAULT 0 CHECK (name_disclosed IN (0, 1)),
    credential_jws    TEXT NOT NULL,               -- the signed credential, never edited
    kid               TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'revoked')),
    status_list_index INTEGER,                     -- reserved for the Bitstring Status List PR
    issued_at         TEXT NOT NULL,
    revoked_at        TEXT,
    revoked_reason    TEXT
);

-- One active credential per learner per activity. Revoked ones don't count,
-- so "revoke and reissue" still works.
CREATE UNIQUE INDEX IF NOT EXISTS uq_credentials_active_user_activity
    ON credentials (user_id, activity_id)
    WHERE user_id IS NOT NULL AND status = 'active';

CREATE INDEX IF NOT EXISTS idx_credentials_user ON credentials (user_id);