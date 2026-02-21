-- D1 Database Schema for OSS Project Management

-- Issues table
CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY,
    number INTEGER NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    closed_at TEXT,
    html_url TEXT NOT NULL,
    repository TEXT NOT NULL,
    assignee TEXT,
    milestone TEXT,
    time_to_close INTEGER,
    UNIQUE(repository, number)
);

-- Labels table
CREATE TABLE IF NOT EXISTS labels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    color TEXT,
    FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_labels_issue_id ON labels(issue_id);

-- Assignees table (for multiple assignees support)
CREATE TABLE IF NOT EXISTS assignees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id INTEGER NOT NULL,
    username TEXT NOT NULL,
    FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_assignees_issue_id ON assignees(issue_id);

-- Metrics table
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository TEXT NOT NULL,
    metric_date TEXT NOT NULL,
    total_issues INTEGER DEFAULT 0,
    open_issues INTEGER DEFAULT 0,
    closed_issues INTEGER DEFAULT 0,
    avg_time_to_close REAL DEFAULT 0,
    issues_opened_today INTEGER DEFAULT 0,
    issues_closed_today INTEGER DEFAULT 0,
    UNIQUE(repository, metric_date)
);

-- Sync status table
CREATE TABLE IF NOT EXISTS sync_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository TEXT NOT NULL UNIQUE,
    last_sync TEXT NOT NULL,
    status TEXT NOT NULL,
    error_message TEXT
);

-- User sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    access_token TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_username ON sessions(username);
CREATE INDEX IF NOT EXISTS idx_issues_state ON issues(state);
CREATE INDEX IF NOT EXISTS idx_issues_repository ON issues(repository);
CREATE INDEX IF NOT EXISTS idx_metrics_repository ON metrics(repository);
