-- Migration 0004: Legacy Django migration support.

ALTER TABLE users ADD COLUMN legacy_user_id TEXT;
ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1;
ALTER TABLE users ADD COLUMN is_staff INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN last_login TEXT;

ALTER TABLE activities ADD COLUMN legacy_course_id TEXT;
ALTER TABLE activities ADD COLUMN slug TEXT;
ALTER TABLE activities ADD COLUMN image_url TEXT;
ALTER TABLE activities ADD COLUMN image_r2_key TEXT;
ALTER TABLE activities ADD COLUMN learning_objectives TEXT;
ALTER TABLE activities ADD COLUMN prerequisites TEXT;
ALTER TABLE activities ADD COLUMN price_cents INTEGER;
ALTER TABLE activities ADD COLUMN price_currency TEXT NOT NULL DEFAULT 'USD';
ALTER TABLE activities ADD COLUMN max_students INTEGER;
ALTER TABLE activities ADD COLUMN invite_only INTEGER NOT NULL DEFAULT 0;
ALTER TABLE activities ADD COLUMN allow_individual_sessions INTEGER NOT NULL DEFAULT 0;
ALTER TABLE activities ADD COLUMN status TEXT NOT NULL DEFAULT 'published';
ALTER TABLE activities ADD COLUMN subject_id TEXT;
ALTER TABLE activities ADD COLUMN level TEXT;
ALTER TABLE activities ADD COLUMN is_featured INTEGER NOT NULL DEFAULT 0;
ALTER TABLE activities ADD COLUMN legacy_metadata TEXT;

ALTER TABLE sessions ADD COLUMN legacy_session_id TEXT;
ALTER TABLE sessions ADD COLUMN legacy_metadata TEXT;

ALTER TABLE enrollments ADD COLUMN legacy_enrollment_id TEXT;
ALTER TABLE enrollments ADD COLUMN completion_date TEXT;
ALTER TABLE enrollments ADD COLUMN legacy_metadata TEXT;

ALTER TABLE session_attendance ADD COLUMN legacy_attendance_id TEXT;
ALTER TABLE session_attendance ADD COLUMN notes TEXT;
ALTER TABLE session_attendance ADD COLUMN legacy_metadata TEXT;
ALTER TABLE session_attendance ADD COLUMN updated_at TEXT;

ALTER TABLE notifications ADD COLUMN legacy_notification_id TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_legacy_user_id ON users(legacy_user_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_activities_legacy_course_id ON activities(legacy_course_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_activities_slug ON activities(slug);
CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_legacy_session_id ON sessions(legacy_session_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_enrollments_legacy_enrollment_id ON enrollments(legacy_enrollment_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_session_attendance_legacy_attendance_id ON session_attendance(legacy_attendance_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_notifications_legacy_notification_id ON notifications(legacy_notification_id);

CREATE TABLE IF NOT EXISTS subjects (
    id                TEXT PRIMARY KEY,
    legacy_subject_id TEXT UNIQUE,
    name              TEXT NOT NULL,
    slug              TEXT UNIQUE,
    description       TEXT,
    icon              TEXT,
    display_order     INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT
);

CREATE TABLE IF NOT EXISTS user_profiles (
    user_id                  TEXT PRIMARY KEY,
    legacy_profile_id         TEXT UNIQUE,
    bio                       TEXT,
    expertise                 TEXT,
    avatar_url                TEXT,
    avatar_r2_key             TEXT,
    discord_username          TEXT,
    slack_username            TEXT,
    github_username           TEXT,
    referral_code             TEXT,
    referred_by_user_id       TEXT,
    referral_earnings_cents   INTEGER,
    stripe_account_id         TEXT,
    stripe_account_status     TEXT,
    commission_rate           TEXT,
    is_teacher                INTEGER NOT NULL DEFAULT 0,
    is_social_media_manager   INTEGER NOT NULL DEFAULT 0,
    is_profile_public         INTEGER NOT NULL DEFAULT 0,
    how_did_you_hear_about_us TEXT,
    created_at                TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at                TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS activity_materials (
    id                  TEXT PRIMARY KEY,
    legacy_material_id  TEXT UNIQUE,
    activity_id          TEXT NOT NULL,
    session_id           TEXT,
    title                TEXT NOT NULL,
    description          TEXT,
    material_type        TEXT,
    file_url             TEXT,
    file_r2_key          TEXT,
    external_url         TEXT,
    display_order        INTEGER NOT NULL DEFAULT 0,
    is_downloadable      INTEGER NOT NULL DEFAULT 0,
    requires_enrollment  INTEGER NOT NULL DEFAULT 1,
    due_date             TEXT,
    created_at           TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at           TEXT,
    legacy_metadata      TEXT,
    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id)  REFERENCES sessions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_activity_materials_activity ON activity_materials(activity_id);
CREATE INDEX IF NOT EXISTS idx_activity_materials_session ON activity_materials(session_id);

CREATE TABLE IF NOT EXISTS legacy_records (
    id           TEXT PRIMARY KEY,
    legacy_model TEXT NOT NULL,
    legacy_pk    TEXT NOT NULL,
    user_id      TEXT,
    activity_id  TEXT,
    payload      TEXT NOT NULL,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (legacy_model, legacy_pk)
);

CREATE INDEX IF NOT EXISTS idx_legacy_records_model ON legacy_records(legacy_model);
CREATE INDEX IF NOT EXISTS idx_legacy_records_user ON legacy_records(user_id);
CREATE INDEX IF NOT EXISTS idx_legacy_records_activity ON legacy_records(activity_id);

CREATE TABLE IF NOT EXISTS legacy_migration_runs (
    id          TEXT PRIMARY KEY,
    source_host TEXT,
    started_at  TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT,
    stats       TEXT,
    notes       TEXT
);
