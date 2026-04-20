-- Education Platform Database Schema (Activities Model)
-- Run with: wrangler d1 execute education_db --file=schema.sql

-- USERS
-- ALL PII (username, email, name, role) is stored encrypted.
-- username_hash and email_hash are HMAC-SHA256 blind indexes used for O(1)
-- lookups so no plaintext ever needs to be stored in an indexed column.
CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    username_hash TEXT NOT NULL UNIQUE,   -- HMAC(username) for lookups
    email_hash    TEXT NOT NULL UNIQUE,   -- HMAC(email)    for lookups
    name          TEXT NOT NULL,          -- encrypt(display_name)
    username      TEXT NOT NULL,          -- encrypt(login_username)
    email         TEXT NOT NULL,          -- encrypt(email)
    password_hash TEXT NOT NULL,          -- PBKDF2-SHA256, per-user salt
    role          TEXT NOT NULL,          -- encrypt('host' | 'member')
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ACTIVITIES (courses, meetups, workshops, seminars, etc.)
-- description is encrypted at rest.
CREATE TABLE IF NOT EXISTS activities (
    id            TEXT PRIMARY KEY,
    title         TEXT NOT NULL,
    description   TEXT,                   -- encrypted
    type          TEXT NOT NULL DEFAULT 'course',      -- course | meetup | workshop | seminar | other
    format        TEXT NOT NULL DEFAULT 'self_paced',  -- live | self_paced | hybrid
    schedule_type TEXT NOT NULL DEFAULT 'ongoing',     -- one_time | multi_session | recurring | ongoing
    host_id       TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (host_id) REFERENCES users(id)
);

-- SESSIONS (optional scheduled instances of an activity)
-- description and location are encrypted at rest.
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    activity_id TEXT NOT NULL,
    title       TEXT,
    description TEXT,                     -- encrypted
    start_time  TEXT,
    end_time    TEXT,
    location    TEXT,                     -- encrypted
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (activity_id) REFERENCES activities(id)
);

-- ENROLLMENTS (people joining activities)
CREATE TABLE IF NOT EXISTS enrollments (
    id          TEXT PRIMARY KEY,
    activity_id TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'participant', -- participant | instructor | organizer
    status      TEXT NOT NULL DEFAULT 'active',     -- active | cancelled | completed
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (activity_id, user_id),
    FOREIGN KEY (activity_id) REFERENCES activities(id),
    FOREIGN KEY (user_id)     REFERENCES users(id)
);

-- SESSION ATTENDANCE (optional per-session tracking)
CREATE TABLE IF NOT EXISTS session_attendance (
    id         TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id    TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'registered', -- registered | attended | missed
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (session_id, user_id),
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (user_id)    REFERENCES users(id)
);

-- TAGS (flexible categorisation)
CREATE TABLE IF NOT EXISTS tags (
    id   TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

-- ACTIVITY TAGS (many-to-many)
CREATE TABLE IF NOT EXISTS activity_tags (
    activity_id TEXT NOT NULL,
    tag_id      TEXT NOT NULL,
    PRIMARY KEY (activity_id, tag_id),
    FOREIGN KEY (activity_id) REFERENCES activities(id),
    FOREIGN KEY (tag_id)      REFERENCES tags(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_activities_host      ON activities(host_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_activity ON enrollments(activity_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_user     ON enrollments(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_activity    ON sessions(activity_id);
CREATE INDEX IF NOT EXISTS idx_sa_session           ON session_attendance(session_id);
CREATE INDEX IF NOT EXISTS idx_sa_user              ON session_attendance(user_id);
CREATE INDEX IF NOT EXISTS idx_at_activity          ON activity_tags(activity_id);

-- NOTIFICATIONS
CREATE TABLE IF NOT EXISTS notifications (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    type       TEXT NOT NULL,
    title      TEXT NOT NULL,
    message    TEXT NOT NULL,
    is_read    INTEGER NOT NULL DEFAULT 0,
    related_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_notif_user   ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notif_unread ON notifications(user_id, is_read);
