# Unit tests for privacy-first direct messaging
import json
import pytest
from src import worker
from tests.helpers import MockDB, MockRequest, MockRow, json_request, make_env, make_stmt

JWT = "test-jwt-secret"

def _make_token(uid="usr-1", username="alice", role="member"):
    return worker.create_token(uid, username, role, JWT)

def _parse(resp):
    return json.loads(resp.body)


class TestMessagingEndpoints:
    def _req(self, method, url, payload=None, token=None):
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if payload is not None:
            return json_request(url, payload, headers=headers, method=method)
        return MockRequest(method=method, url=f"http://localhost{url}", headers=headers)

    async def test_send_request_unauthenticated_returns_401(self):
        env = make_env()
        r = await worker.api_send_message_request(self._req("POST", "/api/messages/request", {"email": "a@b.com"}), env)
        assert r.status == 401

    async def test_send_request_nonexistent_email_returns_neutral_response(self):
        token = _make_token(uid="usr-sender")
        env = make_env(db=MockDB([
            make_stmt(first=MockRow(cnt=0)),  # rate limit check
            make_stmt(first=None),             # target user lookup
        ]))
        r = await worker.api_send_message_request(self._req("POST", "/api/messages/request", {"email": "unknown@example.com"}, token=token), env)
        assert r.status == 200
        data = _parse(r)
        assert "We'll let the other person know" in data["message"]

    async def test_send_request_rate_limited(self):
        token = _make_token(uid="usr-sender")
        env = make_env(db=MockDB([
            make_stmt(first=MockRow(cnt=5)),  # 5 requests already
        ]))
        r = await worker.api_send_message_request(self._req("POST", "/api/messages/request", {"email": "target@example.com"}, token=token), env)
        assert r.status == 429

    async def test_respond_to_request_accept(self):
        token = _make_token(uid="usr-target")
        req_row = MockRow(id="req-1", from_user_id="usr-sender")
        env = make_env(db=MockDB([
            make_stmt(first=req_row),  # SELECT request
            make_stmt(),               # UPDATE request status
        ]))
        r = await worker.api_respond_to_message_request(
            self._req("PATCH", "/api/messages/request/req-1", {"action": "accept"}, token=token),
            env, "req-1"
        )
        assert r.status == 200
        data = _parse(r)
        assert data["data"]["status"] == "accepted"

    async def test_list_message_requests(self):
        token = _make_token(uid="usr-target")
        rows = [MockRow(id="req-1", from_user_id="usr-sender", created_at="2026-01-01", source="email", activity_id=None)]
        sender_row = MockRow(name="Sender Name", username="sender")
        env = make_env(db=MockDB([
            make_stmt(all_results=rows),
            make_stmt(first=sender_row),
        ]))
        r = await worker.api_list_message_requests(self._req("GET", "/api/messages/requests", token=token), env)
        assert r.status == 200
        data = _parse(r)
        assert len(data["data"]["requests"]) == 1
        assert data["data"]["requests"][0]["id"] == "req-1"
        assert data["data"]["requests"][0]["from_user_name"] == "Sender Name"

    async def test_list_message_threads(self):
        token = _make_token(uid="usr-1")
        threads_rows = [MockRow(id="th-1", from_user_id="usr-1", to_user_id="usr-2", created_at="2026-01-01", source="email", activity_id=None)]
        other_user = MockRow(name="Bob Martinez", username="bob")
        env = make_env(db=MockDB([
            make_stmt(all_results=threads_rows),
            make_stmt(first=other_user),
        ]))
        r = await worker.api_list_message_threads(self._req("GET", "/api/messages/threads", token=token), env)
        assert r.status == 200
        data = _parse(r)
        assert len(data["data"]["threads"]) == 1
        assert data["data"]["threads"][0]["other_user_name"] == "Bob Martinez"

    async def test_send_thread_message(self):
        token = _make_token(uid="usr-1")
        thread_row = MockRow(id="th-1", from_user_id="usr-1", to_user_id="usr-2", status="accepted")
        env = make_env(db=MockDB([
            make_stmt(first=thread_row),  # SELECT thread
            make_stmt(),                   # INSERT legacy_records
            make_stmt(),                   # notification
        ]))
        r = await worker.api_send_thread_message(
            self._req("POST", "/api/messages/threads/th-1/send", {"message": "Hello!"}, token=token),
            env, "th-1"
        )
        assert r.status == 200
        data = _parse(r)
        assert data["data"]["content"] == "Hello!"

