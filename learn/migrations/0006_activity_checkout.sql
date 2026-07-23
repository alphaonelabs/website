-- Migration 0006: Stripe checkout sessions for activity carts.

CREATE TABLE IF NOT EXISTS activity_checkout_sessions (
    id                TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL,
    cart_id           TEXT NOT NULL,
    stripe_session_id TEXT NOT NULL UNIQUE,
    status            TEXT NOT NULL DEFAULT 'pending',
    amount_total      INTEGER NOT NULL DEFAULT 0,
    currency          TEXT NOT NULL DEFAULT 'USD',
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at      TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (cart_id) REFERENCES activity_carts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_activity_checkout_sessions_user ON activity_checkout_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_checkout_sessions_cart ON activity_checkout_sessions(cart_id);
