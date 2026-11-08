"""Regression tests for certificate generation and public verification."""

import base64
import json

from tests.helpers import (
    MockDB,
    MockRequest,
    MockRow,
    make_env,
    make_stmt,
    load_worker,
)


worker = load_worker()
JWT = "test-jwt-secret"


def _parse(response):
    return json.loads(response.body)


def _enc(value):
    iv = b"\x00" * 12
    return "v1:" + base64.b64encode(iv + value.encode("utf-8")).decode("ascii")


def _token(user_id, role="student"):
    return worker.create_token(user_id, user_id, role, JWT)


def _request(method, path, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return MockRequest(method=method, url=f"http://localhost{path}", headers=headers)


def _enrollment(
    *,
    enrollment_id="enr-1",
    user_id="learner-1",
    host_id="host-1",
    activity_id="activity-1",
    status="completed",
):
    return MockRow(
        id=enrollment_id,
        user_id=user_id,
        host_id=host_id,
        activity_id=activity_id,
        status=status,
    )


class TestCertificateGeneration:
    async def test_requires_authentication(self):
        env = make_env()

        response = await worker.api_generate_certificate(
            _request("POST", "/api/certificates/generate/enr-1"),
            env,
            "enr-1",
        )

        assert response.status == 401
        assert _parse(response)["error"] == "Authentication required"

    async def test_learner_can_generate_certificate_for_own_completed_enrollment(self):
        insert_stmt = make_stmt()
        env = make_env(
            db=MockDB(
                [
                    make_stmt(first=_enrollment()),
                    make_stmt(first=None),
                    insert_stmt,
                    make_stmt(first=None),
                ]
            )
        )

        response = await worker.api_generate_certificate(
            _request(
                "POST",
                "/api/certificates/generate/enr-1",
                _token("learner-1"),
            ),
            env,
            "enr-1",
        )

        body = _parse(response)
        certificate = body["data"]
        assert response.status == 200
        assert body["success"] is True
        assert certificate["uuid"]
        assert certificate["url"] == f"/certificate.html?uuid={certificate['uuid']}"
        insert_stmt.bind.return_value.run.assert_awaited_once()

    async def test_learner_cannot_generate_another_users_certificate(self):
        insert_stmt = make_stmt()
        env = make_env(
            db=MockDB(
                [
                    make_stmt(first=_enrollment(user_id="other-learner")),
                    insert_stmt,
                ]
            )
        )

        response = await worker.api_generate_certificate(
            _request(
                "POST",
                "/api/certificates/generate/enr-1",
                _token("learner-1"),
            ),
            env,
            "enr-1",
        )

        assert response.status == 403
        assert _parse(response)["error"] == "Forbidden"
        assert insert_stmt.bind.return_value.run.await_count == 0

    async def test_activity_host_can_generate_certificate_for_enrollment(self):
        insert_stmt = make_stmt()
        env = make_env(
            db=MockDB(
                [
                    make_stmt(first=_enrollment(user_id="learner-1", host_id="host-1")),
                    make_stmt(first=None),
                    insert_stmt,
                    make_stmt(first=None),
                ]
            )
        )

        response = await worker.api_generate_certificate(
            _request(
                "POST",
                "/api/certificates/generate/enr-1",
                _token("host-1", role="host"),
            ),
            env,
            "enr-1",
        )

        assert response.status == 200
        assert _parse(response)["data"]["url"].startswith("/certificate.html?uuid=")
        insert_stmt.bind.return_value.run.assert_awaited_once()

    async def test_incomplete_enrollment_is_rejected(self):
        env = make_env(
            db=MockDB(
                [
                    make_stmt(first=_enrollment(status="active")),
                    make_stmt(first=None),
                ]
            )
        )

        response = await worker.api_generate_certificate(
            _request(
                "POST",
                "/api/certificates/generate/enr-1",
                _token("learner-1"),
            ),
            env,
            "enr-1",
        )

        assert response.status == 400
        assert "not completed" in _parse(response)["error"]

    async def test_cancelled_enrollment_is_rejected(self):
        env = make_env(db=MockDB([make_stmt(first=_enrollment(status="cancelled"))]))

        response = await worker.api_generate_certificate(
            _request(
                "POST",
                "/api/certificates/generate/enr-1",
                _token("learner-1"),
            ),
            env,
            "enr-1",
        )

        assert response.status == 400
        assert _parse(response)["error"] == "Enrollment is cancelled"

    async def test_repeated_generation_returns_existing_certificate_without_insert(self):
        existing_id = "certificate-existing"
        insert_stmt = make_stmt()
        env = make_env(
            db=MockDB(
                [
                    make_stmt(first=_enrollment()),
                    make_stmt(first=MockRow(id=existing_id)),
                    insert_stmt,
                ]
            )
        )

        response = await worker.api_generate_certificate(
            _request(
                "POST",
                "/api/certificates/generate/enr-1",
                _token("learner-1"),
            ),
            env,
            "enr-1",
        )

        body = _parse(response)
        assert response.status == 200
        assert body["data"] == {
            "uuid": existing_id,
            "url": f"/certificate.html?uuid={existing_id}",
        }
        assert insert_stmt.bind.return_value.run.await_count == 0


class TestPublicCertificateVerification:
    async def test_valid_certificate_returns_certificate_page_fields(self):
        row = MockRow(
            id="certificate-1",
            enrollment_id="enr-1",
            issued_at="2026-11-08 12:00:00",
            student_name_enc=_enc("Ada Lovelace"),
            activity_title="Introduction to Python",
        )
        env = make_env(db=MockDB([make_stmt(first=row)]))

        response = await worker.api_get_certificate(
            _request("GET", "/api/certificates/certificate-1"),
            env,
            "certificate-1",
        )

        body = _parse(response)
        data = body["data"]
        assert response.status == 200
        assert data["uuid"] == "certificate-1"
        assert data["student_name"] == "Ada Lovelace"
        assert data["activity_title"] == "Introduction to Python"
        assert data["issued_at"] == "2026-11-08 12:00:00"
        assert data["enrollment_id"] == "enr-1"
        assert "password" not in data
        assert "token" not in data
        assert "password_hash" not in data
        assert "credential" not in data

    async def test_invalid_certificate_uuid_returns_not_found(self):
        env = make_env(db=MockDB([make_stmt(first=None)]))

        response = await worker.api_get_certificate(
            _request("GET", "/api/certificates/not-a-uuid"),
            env,
            "not-a-uuid",
        )

        assert response.status == 404
        assert _parse(response)["error"] == "Certificate not found"

    async def test_unknown_certificate_uuid_returns_not_found(self):
        env = make_env(db=MockDB([make_stmt(first=None)]))

        response = await worker.api_get_certificate(
            _request("GET", "/api/certificates/00000000-0000-4000-8000-000000000000"),
            env,
            "00000000-0000-4000-8000-000000000000",
        )

        assert response.status == 404
        assert _parse(response)["error"] == "Certificate not found"
