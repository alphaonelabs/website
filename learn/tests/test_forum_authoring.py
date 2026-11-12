"""
Tests for forum authoring.

Covers:
- POST   /api/forum/topics               (auth, verified email, validation, rate limit)
- POST   /api/forum/topics/:id/replies   (auth, validation, unknown/archived topics, rate limit)
- DELETE /api/forum/topics/:id           (author, admin, other users)
- DELETE /api/forum/replies/:id          (author, admin, other users)
- Server-rendered /forum listing and /forum/topic/:id pages (escaping, archive labels)
- Dispatcher routing for the forum endpoints
"""

import json

from tests.helpers import (
    MockRequest,
    MockRow,
    load_worker,
    make_env,
    make_init_db_stmts,
    make_stmt,
    json_request,
    set_static_content,
)

worker = load_worker()

JWT_SECRET = "test-jwt-secret"
ENC_KEY = "test-encryption-key"

USER_ID = "11111111-1111-4111-8111-111111111111"
OTHER_ID = "22222222-2222-4222-8222-222222222222"
TOPIC_ID = "33333333-3333-4333-8333-333333333333"
REPLY_ID = "44444444-4444-4444-8444-444444444444"


def _parse(resp):
    """Decode a JSON response body."""
    return json.loads(resp.body)


def _auth(uid=USER_ID, role="member"):
    """Return an Authorization header carrying a signed token for *uid*."""
    return {"Authorization": "Bearer " + worker.create_token(uid, "alice", role, JWT_SECRET)}


class RecordingDB:
    """MockDB that also records each prepared SQL string, in order."""

    def __init__(self, stmts=None):
        """Queue *stmts* to be returned by successive prepare() calls."""
        self._stmts = list(stmts or [])
        self.calls = []
        self.batches = []

    async def batch(self, bound_stmts):
        """Record a D1 batch (one transaction) of bound statements."""
        self.batches.append(list(bound_stmts))

    def prepare(self, sql):
        """Record *sql* and return the next queued statement (or a no-op one)."""
        stmt = self._stmts[len(self.calls)] if len(self.calls) < len(self._stmts) else make_stmt()
        self.calls.append((sql, stmt))
        return stmt

    def sql(self, index):
        """Return the SQL text of the *index*-th prepared statement."""
        return self.calls[index][0]

    def binds(self, index):
        """Return the positional bind arguments of the *index*-th statement."""
        return self.calls[index][1].bind.call_args.args

    def ran(self, fragment):
        """Return True if a statement containing *fragment* was executed with .run()."""
        return any(fragment in sql and stmt.bind.return_value.run.await_count for sql, stmt in self.calls)

    def batched(self, fragment):
        """Return True if a statement containing *fragment* was executed inside a batch."""
        in_batch = {id(b) for group in self.batches for b in group}
        return any(fragment in sql and id(stmt.bind.return_value) in in_batch for sql, stmt in self.calls)


def _verified(flag=1):
    """Statement returning a users row with the given email_verified flag."""
    return make_stmt(first=MockRow(email_verified=flag))


def _inserted(ok=True):
    """Statement for the post-insert lookup: a row if the conditional insert wrote one."""
    return make_stmt(first=MockRow(id="inserted") if ok else None)


async def _role(role):
    """Statement returning a users row whose stored (encrypted) role is *role*."""
    return make_stmt(first=MockRow(role=await worker.encrypt_aes(role, ENC_KEY)))


def _topic_req(payload, headers=None):
    """Build a POST /api/forum/topics request."""
    return json_request("/api/forum/topics", payload, headers=headers)


VALID_TOPIC = {"title": "How do I start learning Python?", "body": "Looking for a first project."}


# ---------------------------------------------------------------------------
# Creating topics
# ---------------------------------------------------------------------------

class TestCreateTopic:
    """POST /api/forum/topics."""

    async def test_requires_auth(self):
        """A request without a token is rejected before touching the database."""
        db = RecordingDB()
        r = await worker.api_forum_create_topic(_topic_req(VALID_TOPIC), make_env(db=db))
        assert r.status == 401
        assert db.calls == []

    async def test_rejects_invalid_token(self):
        """A malformed token is rejected with 401."""
        r = await worker.api_forum_create_topic(
            _topic_req(VALID_TOPIC, {"Authorization": "Bearer not-a-token"}), make_env(db=RecordingDB())
        )
        assert r.status == 401

    async def test_rejects_token_for_missing_user(self):
        """A valid token for a user that no longer exists is rejected with 401."""
        db = RecordingDB([make_stmt(first=None)])
        r = await worker.api_forum_create_topic(_topic_req(VALID_TOPIC, _auth()), make_env(db=db))
        assert r.status == 401

    async def test_rejects_unverified_email(self):
        """Users whose email is not verified get 403 and nothing is inserted."""
        db = RecordingDB([_verified(0)])
        r = await worker.api_forum_create_topic(_topic_req(VALID_TOPIC, _auth()), make_env(db=db))
        assert r.status == 403
        assert _parse(r)["code"] == "email_not_verified"
        assert not db.ran("INSERT INTO forum_topics")

    async def test_creates_topic(self):
        """A verified user creates a topic and gets its id and URL back."""
        db = RecordingDB([_verified(), make_stmt(), _inserted()])
        r = await worker.api_forum_create_topic(_topic_req(VALID_TOPIC, _auth()), make_env(db=db))
        assert r.status == 201
        data = _parse(r)["data"]
        assert data["url"] == f"/forum/topic/{data['id']}"
        assert worker._is_forum_id(data["id"])
        assert "INSERT INTO forum_topics" in db.sql(1)
        assert db.binds(1)[:4] == (data["id"], USER_ID, VALID_TOPIC["title"], VALID_TOPIC["body"])
        assert db.binds(2) == (data["id"],)

    async def test_normalises_text(self):
        """Titles collapse whitespace; bodies use LF newlines and drop control characters."""
        db = RecordingDB([_verified(), make_stmt(), _inserted()])
        payload = {"title": "  Line\nbreaks   in\ttitle ", "body": "  first\r\nsecond\x00\x07  "}
        r = await worker.api_forum_create_topic(_topic_req(payload, _auth()), make_env(db=db))
        assert r.status == 201
        _, _, title, body = db.binds(1)[:4]
        assert title == "Line breaks in title"
        assert body == "first\nsecond"

    async def test_rejects_short_title(self):
        """Titles shorter than the minimum are rejected with 400."""
        r = await worker.api_forum_create_topic(
            _topic_req({"title": "Hi", "body": "x"}, _auth()), make_env(db=RecordingDB([_verified()]))
        )
        assert r.status == 400
        assert "at least" in _parse(r)["error"]

    async def test_rejects_long_title(self):
        """Titles longer than the maximum are rejected with 400."""
        payload = {"title": "x" * (worker.FORUM_TITLE_MAX + 1), "body": "x"}
        r = await worker.api_forum_create_topic(_topic_req(payload, _auth()), make_env(db=RecordingDB([_verified()])))
        assert r.status == 400

    async def test_rejects_empty_body(self):
        """A whitespace-only body is rejected with 400."""
        payload = {"title": "Valid title", "body": "   \n  "}
        r = await worker.api_forum_create_topic(_topic_req(payload, _auth()), make_env(db=RecordingDB([_verified()])))
        assert r.status == 400
        assert "body" in _parse(r)["error"].lower()

    async def test_rejects_long_body(self):
        """Bodies longer than the maximum are rejected with 400."""
        payload = {"title": "Valid title", "body": "x" * (worker.FORUM_TOPIC_BODY_MAX + 1)}
        r = await worker.api_forum_create_topic(_topic_req(payload, _auth()), make_env(db=RecordingDB([_verified()])))
        assert r.status == 400

    async def test_rejects_non_string_fields(self):
        """Non-string title and body values are treated as missing."""
        payload = {"title": ["not", "a", "string"], "body": {"x": 1}}
        r = await worker.api_forum_create_topic(_topic_req(payload, _auth()), make_env(db=RecordingDB([_verified()])))
        assert r.status == 400

    async def test_rejects_invalid_json(self):
        """A body that is not valid JSON is rejected with 400."""
        req = MockRequest(method="POST", url="http://localhost/api/forum/topics", headers=_auth(), body="{nope")
        r = await worker.api_forum_create_topic(req, make_env(db=RecordingDB([_verified()])))
        assert r.status == 400

    async def test_limit_check_and_insert_are_one_statement(self):
        """The per-user limit is enforced inside the INSERT so concurrent posts cannot both pass."""
        max_posts, window = worker.FORUM_TOPIC_RATE_LIMIT
        db = RecordingDB([_verified(), make_stmt(), _inserted()])
        await worker.api_forum_create_topic(_topic_req(VALID_TOPIC, _auth()), make_env(db=db))
        sql = db.sql(1)
        assert sql.startswith("INSERT INTO forum_topics") and "SELECT COUNT(*) FROM forum_topics" in sql
        assert db.binds(1)[4:] == (USER_ID, f"-{window} seconds", max_posts)

    async def test_rate_limited(self):
        """When the conditional insert writes nothing, the user gets 429 with Retry-After."""
        _, window = worker.FORUM_TOPIC_RATE_LIMIT
        db = RecordingDB([_verified(), make_stmt(), _inserted(False)])
        r = await worker.api_forum_create_topic(_topic_req(VALID_TOPIC, _auth()), make_env(db=db))
        assert r.status == 429
        assert r.headers["Retry-After"] == str(window)

    async def test_creates_tables_when_missing(self):
        """A missing forum table triggers init_db and the post still succeeds."""
        missing = make_stmt()
        missing.bind.return_value.run.side_effect = Exception("D1_ERROR: no such table: forum_topics")
        init_stmts = await make_init_db_stmts(worker)
        db = RecordingDB([_verified(), missing, *init_stmts, make_stmt(), _inserted()])
        r = await worker.api_forum_create_topic(_topic_req(VALID_TOPIC, _auth()), make_env(db=db))
        assert r.status == 201
        assert db.ran("INSERT INTO forum_topics")


# ---------------------------------------------------------------------------
# Replying
# ---------------------------------------------------------------------------

def _reply_req(topic_id, payload, headers=None):
    """Build a POST /api/forum/topics/:id/replies request."""
    return json_request(f"/api/forum/topics/{topic_id}/replies", payload, headers=headers)


class TestCreateReply:
    """POST /api/forum/topics/:id/replies."""

    async def test_requires_auth(self):
        """A request without a token is rejected with 401."""
        r = await worker.api_forum_create_reply(_reply_req(TOPIC_ID, {"body": "hi"}), make_env(db=RecordingDB()), TOPIC_ID)
        assert r.status == 401

    async def test_rejects_unverified_email(self):
        """Users whose email is not verified cannot reply."""
        r = await worker.api_forum_create_reply(
            _reply_req(TOPIC_ID, {"body": "hi"}, _auth()), make_env(db=RecordingDB([_verified(0)])), TOPIC_ID
        )
        assert r.status == 403

    async def test_creates_reply(self):
        """A verified user replies to an existing topic."""
        db = RecordingDB([_verified(), make_stmt(first=MockRow(id=TOPIC_ID)), make_stmt(), _inserted()])
        r = await worker.api_forum_create_reply(_reply_req(TOPIC_ID, {"body": "Try a small game."}, _auth()), make_env(db=db), TOPIC_ID)
        assert r.status == 201
        data = _parse(r)["data"]
        assert data["topic_id"] == TOPIC_ID
        assert "INSERT INTO forum_replies" in db.sql(2)
        assert db.binds(2)[:4] == (data["id"], TOPIC_ID, USER_ID, "Try a small game.")

    async def test_unknown_topic_returns_404(self):
        """Replying to a topic that does not exist returns 404 and inserts nothing."""
        db = RecordingDB([_verified(), make_stmt(first=None)])
        r = await worker.api_forum_create_reply(_reply_req(TOPIC_ID, {"body": "hi"}, _auth()), make_env(db=db), TOPIC_ID)
        assert r.status == 404
        assert not db.ran("INSERT INTO forum_replies")

    async def test_archived_legacy_topic_is_read_only(self):
        """Legacy topics (numeric ids) cannot be replied to."""
        db = RecordingDB([_verified()])
        r = await worker.api_forum_create_reply(_reply_req("42", {"body": "hi"}, _auth()), make_env(db=db), "42")
        assert r.status == 404
        assert len(db.calls) == 1  # only the verified-email lookup

    async def test_rejects_empty_and_long_bodies(self):
        """Empty, whitespace-only and over-long replies are rejected with 400."""
        for body in ("", "   ", "x" * (worker.FORUM_REPLY_BODY_MAX + 1)):
            r = await worker.api_forum_create_reply(
                _reply_req(TOPIC_ID, {"body": body}, _auth()), make_env(db=RecordingDB([_verified()])), TOPIC_ID
            )
            assert r.status == 400, body[:10]

    async def test_rate_limited(self):
        """Users at the reply limit get 429; the limit is checked inside the INSERT."""
        max_posts, window = worker.FORUM_REPLY_RATE_LIMIT
        db = RecordingDB([_verified(), make_stmt(first=MockRow(id=TOPIC_ID)), make_stmt(), _inserted(False)])
        r = await worker.api_forum_create_reply(_reply_req(TOPIC_ID, {"body": "hi"}, _auth()), make_env(db=db), TOPIC_ID)
        assert r.status == 429
        assert "SELECT COUNT(*) FROM forum_replies" in db.sql(2)
        assert db.binds(2)[4:] == (USER_ID, f"-{window} seconds", max_posts)


# ---------------------------------------------------------------------------
# Deleting
# ---------------------------------------------------------------------------

def _delete_req(path, headers=None):
    """Build a DELETE request for *path*."""
    return MockRequest(method="DELETE", url=f"http://localhost{path}", headers=headers or {})


class TestDeleteTopic:
    """DELETE /api/forum/topics/:id."""

    async def test_requires_auth(self):
        """A request without a token is rejected with 401."""
        r = await worker.api_forum_delete_topic(_delete_req(f"/api/forum/topics/{TOPIC_ID}"), make_env(db=RecordingDB()), TOPIC_ID)
        assert r.status == 401

    async def test_author_deletes_topic_and_replies(self):
        """The author deletes the topic and its replies in a single transaction."""
        db = RecordingDB([make_stmt(first=MockRow(author_id=USER_ID))])
        r = await worker.api_forum_delete_topic(_delete_req(f"/api/forum/topics/{TOPIC_ID}", _auth()), make_env(db=db), TOPIC_ID)
        assert r.status == 200
        assert len(db.batches) == 1 and len(db.batches[0]) == 2
        assert db.batched("DELETE FROM forum_replies WHERE topic_id=?")
        assert db.batched("DELETE FROM forum_topics WHERE id=?")

    async def test_admin_can_delete_any_topic(self):
        """An admin whose stored role is still admin can delete someone else's topic."""
        db = RecordingDB([make_stmt(first=MockRow(author_id=OTHER_ID)), await _role("admin")])
        r = await worker.api_forum_delete_topic(
            _delete_req(f"/api/forum/topics/{TOPIC_ID}", _auth(role="admin")), make_env(db=db), TOPIC_ID
        )
        assert r.status == 200
        assert "SELECT role FROM users" in db.sql(1)
        assert db.batched("DELETE FROM forum_topics WHERE id=?")

    async def test_stale_admin_token_is_rejected(self):
        """A token claiming admin is refused once the stored role is no longer admin."""
        db = RecordingDB([make_stmt(first=MockRow(author_id=OTHER_ID)), await _role("member")])
        r = await worker.api_forum_delete_topic(
            _delete_req(f"/api/forum/topics/{TOPIC_ID}", _auth(role="admin")), make_env(db=db), TOPIC_ID
        )
        assert r.status == 403
        assert db.batches == []

    async def test_admin_token_for_missing_account_is_rejected(self):
        """A token claiming admin for an account that no longer exists is refused."""
        db = RecordingDB([make_stmt(first=MockRow(author_id=OTHER_ID)), make_stmt(first=None)])
        r = await worker.api_forum_delete_topic(
            _delete_req(f"/api/forum/topics/{TOPIC_ID}", _auth(role="admin")), make_env(db=db), TOPIC_ID
        )
        assert r.status == 403

    async def test_other_user_cannot_delete(self):
        """A different member gets 403 and nothing is deleted."""
        db = RecordingDB([make_stmt(first=MockRow(author_id=OTHER_ID))])
        r = await worker.api_forum_delete_topic(_delete_req(f"/api/forum/topics/{TOPIC_ID}", _auth()), make_env(db=db), TOPIC_ID)
        assert r.status == 403
        assert db.batches == []
        assert len(db.calls) == 1  # no role lookup for non-admin tokens

    async def test_host_role_is_not_admin(self):
        """Activity hosts have no special forum delete rights."""
        db = RecordingDB([make_stmt(first=MockRow(author_id=OTHER_ID))])
        r = await worker.api_forum_delete_topic(
            _delete_req(f"/api/forum/topics/{TOPIC_ID}", _auth(role="host")), make_env(db=db), TOPIC_ID
        )
        assert r.status == 403

    async def test_missing_topic_returns_404(self):
        """Deleting a topic that does not exist returns 404."""
        db = RecordingDB([make_stmt(first=None)])
        r = await worker.api_forum_delete_topic(_delete_req(f"/api/forum/topics/{TOPIC_ID}", _auth()), make_env(db=db), TOPIC_ID)
        assert r.status == 404

    async def test_legacy_id_returns_404_without_query(self):
        """Legacy (non-UUID) ids short-circuit to 404 without a database query."""
        db = RecordingDB()
        r = await worker.api_forum_delete_topic(_delete_req("/api/forum/topics/42", _auth()), make_env(db=db), "42")
        assert r.status == 404
        assert db.calls == []


class TestDeleteReply:
    """DELETE /api/forum/replies/:id."""

    async def test_author_deletes_reply(self):
        """The author deletes their own reply."""
        db = RecordingDB([make_stmt(first=MockRow(author_id=USER_ID))])
        r = await worker.api_forum_delete_reply(_delete_req(f"/api/forum/replies/{REPLY_ID}", _auth()), make_env(db=db), REPLY_ID)
        assert r.status == 200
        assert db.ran("DELETE FROM forum_replies WHERE id=?")

    async def test_admin_can_delete_any_reply(self):
        """An admin whose stored role is still admin can delete someone else's reply."""
        db = RecordingDB([make_stmt(first=MockRow(author_id=OTHER_ID)), await _role("admin")])
        r = await worker.api_forum_delete_reply(
            _delete_req(f"/api/forum/replies/{REPLY_ID}", _auth(role="admin")), make_env(db=db), REPLY_ID
        )
        assert r.status == 200
        assert db.ran("DELETE FROM forum_replies WHERE id=?")

    async def test_stale_admin_token_is_rejected(self):
        """A token claiming admin is refused once the stored role is no longer admin."""
        db = RecordingDB([make_stmt(first=MockRow(author_id=OTHER_ID)), await _role("member")])
        r = await worker.api_forum_delete_reply(
            _delete_req(f"/api/forum/replies/{REPLY_ID}", _auth(role="admin")), make_env(db=db), REPLY_ID
        )
        assert r.status == 403
        assert not db.ran("DELETE FROM")

    async def test_other_user_cannot_delete(self):
        """A different member gets 403 and nothing is deleted."""
        db = RecordingDB([make_stmt(first=MockRow(author_id=OTHER_ID))])
        r = await worker.api_forum_delete_reply(_delete_req(f"/api/forum/replies/{REPLY_ID}", _auth()), make_env(db=db), REPLY_ID)
        assert r.status == 403
        assert not db.ran("DELETE FROM")

    async def test_requires_auth(self):
        """A request without a token is rejected with 401."""
        r = await worker.api_forum_delete_reply(_delete_req(f"/api/forum/replies/{REPLY_ID}"), make_env(db=RecordingDB()), REPLY_ID)
        assert r.status == 401


# ---------------------------------------------------------------------------
# Server-rendered pages
# ---------------------------------------------------------------------------

XSS = '<script>alert("x")</script>'


class TestRendering:
    """Server-rendered forum listing and topic pages."""

    async def test_topic_page_escapes_user_content(self):
        """Titles, bodies, author names and replies are HTML-escaped."""
        topic = {
            "id": TOPIC_ID, "title": XSS, "body": XSS, "created_at": "2026-11-12 10:30:00",
            "author_id": USER_ID, "author_name": XSS,
            "replies": [{"id": REPLY_ID, "body": XSS, "created_at": "2026-11-12 11:00:00",
                         "author_id": OTHER_ID, "author_name": XSS}],
        }
        html = worker._render_forum_topic_page(topic).body
        assert 'alert("x")' not in html
        assert html.count("&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;") >= 5
        assert f'data-forum-author="{USER_ID}"' in html
        assert f'id="reply-{REPLY_ID}"' in html
        assert "2026-11-12 10:30 UTC" in html
        assert "/js/forum.js" in html

    async def test_topic_page_is_revalidated(self):
        """Topic pages ask the browser to revalidate and show an empty-replies state."""
        topic = {"id": TOPIC_ID, "title": "t", "body": "b", "created_at": "", "author_id": USER_ID,
                 "author_name": "A", "replies": []}
        r = worker._render_forum_topic_page(topic)
        assert r.headers["Cache-Control"] == "private, no-cache"
        assert "No replies yet" in r.body

    async def test_detail_route_renders_new_topic(self):
        """/forum/topic/<uuid> renders a new topic with the decrypted author name."""
        name_enc = await worker.encrypt_aes("Ada Lovelace", ENC_KEY)
        db = RecordingDB([
            make_stmt(first=MockRow(id=TOPIC_ID, title="Hello forum", body="First post", created_at="2026-11-12 10:00:00",
                                    author_id=USER_ID, author_name_enc=name_enc)),
            make_stmt(all_results=[]),
        ])
        req = MockRequest(url=f"http://localhost/forum/topic/{TOPIC_ID}")
        r = await worker.render_forum_topic_detail(req, make_env(db=db), TOPIC_ID)
        assert r.status == 200
        assert "Hello forum" in r.body
        assert "Ada Lovelace" in r.body
        assert 'id="forum-reply-form"' in r.body

    async def test_listing_shows_new_topics_and_labels_archive(self):
        """New topics are listed first; legacy topics follow in the read-only archive section."""
        legacy_payload = await worker.encrypt_aes(json.dumps({
            "model": "web.ForumTopic", "pk": "7",
            "fields": {"title": "Old Django thread", "content": "From the old site."},
        }), ENC_KEY)
        db = RecordingDB([
            make_stmt(all_results=[MockRow(id=TOPIC_ID, title=XSS, body="Body text", created_at="2026-11-12 10:00:00",
                                           author_id=USER_ID, author_name_enc="", reply_count=1)]),
            make_stmt(all_results=[MockRow(legacy_model="web.ForumTopic", legacy_pk="7", payload=legacy_payload,
                                           created_at="2020-01-01", updated_at="2020-01-01")]),
        ])
        html = await worker._server_forum_records_html(make_env(db=db))
        assert "Latest discussions" in html
        assert "&lt;script&gt;" in html and XSS not in html
        assert "Community member" in html
        assert "1 reply" in html
        new_link = html.index(f"/forum/topic/{TOPIC_ID}")
        archive = html.index("Archived discussions")
        legacy_link = html.index("/forum/topic/7")
        assert new_link < archive < legacy_link
        assert "read-only" in html[archive:legacy_link]
        assert "Old Django thread" in html[archive:]

    async def test_listing_without_legacy_records_has_no_archive(self):
        """The archive heading only appears when legacy records exist."""
        db = RecordingDB([
            make_stmt(all_results=[MockRow(id=TOPIC_ID, title="New", body="b", created_at="2026-11-12 10:00:00",
                                           author_id=USER_ID, author_name_enc="", reply_count=0)]),
            make_stmt(all_results=[]),
        ])
        html = await worker._server_forum_records_html(make_env(db=db))
        assert "Archived discussions" not in html

    async def test_forum_page_is_revalidated(self):
        """/forum is served with a revalidating cache policy; other pages keep the public one."""
        env = make_env()
        set_static_content(env, "<html><body>page</body></html>")
        forum = await worker.serve_static("/forum.html", env, MockRequest(url="http://localhost/forum"))
        about = await worker.serve_static("/about.html", env, MockRequest(url="http://localhost/about"))
        assert forum.headers["Cache-Control"] == "private, no-cache"
        assert about.headers["Cache-Control"].startswith("public")

    async def test_listing_empty_state(self):
        """With no topics at all the listing shows an empty state."""
        db = RecordingDB([make_stmt(all_results=[]), make_stmt(all_results=[])])
        html = await worker._server_forum_records_html(make_env(db=db))
        assert "No discussions yet" in html

    async def test_listing_survives_missing_tables(self):
        """The listing still renders if the forum tables have not been created yet."""
        missing = make_stmt()
        missing.bind.return_value.all.side_effect = Exception("no such table: forum_topics")
        db = RecordingDB([missing, make_stmt(all_results=[])])
        html = await worker._server_forum_records_html(make_env(db=db))
        assert "No discussions yet" in html


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

class TestRouting:
    """The dispatcher sends forum API paths to the forum handlers."""

    async def test_create_topic_route(self):
        """POST /api/forum/topics reaches the create-topic handler."""
        r = await worker._dispatch(_topic_req(VALID_TOPIC), make_env(db=RecordingDB()))
        assert r.status == 401

    async def test_create_reply_route(self):
        """POST /api/forum/topics/:id/replies reaches the reply handler."""
        r = await worker._dispatch(_reply_req(TOPIC_ID, {"body": "hi"}), make_env(db=RecordingDB()))
        assert r.status == 401

    async def test_delete_topic_route(self):
        """DELETE /api/forum/topics/:id reaches the delete-topic handler."""
        db = RecordingDB([make_stmt(first=MockRow(author_id=USER_ID))])
        r = await worker._dispatch(_delete_req(f"/api/forum/topics/{TOPIC_ID}", _auth()), make_env(db=db))
        assert r.status == 200

    async def test_delete_reply_route(self):
        """DELETE /api/forum/replies/:id reaches the delete-reply handler."""
        db = RecordingDB([make_stmt(first=MockRow(author_id=USER_ID))])
        r = await worker._dispatch(_delete_req(f"/api/forum/replies/{REPLY_ID}", _auth()), make_env(db=db))
        assert r.status == 200
