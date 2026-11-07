"""
Tests for activities API handlers:
  * api_list_activities()
  * api_create_activity()
  * api_get_activity()
"""

import base64
import json
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from tests.helpers import (
    load_worker, MockRequest, MockRow, MockDB, make_env, make_stmt, json_request,
    make_init_db_stmts,
)

worker = load_worker()

SECRET = "test-encryption-key"
JWT = "test-jwt-secret"


def _parse(resp):
    return json.loads(resp.body)


def _enc(val: str) -> str:
    """Compute mock-AES ciphertext synchronously (IV = 12 zero bytes, ct = plaintext)."""
    iv = b"\x00" * 12
    return "v1:" + base64.b64encode(iv + val.encode("utf-8")).decode("ascii")


def _make_host_token(uid="host-1", username="alice", role="host"):
    return worker.create_token(uid, username, role, JWT)


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# api_list_activities()
# ---------------------------------------------------------------------------

class TestApiListActivities:
    def _req(self, query=""):
        url = f"http://localhost/api/activities{('?' + query) if query else ''}"
        return MockRequest(method="GET", url=url)

    def _activity_row(self, aid="act-1", title="Python 101", atype="course",
                      fmt="self_paced", sched="ongoing"):
        return MockRow(
            id=aid,
            title=title,
            description=_enc("A great course"),
            type=atype,
            format=fmt,
            schedule_type=sched,
            created_at="2024-01-01T00:00:00",
            host_name_enc=_enc("Alice"),
            participant_count=5,
            session_count=2,
        )

    async def test_returns_activities_list(self):
        row = self._activity_row()
        # prepare() call order: list query, then tags query per row
        tags_row = MockRow(name="Python")
        env = make_env(db=MockDB([
            make_stmt(all_results=[row]),   # main query
            make_stmt(all_results=[tags_row]),  # tags for row
        ]))
        r = await worker.api_list_activities(self._req(), env)
        assert r.status == 200
        data = _parse(r)
        assert "activities" in data
        assert len(data["activities"]) == 1
        assert data["activities"][0]["title"] == "Python 101"

    async def test_empty_db_returns_empty_list(self):
        env = make_env(db=MockDB([make_stmt(all_results=[])]))
        r = await worker.api_list_activities(self._req(), env)
        assert _parse(r)["activities"] == []

    async def test_type_filter_applied(self):
        row = self._activity_row(atype="meetup")
        env = make_env(db=MockDB([
            make_stmt(all_results=[row]),
            make_stmt(all_results=[]),
        ]))
        r = await worker.api_list_activities(self._req("type=meetup"), env)
        data = _parse(r)
        assert len(data["activities"]) == 1

    async def test_format_filter_applied(self):
        row = self._activity_row(fmt="live")
        env = make_env(db=MockDB([
            make_stmt(all_results=[row]),
            make_stmt(all_results=[]),
        ]))
        r = await worker.api_list_activities(self._req("format=live"), env)
        data = _parse(r)
        assert len(data["activities"]) == 1

    async def test_type_and_format_filter(self):
        row = self._activity_row()
        env = make_env(db=MockDB([
            make_stmt(all_results=[row]),
            make_stmt(all_results=[]),
        ]))
        r = await worker.api_list_activities(self._req("type=course&format=self_paced"), env)
        assert r.status == 200

    async def test_tag_filter_unknown_tag_returns_empty(self):
        # Tag not found → empty activities
        env = make_env(db=MockDB([make_stmt(first=None)]))
        r = await worker.api_list_activities(self._req("tag=NonExistent"), env)
        data = _parse(r)
        assert data["activities"] == []

    async def test_tag_filter_known_tag(self):
        tag_row = MockRow(id="tag-1")
        act_row = self._activity_row()
        env = make_env(db=MockDB([
            make_stmt(first=tag_row),          # tag lookup
            make_stmt(all_results=[act_row]),  # filtered activity query
            make_stmt(all_results=[]),         # tags for activity
        ]))
        r = await worker.api_list_activities(self._req("tag=Python"), env)
        data = _parse(r)
        assert len(data["activities"]) == 1

    async def test_search_filter_matches_title(self):
        row = self._activity_row(title="Python for Beginners")
        env = make_env(db=MockDB([
            make_stmt(all_results=[row]),
            make_stmt(all_results=[]),
        ]))
        r = await worker.api_list_activities(self._req("q=python"), env)
        data = _parse(r)
        assert len(data["activities"]) == 1

    async def test_search_filter_no_match(self):
        row = self._activity_row(title="Python for Beginners")
        env = make_env(db=MockDB([
            make_stmt(all_results=[row]),
            make_stmt(all_results=[]),
        ]))
        r = await worker.api_list_activities(self._req("q=javascript"), env)
        # "javascript" not in "Python for Beginners" → filtered out
        data = _parse(r)
        assert data["activities"] == []

    async def test_activity_fields_present(self):
        row = self._activity_row()
        env = make_env(db=MockDB([
            make_stmt(all_results=[row]),
            make_stmt(all_results=[]),
        ]))
        r = await worker.api_list_activities(self._req(), env)
        act = _parse(r)["activities"][0]
        for field in ("id", "title", "description", "type", "format",
                      "schedule_type", "host_name", "participant_count",
                      "session_count", "tags", "created_at"):
            assert field in act, f"Missing field: {field}"

    async def test_missing_table_initializes_schema_and_retries(self):
        row = self._activity_row()

        failing_stmt = make_stmt()
        failing_stmt.all.side_effect = Exception("D1_ERROR: no such table: activities: SQLITE_ERROR")
        init_db_stmts = await make_init_db_stmts(worker)

        env = make_env(db=MockDB(
            [failing_stmt]                           # first list query fails
            + init_db_stmts                          # init_db schema + migration statements
            + [
                make_stmt(all_results=[row]),        # retried list query succeeds
                make_stmt(all_results=[]),           # tags query
            ]
        ))

        r = await worker.api_list_activities(self._req(), env)
        assert r.status == 200
        data = _parse(r)
        assert len(data["activities"]) == 1
        assert data["activities"][0]["id"] == row.id

    async def test_non_missing_table_error_is_raised(self):
        failing_stmt = make_stmt()
        failing_stmt.all.side_effect = Exception("DB unavailable")
        env = make_env(db=MockDB([failing_stmt]))

        with pytest.raises(Exception, match="DB unavailable"):
            await worker.api_list_activities(self._req(), env)


# ---------------------------------------------------------------------------
# api_get_offline_package()
# ---------------------------------------------------------------------------

class TestApiGetOfflinePackage:
    def _req(self, activity_ref="act-1", token=None):
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return MockRequest(
            method="GET",
            url=f"http://localhost/api/activities/{activity_ref}/offline-package",
            headers=headers,
        )

    def _activity(self, aid="act-1", slug="python-101"):
        return MockRow(
            id=aid, title="Python 101", type="course", format="self_paced",
            slug=slug, host_id="host-1",
        )

    def _material(self, mid, **overrides):
        values = {
            "id": mid,
            "title": f"Material {mid}",
            "description": "A learning resource",
            "material_type": "pdf",
            "file_url": "",
            "file_r2_key": "",
            "external_url": "",
            "display_order": 0,
            "is_downloadable": 0,
            "requires_enrollment": 1,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-02T00:00:00",
        }
        values.update(overrides)
        return MockRow(**values)

    def _env(self, activity=None, enrollment=None, materials=None, bucket=None):
        env = make_env(db=MockDB([
            make_stmt(first=activity),
            make_stmt(first=enrollment),
            make_stmt(all_results=materials or []),
        ]))
        env.MY_BUCKET = bucket
        return env

    async def test_requires_authentication(self):
        r = await worker.api_get_offline_package(
            "act-1", self._req(), self._env()
        )
        assert r.status == 401

    async def test_rejects_non_enrolled_learner(self):
        token = _make_host_token(uid="learner-1", role="member")
        r = await worker.api_get_offline_package(
            "act-1", self._req(token=token),
            self._env(activity=self._activity(), enrollment=None),
        )
        assert r.status == 403

    async def test_rejects_inactive_enrollee_without_manifest_data(self):
        token = _make_host_token(uid="learner-1", role="member")
        r = await worker.api_get_offline_package(
            "act-1", self._req(token=token),
            self._env(
                activity=self._activity(),
                enrollment=MockRow(role="participant", status="inactive"),
                materials=[self._material("private")],
            ),
        )
        assert r.status == 403
        assert "package" not in _parse(r)
        assert "private" not in r.body

    async def test_active_enrollee_receives_manifest(self):
        token = _make_host_token(uid="learner-1", role="member")
        enrollment = MockRow(role="participant", status="active")
        r = await worker.api_get_offline_package(
            "act-1", self._req(token=token),
            self._env(
                activity=self._activity(), enrollment=enrollment,
                materials=[self._material("mat-a")],
            ),
        )
        assert r.status == 200
        assert _parse(r)["package"]["activity_id"] == "act-1"

    async def test_host_receives_ordered_manifest_with_r2_metadata(self):
        token = _make_host_token()
        material_a = self._material(
            "mat-a", display_order=2, is_downloadable=1, file_r2_key="courses/a.pdf"
        )
        material_b = self._material(
            "mat-b", display_order=1, external_url="https://example.test/guide"
        )
        bucket = SimpleNamespace(
            get=AsyncMock(return_value=SimpleNamespace(
                size=42,
                etag="etag-a",
                checksums={"sha256": "hash-a"},
                http_metadata=SimpleNamespace(contentType="application/pdf"),
            ))
        )
        r = await worker.api_get_offline_package(
            "python-101", self._req("python-101", token),
            self._env(
                activity=self._activity(),
                enrollment=None,
                materials=[material_a, material_b],
                bucket=bucket,
            ),
        )
        assert r.status == 200
        package = _parse(r)["package"]
        assert package["package_id"] == "activity:act-1"
        assert [item["material_id"] for item in package["resources"]] == ["mat-b", "mat-a"]
        downloadable = package["resources"][1]
        assert downloadable["availability"] == "available"
        assert downloadable["downloadable"] is True
        assert downloadable["url"] == "/media/courses/a.pdf"
        assert downloadable["size_bytes"] == 42
        assert downloadable["content_hash"] == "sha256:hash-a"
        assert "file_r2_key" not in json.dumps(package)

    async def test_r2_checksum_bytes_are_encoded(self):
        token = _make_host_token()
        bucket = SimpleNamespace(
            get=AsyncMock(return_value=SimpleNamespace(
                size=2,
                checksums=SimpleNamespace(sha256=b"\x01\x02", md5=None),
            ))
        )
        r = await worker.api_get_offline_package(
            "act-1", self._req(token=token),
            self._env(
                activity=self._activity(), enrollment=None,
                materials=[self._material("mat-a", file_r2_key="courses/a.pdf", is_downloadable=1)],
                bucket=bucket,
            ),
        )
        assert _parse(r)["package"]["resources"][0]["content_hash"] == "sha256:0102"

    async def test_slug_resolution_precedes_id_resolution(self):
        token = _make_host_token()
        slug_activity = self._activity(aid="slug-activity", slug="collision")
        env = make_env(db=MockDB([
            make_stmt(first=slug_activity),
            make_stmt(first=None),
            make_stmt(all_results=[self._material("mat-a")]),
        ]))
        r = await worker.api_get_offline_package(
            "collision", self._req("collision", token),
            env,
        )
        assert r.status == 200
        assert _parse(r)["package"]["activity_id"] == "slug-activity"

    async def test_resource_availability_distinguishes_locations(self):
        token = _make_host_token()
        existing = SimpleNamespace(etag="etag", checksums=None)
        bucket = SimpleNamespace(
            get=AsyncMock(side_effect=lambda key: existing if key == "media/file.pdf" else None)
        )
        materials = [
            self._material("missing", is_downloadable=1),
            self._material("external", external_url="https://example.test/guide"),
            self._material("download", file_url="/media/media/file.pdf", is_downloadable=1),
        ]
        r = await worker.api_get_offline_package(
            "act-1", self._req(token=token),
            self._env(activity=self._activity(), enrollment=None, materials=materials, bucket=bucket),
        )
        resources = {item["material_id"]: item for item in _parse(r)["package"]["resources"]}
        assert resources["missing"]["availability"] == "unavailable"
        assert resources["external"]["availability"] == "online_only"
        assert resources["download"]["availability"] == "available"

    async def test_media_manifest_url_resolves_to_exact_r2_key(self):
        bucket = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(body=b"data")))
        response = await worker.serve_r2_media(
            "/media/courses/lesson%20one.pdf", SimpleNamespace(MY_BUCKET=bucket)
        )
        assert response.status == 200
        bucket.get.assert_awaited_once_with("courses/lesson one.pdf")

    async def test_identical_manifests_have_identical_versions(self):
        token = _make_host_token()
        material = self._material("mat-a", file_url="/media/material-a.pdf", is_downloadable=1)
        bucket = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(etag="etag")))
        first = await worker.api_get_offline_package(
            "act-1", self._req(token=token),
            self._env(activity=self._activity(), enrollment=None, materials=[material], bucket=bucket),
        )
        second = await worker.api_get_offline_package(
            "act-1", self._req(token=token),
            self._env(activity=self._activity(), enrollment=None, materials=[material], bucket=bucket),
        )
        assert _parse(first)["package"]["package_version"] == _parse(second)["package"]["package_version"]

    async def test_material_changes_change_version(self):
        token = _make_host_token()
        base = self._material("mat-a", file_url="/media/material-a.pdf", is_downloadable=1)
        changed = self._material("mat-a", file_url="/media/material-a.pdf", is_downloadable=0)
        bucket = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(etag="etag")))
        first = await worker.api_get_offline_package(
            "act-1", self._req(token=token),
            self._env(activity=self._activity(), enrollment=None, materials=[base], bucket=bucket),
        )
        second = await worker.api_get_offline_package(
            "act-1", self._req(token=token),
            self._env(activity=self._activity(), enrollment=None, materials=[changed], bucket=bucket),
        )
        assert _parse(first)["package"]["package_version"] != _parse(second)["package"]["package_version"]
        assert _parse(second)["package"]["resources"][0]["availability"] == "online_only"

    async def test_missing_r2_object_is_unavailable_without_fake_integrity_data(self):
        token = _make_host_token()
        bucket = SimpleNamespace(get=AsyncMock(return_value=None))
        material = self._material("mat-a", file_r2_key="courses/missing.pdf", is_downloadable=1)
        r = await worker.api_get_offline_package(
            "act-1", self._req(token=token),
            self._env(
                activity=self._activity(), enrollment=None,
                materials=[material], bucket=bucket,
            ),
        )
        resource = _parse(r)["package"]["resources"][0]
        assert resource["availability"] == "unavailable"
        assert resource["downloadable"] is False
        assert resource["content_hash"] is None
        assert resource["url"] is None

    async def test_duplicate_material_ids_are_not_repeated(self):
        token = _make_host_token()
        materials = [self._material("mat-a"), self._material("mat-a", title="duplicate")]
        r = await worker.api_get_offline_package(
            "act-1", self._req(token=token),
            self._env(activity=self._activity(), enrollment=None, materials=materials),
        )
        resources = _parse(r)["package"]["resources"]
        assert len(resources) == 1


# ---------------------------------------------------------------------------
# api_create_activity()
# ---------------------------------------------------------------------------

class TestApiCreateActivity:
    def _req(self, payload, token=None):
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return json_request("/api/activities", payload, headers=headers)

    async def test_no_auth_returns_401(self):
        env = make_env()
        r = await worker.api_create_activity(self._req({"title": "My Course"}), env)
        assert r.status == 401

    async def test_missing_title_returns_400(self):
        token = _make_host_token()
        env = make_env()
        r = await worker.api_create_activity(self._req({"description": "no title"}, token), env)
        assert r.status == 400

    async def test_successful_creation(self):
        token = _make_host_token()
        env = make_env(db=MockDB([make_stmt()]))  # INSERT run()
        r = await worker.api_create_activity(
            self._req({"title": "New Course", "description": "Awesome"}, token), env
        )
        assert r.status == 200
        data = _parse(r)
        assert data["success"] is True
        assert data["data"]["title"] == "New Course"
        assert "id" in data["data"]

    async def test_invalid_type_defaults_to_course(self):
        token = _make_host_token()
        env = make_env(db=MockDB([make_stmt()]))
        r = await worker.api_create_activity(
            self._req({"title": "T", "type": "invalid_type"}, token), env
        )
        assert r.status == 200

    async def test_invalid_format_defaults_to_self_paced(self):
        token = _make_host_token()
        env = make_env(db=MockDB([make_stmt()]))
        r = await worker.api_create_activity(
            self._req({"title": "T", "format": "invalid"}, token), env
        )
        assert r.status == 200

    async def test_tags_are_created(self):
        token = _make_host_token()
        # Stmts: slug lookup, INSERT activity, tag lookup (not found), INSERT tag, INSERT activity_tag
        tag_stmt = make_stmt(first=None)  # tag not found
        env = make_env(db=MockDB([
            make_stmt(),   # slug lookup
            make_stmt(),   # INSERT activity
            tag_stmt,      # SELECT tag WHERE name=?
            make_stmt(),   # INSERT tag
            make_stmt(),   # INSERT activity_tags
        ]))
        r = await worker.api_create_activity(
            self._req({"title": "T", "tags": ["Python"]}, token), env
        )
        assert r.status == 200

    async def test_existing_tags_reused(self):
        token = _make_host_token()
        existing_tag = MockRow(id="tag-existing")
        env = make_env(db=MockDB([
            make_stmt(),                    # slug lookup
            make_stmt(),                    # INSERT activity
            make_stmt(first=existing_tag),  # SELECT tag WHERE name=? → found
            make_stmt(),                    # INSERT activity_tags
        ]))
        r = await worker.api_create_activity(
            self._req({"title": "T", "tags": ["Python"]}, token), env
        )
        assert r.status == 200

    async def test_db_error_returns_500(self):
        token = _make_host_token()
        stmt = make_stmt()
        stmt.bind.return_value.run.side_effect = Exception("DB error")
        env = make_env(db=MockDB([
            make_stmt(),  # slug lookup
            stmt,         # INSERT activities fails
        ]))
        r = await worker.api_create_activity(
            self._req({"title": "Course"}, token), env
        )
        assert r.status == 500

    async def test_slug_db_error_returns_500(self):
        token = _make_host_token()
        stmt = make_stmt()
        stmt.bind.return_value.first.side_effect = Exception("DB error during slug lookup")
        env = make_env(db=MockDB([stmt]))
        r = await worker.api_create_activity(
            self._req({"title": "Course"}, token), env
        )
        assert r.status == 500

    async def test_invalid_json_returns_400(self):
        token = _make_host_token()
        req = MockRequest(method="POST", url="http://localhost/api/activities",
                          headers={"Authorization": f"Bearer {token}"},
                          body="not-json")
        r = await worker.api_create_activity(req, make_env())
        assert r.status == 400


# ---------------------------------------------------------------------------
# api_get_activity()
# ---------------------------------------------------------------------------

class TestApiGetActivity:
    def _req(self, act_id="act-1", token=None):
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return MockRequest(method="GET",
                           url=f"http://localhost/api/activities/{act_id}",
                           headers=headers)

    def _activity_row(self, host_uid="host-1"):
        return MockRow(
            id="act-1",
            title="Python 101",
            description=_enc("Great course"),
            type="course",
            format="self_paced",
            schedule_type="ongoing",
            created_at="2024-01-01",
            host_name_enc=_enc("Alice"),
            host_uid=host_uid,
        )

    def _count_row(self, cnt=3):
        return MockRow(cnt=cnt)

    async def test_not_found_returns_404(self):
        env = make_env(db=MockDB([make_stmt(first=None)]))
        r = await worker.api_get_activity("bad-id", self._req("bad-id"), env)
        assert r.status == 404

    async def test_unauthenticated_access_returns_activity(self):
        act = self._activity_row()
        sessions_row = MockRow(
            id="ses-1", title="Intro", description=_enc("desc"),
            start_time="2024-01-01", end_time="2024-01-01", location=_enc("online"),
        )
        count = self._count_row()
        env = make_env(db=MockDB([
            make_stmt(first=act),           # SELECT activity
            make_stmt(all_results=[sessions_row]),  # SELECT sessions
            make_stmt(all_results=[]),      # SELECT tags
            make_stmt(first=count),         # COUNT enrollments
        ]))
        r = await worker.api_get_activity("act-1", self._req(), env)
        assert r.status == 200
        data = _parse(r)
        assert "activity" in data
        assert data["is_enrolled"] is False
        assert data["is_host"] is False

    async def test_authenticated_non_enrolled_user(self):
        token = _make_host_token(uid="other-user", role="member")
        act = self._activity_row(host_uid="host-1")
        count = self._count_row()
        env = make_env(db=MockDB([
            make_stmt(first=act),
            make_stmt(first=None),          # enrollment lookup → not enrolled
            make_stmt(all_results=[]),      # sessions
            make_stmt(all_results=[]),      # tags
            make_stmt(first=count),
        ]))
        r = await worker.api_get_activity("act-1", self._req(token=token), env)
        assert r.status == 200
        data = _parse(r)
        assert data["is_enrolled"] is False
        assert data["is_host"] is False

    async def test_host_sees_is_host_true(self):
        token = _make_host_token(uid="host-1", role="host")
        act = self._activity_row(host_uid="host-1")
        count = self._count_row()
        env = make_env(db=MockDB([
            make_stmt(first=act),
            make_stmt(first=None),          # enrollment lookup
            make_stmt(all_results=[]),      # sessions
            make_stmt(all_results=[]),      # tags
            make_stmt(first=count),
        ]))
        r = await worker.api_get_activity("act-1", self._req(token=token), env)
        data = _parse(r)
        assert data["is_host"] is True

    async def test_enrolled_user_sees_is_enrolled_true(self):
        token = _make_host_token(uid="member-1", role="member")
        act = self._activity_row(host_uid="host-1")
        enrollment = MockRow(id="enr-1", role="participant", status="active")
        count = self._count_row()
        env = make_env(db=MockDB([
            make_stmt(first=act),
            make_stmt(first=enrollment),    # enrolled
            make_stmt(all_results=[]),      # sessions
            make_stmt(all_results=[]),      # tags
            make_stmt(first=count),
        ]))
        r = await worker.api_get_activity("act-1", self._req(token=token), env)
        data = _parse(r)
        assert data["is_enrolled"] is True
        assert data["enrollment"]["role"] == "participant"

    async def test_activity_fields_complete(self):
        act = self._activity_row()
        count = self._count_row(cnt=7)
        env = make_env(db=MockDB([
            make_stmt(first=act),
            make_stmt(all_results=[]),
            make_stmt(all_results=[]),
            make_stmt(first=count),
        ]))
        r = await worker.api_get_activity("act-1", self._req(), env)
        activity = _parse(r)["activity"]
        for field in ("id", "title", "description", "type", "format",
                      "schedule_type", "host_name", "participant_count", "tags", "created_at"):
            assert field in activity
        assert activity["participant_count"] == 7


class TestApiCertificates:
    def _req(self, method="GET", path="/api/certificates", token=None):
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return MockRequest(method=method, url=f"http://localhost{path}", headers=headers)

    async def test_generate_certificate_requires_auth(self):
        env = make_env()
        req = self._req(method="POST", path="/api/certificates/generate/enr-1")
        r = await worker.api_generate_certificate(req, env, "enr-1")
        assert r.status == 401

    async def test_generate_certificate_not_found(self):
        token = _make_host_token(uid="user-1")
        env = make_env(db=MockDB([make_stmt(first=None), make_stmt(first=None)]))
        req = self._req(method="POST", path="/api/certificates/generate/enr-1", token=token)
        r = await worker.api_generate_certificate(req, env, "enr-1")
        assert r.status == 404

    async def test_generate_certificate_success(self):
        token = _make_host_token(uid="user-1")
        enr = MockRow(id="enr-1", user_id="user-1", host_id="host-1", status="completed", activity_id="act-1")
        env = make_env(db=MockDB([
            make_stmt(first=enr),        # fetch enrollment
            make_stmt(first=None),       # check existing cert
            make_stmt(),                 # insert cert
            make_stmt(),                 # notification
        ]))
        req = self._req(method="POST", path="/api/certificates/generate/enr-1", token=token)
        r = await worker.api_generate_certificate(req, env, "enr-1")
        assert r.status == 200
        data = _parse(r)
        assert "uuid" in data["data"]
        assert "/certificate.html?uuid=" in data["data"]["url"]

    async def test_generate_certificate_by_activity_id_fallback(self):
        token = _make_host_token(uid="user-1")
        enr = MockRow(id="enr-1", user_id="user-1", host_id="host-1", status="completed", activity_id="act-1")
        env = make_env(db=MockDB([
            make_stmt(first=None),       # fetch enrollment by enrollment.id (none)
            make_stmt(first=enr),        # fetch enrollment by activity.id / slug
            make_stmt(first=None),       # check existing cert
            make_stmt(),                 # insert cert
            make_stmt(),                 # notification
        ]))
        req = self._req(method="POST", path="/api/certificates/generate/act-1", token=token)
        r = await worker.api_generate_certificate(req, env, "act-1")
        assert r.status == 200
        data = _parse(r)
        assert "uuid" in data["data"]

    async def test_get_certificate_not_found(self):
        env = make_env(db=MockDB([make_stmt(first=None)]))
        req = self._req(method="GET", path="/api/certificates/cert-uuid")
        r = await worker.api_get_certificate(req, env, "cert-uuid")
        assert r.status == 404
