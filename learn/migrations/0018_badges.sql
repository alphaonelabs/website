-- Migration 0018: Badges and earned badges
-- Ported from the Django site (web.Badge, web.UserBadge). Badges tied to a challenge are
-- awarded automatically when a user submits that challenge.

CREATE TABLE IF NOT EXISTS badges (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL,
    badge_type  TEXT NOT NULL DEFAULT 'challenge'
                CHECK (badge_type IN ('challenge', 'course', 'achievement', 'teacher_awarded')),
    challenge_id TEXT,
    icon        TEXT NOT NULL DEFAULT 'medal',
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_by  TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (challenge_id) REFERENCES challenges(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_badges_challenge ON badges(challenge_id);

CREATE TABLE IF NOT EXISTS user_badges (
    id                      TEXT PRIMARY KEY,
    user_id                 TEXT NOT NULL,
    badge_id                TEXT NOT NULL,
    award_method            TEXT NOT NULL
                            CHECK (award_method IN ('challenge_completion', 'course_completion', 'teacher_awarded', 'system_awarded')),
    challenge_submission_id TEXT,
    awarded_at              TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (user_id, badge_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (badge_id) REFERENCES badges(id) ON DELETE CASCADE,
    FOREIGN KEY (challenge_submission_id) REFERENCES challenge_submissions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_user_badges_user ON user_badges(user_id, awarded_at);
