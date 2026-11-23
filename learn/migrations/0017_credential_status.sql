CREATE TABLE IF NOT EXISTS status_list_slots (
    idx           INTEGER PRIMARY KEY AUTOINCREMENT,
    credential_id TEXT NOT NULL UNIQUE
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_credentials_status_index
    ON credentials (status_list_index)
    WHERE status_list_index IS NOT NULL;