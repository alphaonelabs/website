-- Migration 0018: Forum authoring (topics and replies written on the current site)
-- Legacy Django forum records stay in legacy_records and are shown as an
-- archive; these tables hold new discussions only.

CREATE TABLE IF NOT EXISTS forum_topics (
    id         TEXT PRIMARY KEY,
    author_id  TEXT NOT NULL,
    title      TEXT NOT NULL,
    body       TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT,
    FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_forum_topics_created ON forum_topics(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_forum_topics_author  ON forum_topics(author_id, created_at);

CREATE TABLE IF NOT EXISTS forum_replies (
    id         TEXT PRIMARY KEY,
    topic_id   TEXT NOT NULL,
    author_id  TEXT NOT NULL,
    body       TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT,
    FOREIGN KEY (topic_id)  REFERENCES forum_topics(id) ON DELETE CASCADE,
    FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_forum_replies_topic  ON forum_replies(topic_id, created_at);
CREATE INDEX IF NOT EXISTS idx_forum_replies_author ON forum_replies(author_id, created_at);
