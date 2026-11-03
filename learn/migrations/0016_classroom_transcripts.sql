-- Migration 0016: Classroom Transcripts & Breakouts

CREATE TABLE IF NOT EXISTS classroom_transcripts (
    id             TEXT PRIMARY KEY,
    room_id        TEXT NOT NULL,
    session_id     TEXT,
    participant_id TEXT NOT NULL,
    display_name   TEXT NOT NULL,
    text           TEXT NOT NULL,
    timestamp      TEXT NOT NULL DEFAULT (datetime('now')),
    source         TEXT NOT NULL DEFAULT 'live'
);

CREATE INDEX IF NOT EXISTS idx_transcripts_room ON classroom_transcripts (room_id);
CREATE INDEX IF NOT EXISTS idx_transcripts_time ON classroom_transcripts (timestamp);

CREATE TABLE IF NOT EXISTS classroom_breakouts (
    id               TEXT PRIMARY KEY,
    parent_room_id   TEXT NOT NULL,
    breakout_room_id TEXT NOT NULL,
    title            TEXT NOT NULL,
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_breakouts_parent ON classroom_breakouts (parent_room_id);
