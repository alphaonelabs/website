-- Migration 0005: Activity checkout cart.

CREATE TABLE IF NOT EXISTS activity_carts (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'open',
    currency   TEXT NOT NULL DEFAULT 'USD',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_activity_carts_user_status ON activity_carts(user_id, status);

CREATE TABLE IF NOT EXISTS activity_cart_items (
    id               TEXT PRIMARY KEY,
    cart_id          TEXT NOT NULL,
    activity_id      TEXT NOT NULL,
    session_id       TEXT NOT NULL DEFAULT '',
    quantity         INTEGER NOT NULL DEFAULT 1,
    unit_price_cents INTEGER NOT NULL DEFAULT 0,
    title_snapshot   TEXT NOT NULL DEFAULT '',
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at       TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (cart_id, activity_id, session_id),
    FOREIGN KEY (cart_id)     REFERENCES activity_carts(id) ON DELETE CASCADE,
    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_activity_cart_items_cart ON activity_cart_items(cart_id);
CREATE INDEX IF NOT EXISTS idx_activity_cart_items_activity ON activity_cart_items(activity_id);
