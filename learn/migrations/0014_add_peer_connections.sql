-- Migration: add peer_connections table for study buddy network
-- Connection requests require shared activity enrollment (privacy-first).

CREATE TABLE IF NOT EXISTS peer_connections (
    id            TEXT PRIMARY KEY,
    sender_id     TEXT NOT NULL,
    recipient_id  TEXT NOT NULL,
    activity_id   TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending',
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (sender_id, recipient_id),
    FOREIGN KEY (sender_id)    REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (recipient_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (activity_id)  REFERENCES activities(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_peer_conn_sender    ON peer_connections(sender_id, status);
CREATE INDEX IF NOT EXISTS idx_peer_conn_recipient ON peer_connections(recipient_id, status);
CREATE INDEX IF NOT EXISTS idx_peer_conn_activity  ON peer_connections(activity_id);
