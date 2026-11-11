import json
import pytest
from src import worker
from tests.helpers import MockDB, MockRequest, MockRow, json_request, make_env, make_stmt

JWT = "test-jwt-secret"


def _make_token(uid="usr-1", username="alice", role="member"):
    return worker.create_token(uid, username, role, JWT)


def _parse(resp):
    return json.loads(resp.body)


class TestPeerConnections:
    def _req(self, method, url, payload=None, token=None):
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if payload is not None:
            return json_request(url, payload, headers=headers, method=method)
        return MockRequest(method=method, url=f"http://localhost{url}", headers=headers)

    async def test_send_request_unauthenticated(self):
        env = make_env()
        r = await worker.api_send_peer_request(
            self._req("POST", "/api/peers/request", {"recipient_id": "usr-2", "activity_id": "act-1"}),
            env,
        )
        assert r.status == 401

    async def test_send_request_missing_fields(self):
        token = _make_token(uid="usr-1")
        env = make_env()
        r = await worker.api_send_peer_request(
            self._req("POST", "/api/peers/request", {"recipient_id": ""}, token=token),
            env,
        )
        assert r.status == 400
        assert "required" in _parse(r)["error"]

    async def test_send_request_to_self(self):
        token = _make_token(uid="usr-1")
        env = make_env()
        r = await worker.api_send_peer_request(
            self._req("POST", "/api/peers/request", {"recipient_id": "usr-1", "activity_id": "act-1"}, token=token),
            env,
        )
        assert r.status == 400
        assert "yourself" in _parse(r)["error"]

    async def test_send_request_activity_not_found(self):
        token = _make_token(uid="usr-1")
        env = make_env(db=MockDB([
            make_stmt(first=None),
        ]))
        r = await worker.api_send_peer_request(
            self._req("POST", "/api/peers/request", {"recipient_id": "usr-2", "activity_id": "act-bad"}, token=token),
            env,
        )
        assert r.status == 404

    async def test_send_request_sender_not_enrolled(self):
        token = _make_token(uid="usr-1")
        env = make_env(db=MockDB([
            make_stmt(first=MockRow(id="act-1")),
            make_stmt(first=None),
            make_stmt(first=None),
        ]))
        r = await worker.api_send_peer_request(
            self._req("POST", "/api/peers/request", {"recipient_id": "usr-2", "activity_id": "act-1"}, token=token),
            env,
        )
        assert r.status == 403
        assert "enrolled" in _parse(r)["error"].lower()

    async def test_send_request_recipient_not_enrolled(self):
        token = _make_token(uid="usr-1")
        env = make_env(db=MockDB([
            make_stmt(first=MockRow(id="act-1")),
            make_stmt(first=MockRow(id="enr-1")),
            make_stmt(first=None),
            make_stmt(first=None),
            make_stmt(first=None),
        ]))
        r = await worker.api_send_peer_request(
            self._req("POST", "/api/peers/request", {"recipient_id": "usr-2", "activity_id": "act-1"}, token=token),
            env,
        )
        assert r.status == 403
        assert "not part of" in _parse(r)["error"].lower()

    async def test_send_request_recipient_disallows_buddy_requests(self):
        token = _make_token(uid="usr-1")
        env = make_env(db=MockDB([
            make_stmt(first=MockRow(id="act-1")),
            make_stmt(first=MockRow(id="enr-1")),
            make_stmt(first=None),
            make_stmt(first=MockRow(id="enr-2")),
            make_stmt(first=None),
            make_stmt(first=MockRow(allow_buddy_requests=0)),
        ]))
        r = await worker.api_send_peer_request(
            self._req("POST", "/api/peers/request", {"recipient_id": "usr-2", "activity_id": "act-1"}, token=token),
            env,
        )
        assert r.status == 403
        assert "not accepting buddy requests" in _parse(r)["error"].lower()

    async def test_send_request_success(self):
        token = _make_token(uid="usr-1")
        env = make_env(db=MockDB([
            make_stmt(first=MockRow(id="act-1")),
            make_stmt(first=MockRow(id="enr-1")),
            make_stmt(first=None),
            make_stmt(first=MockRow(id="enr-2")),
            make_stmt(first=None),
            make_stmt(first=MockRow(allow_buddy_requests=1)),
            make_stmt(first=MockRow(cnt=0)),
            make_stmt(first=None),
            make_stmt(),
            make_stmt(first=MockRow(name="Alice", username="alice")),
            make_stmt(),
            make_stmt(),
        ]))
        r = await worker.api_send_peer_request(
            self._req("POST", "/api/peers/request", {"recipient_id": "usr-2", "activity_id": "act-1"}, token=token),
            env,
        )
        assert r.status == 200
        data = _parse(r)
        assert data["data"]["status"] == "pending"
        assert data["data"]["id"]

    async def test_send_request_already_connected(self):
        token = _make_token(uid="usr-1")
        env = make_env(db=MockDB([
            make_stmt(first=MockRow(id="act-1")),
            make_stmt(first=MockRow(id="enr-1")),
            make_stmt(first=None),
            make_stmt(first=MockRow(id="enr-2")),
            make_stmt(first=None),
            make_stmt(first=MockRow(allow_buddy_requests=1)),
            make_stmt(first=MockRow(cnt=0)),
            make_stmt(first=MockRow(id="conn-1", status="accepted")),
        ]))
        r = await worker.api_send_peer_request(
            self._req("POST", "/api/peers/request", {"recipient_id": "usr-2", "activity_id": "act-1"}, token=token),
            env,
        )
        assert r.status == 409

    async def test_send_request_rate_limited(self):
        token = _make_token(uid="usr-1")
        env = make_env(db=MockDB([
            make_stmt(first=MockRow(id="act-1")),
            make_stmt(first=MockRow(id="enr-1")),
            make_stmt(first=None),
            make_stmt(first=MockRow(id="enr-2")),
            make_stmt(first=None),
            make_stmt(first=MockRow(allow_buddy_requests=1)),
            make_stmt(first=MockRow(cnt=10)),
        ]))
        r = await worker.api_send_peer_request(
            self._req("POST", "/api/peers/request", {"recipient_id": "usr-2", "activity_id": "act-1"}, token=token),
            env,
        )
        assert r.status == 429

    async def test_respond_unauthenticated(self):
        env = make_env()
        r = await worker.api_respond_peer_request(
            self._req("PATCH", "/api/peers/conn-1/respond", {"action": "accept"}),
            env, "conn-1",
        )
        assert r.status == 401

    async def test_respond_invalid_action(self):
        token = _make_token(uid="usr-2")
        env = make_env()
        r = await worker.api_respond_peer_request(
            self._req("PATCH", "/api/peers/conn-1/respond", {"action": "block"}, token=token),
            env, "conn-1",
        )
        assert r.status == 400

    async def test_respond_not_found(self):
        token = _make_token(uid="usr-2")
        env = make_env(db=MockDB([
            make_stmt(first=None),
        ]))
        r = await worker.api_respond_peer_request(
            self._req("PATCH", "/api/peers/conn-1/respond", {"action": "accept"}, token=token),
            env, "conn-1",
        )
        assert r.status == 404

    async def test_respond_accept(self):
        token = _make_token(uid="usr-2")
        env = make_env(db=MockDB([
            make_stmt(first=MockRow(id="conn-1", sender_id="usr-1")),
            make_stmt(),
            make_stmt(first=MockRow(name="Bob", username="bob")),
            make_stmt(),
            make_stmt(),
        ]))
        r = await worker.api_respond_peer_request(
            self._req("PATCH", "/api/peers/conn-1/respond", {"action": "accept"}, token=token),
            env, "conn-1",
        )
        assert r.status == 200
        data = _parse(r)
        assert data["data"]["status"] == "accepted"

    async def test_respond_decline(self):
        token = _make_token(uid="usr-2")
        env = make_env(db=MockDB([
            make_stmt(first=MockRow(id="conn-1", sender_id="usr-1")),
            make_stmt(),
        ]))
        r = await worker.api_respond_peer_request(
            self._req("PATCH", "/api/peers/conn-1/respond", {"action": "decline"}, token=token),
            env, "conn-1",
        )
        assert r.status == 200
        data = _parse(r)
        assert data["data"]["status"] == "declined"

    async def test_list_unauthenticated(self):
        env = make_env()
        r = await worker.api_list_peer_connections(
            self._req("GET", "/api/peers"), env,
        )
        assert r.status == 401

    async def test_list_empty(self):
        token = _make_token(uid="usr-1")
        env = make_env(db=MockDB([
            make_stmt(all_results=[]),
            make_stmt(all_results=[]),
        ]))
        r = await worker.api_list_peer_connections(
            self._req("GET", "/api/peers", token=token), env,
        )
        assert r.status == 200
        data = _parse(r)
        assert data["data"]["connections"] == []
        assert data["data"]["pending"] == []

    async def test_list_with_connections(self):
        token = _make_token(uid="usr-1")
        conn_row = MockRow(id="conn-1", sender_id="usr-1", recipient_id="usr-2", activity_id="act-1", created_at="2026-01-01")
        env = make_env(db=MockDB([
            make_stmt(all_results=[conn_row]),
            make_stmt(first=MockRow(name="Bob", username="bob")),
            make_stmt(first=MockRow(title="Python 101")),
            make_stmt(all_results=[]),
        ]))
        r = await worker.api_list_peer_connections(
            self._req("GET", "/api/peers", token=token), env,
        )
        assert r.status == 200
        data = _parse(r)
        assert len(data["data"]["connections"]) == 1
        assert data["data"]["connections"][0]["display_name"] == "Bob"
        assert data["data"]["connections"][0]["activity_title"] == "Python 101"

    async def test_status_unauthenticated(self):
        env = make_env()
        r = await worker.api_peer_connection_status(
            self._req("GET", "/api/peers/status/usr-2"), env, "usr-2",
        )
        assert r.status == 401

    async def test_status_none(self):
        token = _make_token(uid="usr-1")
        env = make_env(db=MockDB([
            make_stmt(first=MockRow(allow_buddy_requests=0)),
            make_stmt(first=None),
        ]))
        r = await worker.api_peer_connection_status(
            self._req("GET", "/api/peers/status/usr-2", token=token), env, "usr-2",
        )
        assert r.status == 200
        data = _parse(r)
        assert data["data"]["status"] == "none"
        assert data["data"]["allow_buddy_requests"] is False

    async def test_status_connected(self):
        token = _make_token(uid="usr-1")
        env = make_env(db=MockDB([
            make_stmt(first=MockRow(allow_buddy_requests=1)),
            make_stmt(first=MockRow(id="conn-1", status="accepted", sender_id="usr-1", recipient_id="usr-2")),
        ]))
        r = await worker.api_peer_connection_status(
            self._req("GET", "/api/peers/status/usr-2", token=token), env, "usr-2",
        )
        assert r.status == 200
        data = _parse(r)
        assert data["data"]["status"] == "accepted"
        assert data["data"]["is_sender"] is True
        assert data["data"]["allow_buddy_requests"] is True

    async def test_delete_connection_unauthenticated(self):
        env = make_env()
        r = await worker.api_delete_peer_connection(
            self._req("DELETE", "/api/peers/conn-1"), env, "conn-1"
        )
        assert r.status == 401

    async def test_delete_connection_not_found(self):
        token = _make_token(uid="usr-1")
        env = make_env(db=MockDB([
            make_stmt(first=None),
        ]))
        r = await worker.api_delete_peer_connection(
            self._req("DELETE", "/api/peers/conn-1", token=token), env, "conn-1"
        )
        assert r.status == 404

    async def test_delete_connection_success(self):
        token = _make_token(uid="usr-1")
        env = make_env(db=MockDB([
            make_stmt(first=MockRow(id="conn-1", sender_id="usr-1", recipient_id="usr-2")),
            make_stmt(),
        ]))
        r = await worker.api_delete_peer_connection(
            self._req("DELETE", "/api/peers/conn-1", token=token), env, "conn-1"
        )
        assert r.status == 200
        data = _parse(r)
        assert data["data"]["deleted"] is True

    async def test_send_peer_request_by_email_success(self):
        token = _make_token(uid="usr-1")
        target_user = MockRow(id="usr-2")
        target_prof = MockRow(allow_email_buddy_requests=1)
        sender_row = MockRow(name="Alice", username="alice")
        env = make_env(db=MockDB([
            make_stmt(first=MockRow(cnt=0)),    # rate limit check
            make_stmt(first=target_user),       # lookup target user
            make_stmt(first=target_prof),       # lookup target profile
            make_stmt(first=None),              # check existing connection
            make_stmt(),                        # insert peer connection
            make_stmt(first=sender_row),        # resolve sender display name
            make_stmt(),                        # create notification
        ]))
        r = await worker.api_send_peer_request(
            self._req("POST", "/api/peers/request", {"email": "bob@example.com"}, token=token),
            env,
        )
        assert r.status == 200
        data = _parse(r)
        assert data["message"] == "We will send a request if that user exists"

    async def test_send_peer_request_by_email_target_toggle_off(self):
        token = _make_token(uid="usr-1")
        target_user = MockRow(id="usr-2")
        target_prof = MockRow(allow_email_buddy_requests=0) # toggle off!
        env = make_env(db=MockDB([
            make_stmt(first=MockRow(cnt=0)),    # rate limit check
            make_stmt(first=target_user),       # lookup target user
            make_stmt(first=target_prof),       # lookup target profile
        ]))
        r = await worker.api_send_peer_request(
            self._req("POST", "/api/peers/request", {"email": "bob@example.com"}, token=token),
            env,
        )
        assert r.status == 200
        data = _parse(r)
        # Does not confirm whether sent or user exists:
        assert data["message"] == "We will send a request if that user exists"

    async def test_send_peer_request_by_email_nonexistent_user(self):
        token = _make_token(uid="usr-1")
        env = make_env(db=MockDB([
            make_stmt(first=MockRow(cnt=0)),    # rate limit check
            make_stmt(first=None),              # user lookup returns none
        ]))
        r = await worker.api_send_peer_request(
            self._req("POST", "/api/peers/request", {"email": "unknown@example.com"}, token=token),
            env,
        )
        assert r.status == 200
        data = _parse(r)
        assert data["message"] == "We will send a request if that user exists"

    async def test_send_peer_request_by_email_self(self):
        token = _make_token(uid="usr-1")
        env = make_env(db=MockDB([
            make_stmt(first=MockRow(cnt=0)),    # rate limit check
            make_stmt(first=MockRow(id="usr-1")), # lookup returns self
        ]))
        r = await worker.api_send_peer_request(
            self._req("POST", "/api/peers/request", {"email": "myself@example.com"}, token=token),
            env,
        )
        assert r.status == 200
        data = _parse(r)
        assert data["message"] == "We will send a request if that user exists"

    async def test_send_peer_request_by_email_rate_limited(self):
        token = _make_token(uid="usr-1")
        env = make_env(db=MockDB([
            make_stmt(first=MockRow(cnt=10)),    # rate limit exceeded
        ]))
        r = await worker.api_send_peer_request(
            self._req("POST", "/api/peers/request", {"email": "target@example.com"}, token=token),
            env,
        )
        assert r.status == 429
        assert "Rate limit" in _parse(r)["error"]

    async def test_profile_patch_allow_email_buddy_requests(self):
        token = _make_token(uid="usr-1")
        env = make_env(db=MockDB([
            make_stmt(), # ensure user profile
            make_stmt(), # update user_profiles SET allow_email_buddy_requests=?
        ]))
        r = await worker.api_profile(
            self._req("PATCH", "/api/profile", {"allow_email_buddy_requests": True}, token=token),
            env,
        )
        assert r.status == 200
        data = _parse(r)
        assert data["data"]["allow_email_buddy_requests"] is True

