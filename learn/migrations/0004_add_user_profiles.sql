-- Migration 0004: Add user profile fields and avatars table

ALTER TABLE users ADD COLUMN bio TEXT;
ALTER TABLE users ADD COLUMN avatar_url TEXT;
ALTER TABLE users ADD COLUMN is_teacher INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN github_username TEXT;
ALTER TABLE users ADD COLUMN discord_username TEXT;
ALTER TABLE users ADD COLUMN slack_username TEXT;
ALTER TABLE users ADD COLUMN expertise TEXT;
ALTER TABLE users ADD COLUMN is_profile_public INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS avatars (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    avatar_url TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_avatars_user   ON avatars(user_id);
CREATE INDEX IF NOT EXISTS idx_users_public   ON users(is_profile_public);
