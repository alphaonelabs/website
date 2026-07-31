-- Migration 0013: Add certificates table

CREATE TABLE IF NOT EXISTS certificates (
    id            TEXT PRIMARY KEY,
    enrollment_id TEXT NOT NULL UNIQUE,
    issued_at     TEXT NOT NULL DEFAULT (datetime('now')),
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (enrollment_id) REFERENCES enrollments(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_certificates_enrollment ON certificates(enrollment_id);
