"""Tests for /api/activities/:ref/reviews.

Self-contained: a tiny SQLite-backed fake of the D1 binding, with the crypto and
token helpers patched. If the repo already has a D1 fixture in conftest.py, swap
`FakeD1`/`env` for it and keep the test bodies as they are.
"""
import asyncio
import json
import sqlite3
from types import SimpleNamespace

import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import worker


# --------------------------------------------------------------------------- fakes
class _Result:
    def __init__(self, results):
        self.results = results


class _Stmt:
    def __init__(self, db, sql):
        self.db, self.sql, self.args = db, sql, ()

    def bind(self, *args):
        self.args = args
        return self

    def _rows(self):
        cur = self.db.conn.execute(self.sql, self.args)
        cols = [c[0] for c in cur.description] if cur.description else []
        return [SimpleNamespace(**dict(zip(cols, r))) for r in cur.fetchall()]

    async def first(self):
        rows = self._rows()
        return rows[0] if rows else None

    async def all(self):
        return _Result(self._rows())

    async def run(self):
        self.db.conn.execute(self.sql, self.args)
        self.db.conn.commit()
        return _Result([])


class FakeD1:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("PRAGMA foreign_keys=ON")

    def prepare(self, sql):
        return _Stmt(self, sql)


class FakeReq:
    def __init__(self, method="GET", url="https://x.test/api/activities/a1/reviews",
                 user=None, body=None, raw=None):
        self.method, self.url = method, url
        self.headers = {"Authorization": f"Bearer {user}"} if user else {}
        self._text = raw if raw is not None else json.dumps(body if body is not None else {})

    async def text(self):
        return self._text


def run(coro):
    return asyncio.run(coro)


def body_of(resp):
    return json.loads(resp.body)


@pytest.fixture
def env(monkeypatch):
    async def fake_enc(text, _k):
        return "enc:" + text

    async def fake_dec(text, _k):
        return text[4:] if text.startswith("enc:") else text

    monkeypatch.setattr(worker, "encrypt_aes", fake_enc)
    monkeypatch.setattr(worker, "decrypt_aes", fake_dec)
    monkeypatch.setattr(
        worker, "verify_token",
        lambda raw, _s, leeway_seconds=60: {"id": raw.replace("Bearer ", "")} if raw else None,
    )
    e = SimpleNamespace(DB=FakeD1(), JWT_SECRET="s", ENCRYPTION_KEY="k")
    run(worker.init_db(e))
    return e


def sql(env, q, *a):
    env.DB.conn.execute(q, a)
    env.DB.conn.commit()


def count(env, table="activity_reviews"):
    return env.DB.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


@pytest.fixture
def world(env):
    for uid in ("host", "u1", "u2", "u3", "u4"):
        sql(env, "INSERT INTO users (id,username_hash,email_hash,name,username,email,password_hash,role)"
                 " VALUES (?,?,?,?,?,?,?,?)",
            uid, "uh" + uid, "eh" + uid, "enc:Name " + uid, "enc:" + uid, "enc:e", "x", "member")
    sql(env, "INSERT INTO activities (id,title,host_id,slug) VALUES ('a1','T','host','my-slug')")
    sql(env, "INSERT INTO activity_completions (id,activity_id,user_id,kind) VALUES ('c1','a1','u1','completed')")
    sql(env, "INSERT INTO activity_completions (id,activity_id,user_id,kind) VALUES ('c2','a1','u2','completed')")
    sql(env, "INSERT INTO enrollments (id,activity_id,user_id,status) VALUES ('e3','a1','u3','active')")
    return env


def call(fn, env, ref="a1", **kw):
    return run(fn(ref, FakeReq(**kw), env))


def create(env, user, rating=5, review="Great", ref="a1"):
    return call(worker.api_create_review, env, ref, method="POST", user=user,
                body={"rating": rating, "review": review})


# --------------------------------------------------------------------------- tests
def test_public_listing_without_auth(world):
    create(world, "u1", 4, "Nice")
    r = call(worker.api_list_reviews, world)
    d = body_of(r)["data"]
    assert r.status == 200
    assert d["summary"]["count"] == 1 and d["viewer"]["signed_in"] is False
    rv = d["reviews"][0]
    assert rv["reviewer_name"] == "Name u1" and rv["review"] == "Nice"
    assert "user_id" not in rv and not rv["is_own"]


def test_unauthenticated_submit_rejected(world):
    r = call(worker.api_create_review, world, method="POST", body={"rating": 5, "review": "x"})
    assert r.status == 401 and count(world) == 0


def test_completed_learner_can_submit_by_id_and_slug(world):
    assert create(world, "u1", 5, "ok").status == 200
    assert create(world, "u2", 3, "meh", ref="my-slug").status == 200
    assert count(world) == 2


def test_enrolled_but_incomplete_rejected(world):
    r = create(world, "u3")
    assert r.status == 403 and count(world) == 0


def test_completed_enrollment_status_qualifies(world):
    sql(world, "UPDATE enrollments SET status='completed' WHERE id='e3'")
    assert create(world, "u3").status == 200


def test_non_enrolled_rejected(world):
    assert create(world, "u4").status == 403


def test_host_cannot_review(world):
    sql(world, "INSERT INTO activity_completions (id,activity_id,user_id,kind) VALUES ('ch','a1','host','completed')")
    assert create(world, "host").status == 403 and count(world) == 0


def test_duplicate_rejected_and_concurrent_unique_violation_is_409(world):
    assert create(world, "u1").status == 200
    assert create(world, "u1").status == 409
    assert count(world) == 1
    # Simulate the race: the pre-check passes but the INSERT hits UNIQUE.
    async def never_exists_then_insert(*a, **k):
        return False
    sql(world, "DELETE FROM activity_reviews")
    sql(world, "INSERT INTO activity_reviews (id,activity_id,user_id,rating,review) VALUES ('r','a1','u1',5,'enc:x')")
    orig = world.DB.prepare

    class Racy(FakeD1):
        def prepare(self_inner, q):
            st = orig(q)
            if q.startswith("SELECT id FROM activity_reviews"):
                async def none():
                    return None
                st.first = none
            return st
    racy = SimpleNamespace(DB=Racy(), JWT_SECRET="s", ENCRYPTION_KEY="k")
    racy.DB.conn = world.DB.conn
    assert create(racy, "u1").status == 409


@pytest.mark.parametrize("rating", [True, False, 0, 6, -1, 3.5, "5", None, [5]])
def test_invalid_ratings_rejected(world, rating):
    r = create(world, "u1", rating)
    assert r.status == 400 and count(world) == 0


def test_whole_number_float_accepted(world):
    assert create(world, "u1", 4.0).status == 200


@pytest.mark.parametrize("text", ["", "   ", "x" * 2001, None])
def test_empty_and_oversized_text_rejected(world, text):
    assert create(world, "u1", 5, text).status == 400


def test_max_length_text_accepted(world):
    assert create(world, "u1", 5, "x" * 2000).status == 200


def test_invalid_json_rejected(world):
    r = call(worker.api_create_review, world, method="POST", user="u1", raw="{nope")
    assert r.status == 400


def test_edit_own_review(world):
    create(world, "u1", 5, "old")
    r = call(worker.api_update_review, world, method="PUT", user="u1", body={"rating": 2, "review": "new"})
    assert r.status == 200
    mine = body_of(call(worker.api_list_reviews, world, user="u1"))["data"]["viewer"]["my_review"]
    assert mine["rating"] == 2 and mine["review"] == "new"


def test_cannot_edit_someone_elses_review(world):
    create(world, "u1", 5, "mine")
    # u2 has no review: PUT must 404 and must not touch u1's row.
    sql(
        world,
        "INSERT INTO enrollments (id,activity_id,user_id,status) VALUES ('e1','a1','u1','completed')"
    )
    r = call(worker.api_update_review, world, method="PUT", user="u2", body={"rating": 1, "review": "hijack"})
    assert r.status == 404
    d = body_of(call(worker.api_list_reviews, world))["data"]["reviews"][0]
    assert d["rating"] == 5 and d["review"] == "mine"


def test_update_requires_auth_and_valid_body(world):
    create(world, "u1")
    assert call(worker.api_update_review, world, method="PUT", body={"rating": 1, "review": "x"}).status == 401
    assert call(worker.api_update_review, world, method="PUT", user="u1", body={"rating": 9, "review": "x"}).status == 400


def test_delete_own_review(world):
    create(world, "u1")
    r = call(worker.api_delete_review, world, method="DELETE", user="u1")
    assert r.status == 200 and count(world) == 0


def test_cannot_delete_someone_elses_review(world):
    create(world, "u1")
    r = call(worker.api_delete_review, world, method="DELETE", user="u2")
    assert r.status == 404 and count(world) == 1
    assert call(worker.api_delete_review, world, method="DELETE").status == 401


def test_average_and_distribution(world):
    sql(world, "INSERT INTO activity_completions (id,activity_id,user_id,kind) VALUES ('c4','a1','u3','completed')")
    create(world, "u1", 5)
    create(world, "u2", 4)
    create(world, "u3", 4)
    s = body_of(call(worker.api_list_reviews, world))["data"]["summary"]
    assert s["count"] == 3 and s["average"] == 4.3
    assert s["distribution"] == {"1": 0, "2": 0, "3": 0, "4": 2, "5": 1}


def test_empty_summary(world):
    s = body_of(call(worker.api_list_reviews, world))["data"]["summary"]
    assert s == {"average": 0, "count": 0, "distribution": {str(n): 0 for n in range(1, 6)}}


def test_summary_changes_after_create_update_delete(world):
    def summ():
        return body_of(call(worker.api_list_reviews, world))["data"]["summary"]
    create(world, "u1", 5)
    assert (summ()["count"], summ()["average"]) == (1, 5)
    call(worker.api_update_review, world, method="PUT", user="u1", body={"rating": 1, "review": "bad"})
    assert (summ()["count"], summ()["average"]) == (1, 1)
    call(worker.api_delete_review, world, method="DELETE", user="u1")
    assert (summ()["count"], summ()["average"]) == (0, 0)


def test_pagination_has_more_and_no_overlap(world):
    for i in range(5):
        sql(world, "INSERT INTO users (id,username_hash,email_hash,name,username,email,password_hash,role)"
                   " VALUES (?,?,?,?,?,?,?,?)", f"p{i}", f"puh{i}", f"peh{i}", f"enc:P{i}", "enc:p", "enc:e", "x", "member")
        sql(world, "INSERT INTO activity_reviews (id,activity_id,user_id,rating,review,created_at)"
                   " VALUES (?,?,?,?,?,?)", f"rv{i}", "a1", f"p{i}", 5, "enc:t", f"2026-01-0{i+1} 00:00:00")
    url = "https://x.test/api/activities/a1/reviews?limit=2&offset="
    seen, offset, pages = [], 0, 0
    while True:
        d = body_of(run(worker.api_list_reviews("a1", FakeReq(url=url + str(offset)), world)))["data"]
        seen += [r["id"] for r in d["reviews"]]
        pages += 1
        if not d["has_more"]:
            break
        offset += 2
    assert pages == 3 and len(seen) == 5 and len(set(seen)) == 5


def test_viewer_state(world):
    d = lambda u: body_of(call(worker.api_list_reviews, world, user=u))["data"]["viewer"]
    assert d("u1")["can_review"] is True
    assert d("u3")["can_review"] is False
    assert d("host")["is_host"] is True and d("host")["can_review"] is False
    create(world, "u1", 3, "mine")
    v = d("u1")
    assert v["can_review"] is False and v["my_review"]["rating"] == 3


def test_missing_activity_and_review(world):
    assert call(worker.api_list_reviews, world, "nope").status == 404
    assert create(world, "u1", ref="nope").status == 404
    assert call(worker.api_update_review, world, "nope", method="PUT", user="u1",
                body={"rating": 3, "review": "x"}).status == 404
    assert call(worker.api_delete_review, world, "nope", method="DELETE", user="u1").status == 404
    assert call(worker.api_delete_review, world, method="DELETE", user="u1").status == 404


def test_missing_table_is_recovered(env):
    # Fresh DB without the reviews table: first call must init_db and succeed.
    sql(env, "INSERT INTO users (id,username_hash,email_hash,name,username,email,password_hash,role)"
             " VALUES ('h','uh','eh','enc:H','enc:h','enc:e','x','host')")
    sql(env, "INSERT INTO activities (id,title,host_id,slug) VALUES ('a1','T','h','s')")
    sql(env, "DROP TABLE activity_reviews")
    r = call(worker.api_list_reviews, env)
    assert r.status == 200 and body_of(r)["data"]["summary"]["count"] == 0
    assert count(env) == 0


def test_account_deletion_removes_reviews(world, monkeypatch):
    create(world, "u1")
    create(world, "u2")

    async def fake_text():
        return json.dumps({"confirmation": "DELETE"})

    r = FakeReq(method="POST", user="u1", body={"confirmation": "DELETE"})
    resp = run(worker.api_delete_account(r, world))
    assert resp.status == 200
    rows = world.DB.conn.execute("SELECT user_id FROM activity_reviews").fetchall()
    assert rows == [("u2",)]


def test_rating_check_constraint_and_cascade(world):
    with pytest.raises(sqlite3.IntegrityError):
        sql(world, "INSERT INTO activity_reviews (id,activity_id,user_id,rating,review) VALUES ('z','a1','u1',9,'')")
    create(world, "u1")
    sql(world, "DELETE FROM enrollments")  # enrollments FK has no cascade in the existing schema
    sql(world, "DELETE FROM activities WHERE id='a1'")
    assert count(world) == 0

@pytest.mark.parametrize("raw_rating", ["1e309", "-1e309", "1e400", "NaN", "Infinity", "-Infinity"])
def test_non_finite_ratings_get_400_not_a_server_error(world, raw_rating):
    payload = '{"rating": %s, "review": "text"}' % raw_rating
    r = call(worker.api_create_review, world, method="POST", user="u1", raw=payload)
    assert r.status == 400 and count(world) == 0
    create(world, "u1", 4, "ok")
    r = call(worker.api_update_review, world, method="PUT", user="u1", raw=payload)
    assert r.status == 400


def test_account_deletion_fails_closed_when_review_cleanup_fails(world):
    create(world, "u1", 5, "mine")

    sql(
        world,
        "INSERT INTO enrollments (id,activity_id,user_id,status) "
        "VALUES ('e1','a1','u1','completed')"
    )

    class FailingReviewDelete:
        def prepare(self, q):
            if q.startswith("DELETE FROM activity_reviews"):
                raise RuntimeError("D1 unavailable")
            return world.DB.prepare(q)

    broken = SimpleNamespace(DB=FailingReviewDelete(), JWT_SECRET="s", ENCRYPTION_KEY="k")
    resp = run(worker.api_delete_account(FakeReq(method="POST", user="u1", body={"confirmation": "DELETE"}), broken))
    assert resp.status == 500
    assert world.DB.conn.execute("SELECT name FROM users WHERE id='u1'").fetchone()[0] == "enc:Name u1"
    assert count(world) == 1
    # Nothing irreversible may have happened: learning records survive the failed request.
    mine = lambda t: world.DB.conn.execute(
        f"SELECT COUNT(*) FROM {t} WHERE user_id='u1'"
    ).fetchone()[0]
    assert mine("enrollments") == 1
    assert mine("activity_completions") == 1
    resp = run(worker.api_delete_account(FakeReq(method="POST", user="u1", body={"confirmation": "DELETE"}), world))
    assert resp.status == 200 and count(world) == 0


def test_account_deletion_works_when_review_table_does_not_exist(world):
    sql(world, "DROP TABLE IF EXISTS activity_reviews")
    resp = run(worker.api_delete_account(FakeReq(method="POST", user="u1", body={"confirmation": "DELETE"}), world))
    assert resp.status == 200