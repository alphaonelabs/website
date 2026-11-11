-- Migration: add allow_email_buddy_requests and allow nullable activity_id in peer_connections
ALTER TABLE user_profiles ADD COLUMN allow_email_buddy_requests INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS peer_connections_new (
    id            TEXT PRIMARY KEY,
    sender_id     TEXT NOT NULL,
    recipient_id  TEXT NOT NULL,
    activity_id   TEXT,
    status        TEXT NOT NULL DEFAULT 'pending',
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (sender_id, recipient_id),
    FOREIGN KEY (sender_id)    REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (recipient_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (activity_id)  REFERENCES activities(id) ON DELETE CASCADE
);

INSERT OR IGNORE INTO peer_connections_new (id, sender_id, recipient_id, activity_id, status, created_at, updated_at)
    SELECT id, sender_id, recipient_id, activity_id, status, created_at, updated_at FROM peer_connections;

DROP TABLE peer_connections;

ALTER TABLE peer_connections_new RENAME TO peer_connections;

CREATE INDEX IF NOT EXISTS idx_peer_conn_sender    ON peer_connections(sender_id, status);
CREATE INDEX IF NOT EXISTS idx_peer_conn_recipient ON peer_connections(recipient_id, status);
CREATE INDEX IF NOT EXISTS idx_peer_conn_activity  ON peer_connections(activity_id);
