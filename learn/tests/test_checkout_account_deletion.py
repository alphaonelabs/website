
import sqlite3

import worker


def _database():
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        );

        CREATE TABLE enrollments (
            id TEXT PRIMARY KEY,
            activity_id TEXT,
            user_id TEXT,
            role TEXT,
            status TEXT
        );

        CREATE TABLE activity_checkout_sessions (
            stripe_session_id TEXT PRIMARY KEY,
            user_id TEXT,
            owner_kind TEXT,
            status TEXT,
            completed_at TEXT,
            amount_total INTEGER
        );

        INSERT INTO users VALUES ('u1', 'active-hash');

        INSERT INTO activity_checkout_sessions
        VALUES ('cs_test', 'u1', 'user', 'pending', NULL, NULL);
    """)
    return conn


def _checkout_enroll(conn):
    return conn.execute(
        worker._CHECKOUT_ENROLL_SQL,
        ("e1", "activity1", "u1", "participant", "active", "u1"),
    ).rowcount


def _mark_paid(conn):
    return conn.execute(
        worker._MARK_CHECKOUT_PAID_SQL,
        (1000, "cs_test", "u1", "u1"),
    ).rowcount


def test_checkout_cannot_enroll_or_mark_paid_after_account_deletion():
    conn = _database()

    try:
        conn.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            ("deleted:test", "u1"),
        )

        assert _checkout_enroll(conn) == 0
        assert _mark_paid(conn) == 0

        assert conn.execute(
            "SELECT COUNT(*) FROM enrollments WHERE user_id='u1'"
        ).fetchone()[0] == 0

        assert conn.execute(
            "SELECT status FROM activity_checkout_sessions"
            " WHERE stripe_session_id='cs_test'"
        ).fetchone()[0] == "pending"

    finally:
        conn.close()


def test_account_deletion_removes_enrollment_created_before_deletion():
    conn = _database()

    try:
        assert _checkout_enroll(conn) == 1

        with conn:
            conn.execute(
                worker._DELETE_ACCOUNT_ENROLLMENTS_SQL,
                ("u1",),
            )
            conn.execute(
                "UPDATE users SET password_hash=? WHERE id=?",
                ("deleted:test", "u1"),
            )

        assert conn.execute(
            "SELECT COUNT(*) FROM enrollments WHERE user_id='u1'"
        ).fetchone()[0] == 0

        assert _mark_paid(conn) == 0

    finally:
        conn.close()
