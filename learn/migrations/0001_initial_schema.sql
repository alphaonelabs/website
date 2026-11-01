-- Migration 0001: Initial schema

CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    username_hash TEXT NOT NULL UNIQUE,
    email_hash    TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    username      TEXT NOT NULL,
    email         TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS activities (
    id            TEXT PRIMARY KEY,
    title         TEXT NOT NULL,
    description   TEXT,
    type          TEXT NOT NULL DEFAULT 'course',
    format        TEXT NOT NULL DEFAULT 'self_paced',
    schedule_type TEXT NOT NULL DEFAULT 'ongoing',
    host_id       TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (host_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    activity_id TEXT NOT NULL,
    title       TEXT,
    description TEXT,
    start_time  TEXT,
    end_time    TEXT,
    location    TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (activity_id) REFERENCES activities(id)
);

CREATE TABLE IF NOT EXISTS enrollments (
    id          TEXT PRIMARY KEY,
    activity_id TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'participant',
    status      TEXT NOT NULL DEFAULT 'active',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (activity_id, user_id),
    FOREIGN KEY (activity_id) REFERENCES activities(id),
    FOREIGN KEY (user_id)     REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS session_attendance (
    id         TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id    TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'registered',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (session_id, user_id),
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (user_id)    REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS tags (
    id   TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS activity_tags (
    activity_id TEXT NOT NULL,
    tag_id      TEXT NOT NULL,
    PRIMARY KEY (activity_id, tag_id),
    FOREIGN KEY (activity_id) REFERENCES activities(id),
    FOREIGN KEY (tag_id)      REFERENCES tags(id)
);

CREATE INDEX IF NOT EXISTS idx_activities_host         ON activities(host_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_activity    ON enrollments(activity_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_user        ON enrollments(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_activity       ON sessions(activity_id);
CREATE INDEX IF NOT EXISTS idx_sa_session              ON session_attendance(session_id);
CREATE INDEX IF NOT EXISTS idx_sa_user                 ON session_attendance(user_id);
CREATE INDEX IF NOT EXISTS idx_at_activity             ON activity_tags(activity_id);