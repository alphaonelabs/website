PRAGMA foreign_keys=off;

CREATE TABLE activity_carts_new (
    id         TEXT PRIMARY KEY,
    user_id    TEXT,
    guest_id   TEXT NOT NULL DEFAULT '',
    owner_kind TEXT NOT NULL DEFAULT 'user',
    status     TEXT NOT NULL DEFAULT 'open',
    currency   TEXT NOT NULL DEFAULT 'USD',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

INSERT INTO activity_carts_new (id,user_id,guest_id,owner_kind,status,currency,created_at,updated_at)
SELECT id,user_id,'','user',status,currency,created_at,updated_at
FROM activity_carts;

DROP TABLE activity_carts;
ALTER TABLE activity_carts_new RENAME TO activity_carts;

CREATE INDEX idx_activity_carts_user_status ON activity_carts(user_id, status);
CREATE INDEX idx_activity_carts_guest_status ON activity_carts(guest_id, status);

CREATE TABLE activity_checkout_sessions_new (
    id                TEXT PRIMARY KEY,
    user_id           TEXT,
    guest_id          TEXT NOT NULL DEFAULT '',
    owner_kind        TEXT NOT NULL DEFAULT 'user',
    cart_id           TEXT NOT NULL,
    stripe_session_id TEXT NOT NULL UNIQUE,
    status            TEXT NOT NULL DEFAULT 'pending',
    amount_total      INTEGER NOT NULL DEFAULT 0,
    currency          TEXT NOT NULL DEFAULT 'USD',
    guest_email       TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at      TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (cart_id) REFERENCES activity_carts(id) ON DELETE CASCADE
);

INSERT INTO activity_checkout_sessions_new
    (id,user_id,guest_id,owner_kind,cart_id,stripe_session_id,status,amount_total,currency,guest_email,created_at,completed_at)
SELECT
    id,user_id,'','user',cart_id,stripe_session_id,status,amount_total,currency,NULL,created_at,completed_at
FROM activity_checkout_sessions;

DROP TABLE activity_checkout_sessions;
ALTER TABLE activity_checkout_sessions_new RENAME TO activity_checkout_sessions;

CREATE INDEX idx_activity_checkout_sessions_user ON activity_checkout_sessions(user_id);
CREATE INDEX idx_activity_checkout_sessions_guest ON activity_checkout_sessions(guest_id);
CREATE INDEX idx_activity_checkout_sessions_cart ON activity_checkout_sessions(cart_id);

PRAGMA foreign_keys=on;
