-- Migration 0015: Implement complete quiz data model and authoring API
-- Quizzes and Quiz Questions for activities

CREATE TABLE IF NOT EXISTS quizzes (
    id                 TEXT PRIMARY KEY,
    activity_id        TEXT NOT NULL,
    title              TEXT NOT NULL,
    description        TEXT,
    time_limit_minutes INTEGER DEFAULT 0,
    passing_score      INTEGER DEFAULT 70,
    created_at         TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at         TEXT,
    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_quizzes_activity ON quizzes(activity_id);

CREATE TABLE IF NOT EXISTS quiz_questions (
    id                       TEXT PRIMARY KEY,
    quiz_id                  TEXT NOT NULL,
    prompt                   TEXT NOT NULL,
    question_type            TEXT NOT NULL DEFAULT 'multiple_choice',
    options_json             TEXT,
    correct_answer_encrypted TEXT,
    display_order            INTEGER NOT NULL DEFAULT 0,
    created_at               TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_quiz_questions_quiz ON quiz_questions(quiz_id);
