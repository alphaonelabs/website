-- Migration 0017: Challenges, challenge submissions and points
-- Ported from the Django site (web.Challenge, web.ChallengeSubmission, web.Points).

CREATE TABLE IF NOT EXISTS challenges (
    id             TEXT PRIMARY KEY,
    title          TEXT NOT NULL,
    description    TEXT NOT NULL,
    challenge_type TEXT NOT NULL DEFAULT 'weekly' CHECK (challenge_type IN ('weekly', 'one_time')),
    week_number    INTEGER,
    start_date     TEXT NOT NULL,
    end_date       TEXT NOT NULL,
    points         INTEGER NOT NULL DEFAULT 10 CHECK (points >= 1),
    created_by     TEXT,
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_challenges_weekly_number
    ON challenges(week_number) WHERE challenge_type = 'weekly';
CREATE INDEX IF NOT EXISTS idx_challenges_dates ON challenges(start_date, end_date);

CREATE TABLE IF NOT EXISTS challenge_submissions (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    challenge_id    TEXT NOT NULL,
    submission_text TEXT NOT NULL,
    points_awarded  INTEGER NOT NULL DEFAULT 10 CHECK (points_awarded >= 0),
    submitted_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (user_id, challenge_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (challenge_id) REFERENCES challenges(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_challenge_submissions_challenge ON challenge_submissions(challenge_id);

CREATE TABLE IF NOT EXISTS user_points (
    id           TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL,
    challenge_id TEXT,
    amount       INTEGER NOT NULL CHECK (amount >= 0),
    reason       TEXT NOT NULL,
    point_type   TEXT NOT NULL DEFAULT 'regular' CHECK (point_type IN ('regular', 'streak', 'bonus')),
    awarded_at   TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (challenge_id) REFERENCES challenges(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_user_points_user ON user_points(user_id, awarded_at);
