"""
Unit tests for PresenceDO.

Stubs are installed by conftest.py before any test file imports worker.py.
All WebSocket interactions use unittest.mock.MagicMock so no real runtime
primitives are needed.
"""

import base64
import json
from types import SimpleNamespace
import pytest
from unittest.mock import MagicMock, AsyncMock

from tests.helpers import load_worker, make_env, MockRequest, MockRow, make_stmt, MockDB

worker = load_worker()


# ---------------------------------------------------------------------------
# Helpers: fake ctx / ws / request objects
# ---------------------------------------------------------------------------

def _make_ctx(sockets=None):
    ctx = MagicMock()
    ctx.getWebSockets.return_value = sockets or []
    ctx.setWebSocketAutoResponse.return_value = None
    ctx.acceptWebSocket.return_value = None
    return ctx


def _make_ws(attachment=None):
    """Return a MagicMock WebSocket with optional serialized attachment."""
    ws = MagicMock()
    ws.deserializeAttachment.return_value = (
        json.dumps(attachment) if attachment else None
    )
    ws.serializeAttachment.return_value = None
    ws.send.return_value = None
    return ws


def _make_presence_env(*, allow_anon="true", jwt_secret="test-jwt-secret"):
    env = make_env(jwt_secret=jwt_secret)
    env.ALLOW_ANON_PRESENCE = allow_anon
    return env


def _make_request(path="ws://localhost/api/presence/room1",
                  upgrade="websocket",
                  token=None, user_id=None, display_name=None):
    """Build a minimal fake request object."""
    qs_parts = []
    if token:
        qs_parts.append(f"token={token}")
    if user_id:
        qs_parts.append(f"user_id={user_id}")
    if display_name:
        qs_parts.append(f"display_name={display_name}")
    qs = "&".join(qs_parts)
    url = f"{path}{'?' + qs if qs else ''}"

    req = MagicMock()
    req.url = url
    req.headers = MagicMock()
    req.headers.get = lambda k, d=None: upgrade if k == "Upgrade" else d
    return req


def _make_presence_do(allow_anon="true"):
    """Return a fresh PresenceDO with no prior sessions."""
    ctx = _make_ctx()
    env = _make_presence_env(allow_anon=allow_anon)
    return worker.PresenceDO(ctx, env)


# ===========================================================================
# 1.  Constructor / hibernation restore
# ===========================================================================

class TestPresenceDOInit:
    def test_empty_init(self):
        do = _make_presence_do()
        assert do.sessions == {}
        assert do.presence == {}

    def test_restores_hibernated_socket(self):
        attachment = {
            "session_id":   "sid-1",
            "user_id":      "alice",
            "display_name": "Alice",
            "x": 0.3, "y": 0.7, "emoji": "👋", "hand_raised": True,
        }
        ws  = _make_ws(attachment=attachment)
        ctx = _make_ctx(sockets=[ws])
        do  = worker.PresenceDO(ctx, _make_presence_env())

        assert "sid-1" in do.sessions
        assert do.presence["alice"]["x"] == pytest.approx(0.3)
        assert do.presence["alice"]["hand_raised"] is True

    def test_skips_socket_with_no_attachment(self):
        ws  = _make_ws(attachment=None)
        ctx = _make_ctx(sockets=[ws])
        do  = worker.PresenceDO(ctx, _make_presence_env())
        assert do.sessions == {}
        assert do.presence == {}

    def test_does_not_overwrite_existing_presence_on_restore(self):
        """If two sockets belong to the same user, presence is only set once."""
        att1 = {"session_id": "s1", "user_id": "alice", "display_name": "Alice",
                "x": 0.1, "y": 0.1, "emoji": "", "hand_raised": False}
        att2 = {"session_id": "s2", "user_id": "alice", "display_name": "Alice",
                "x": 0.9, "y": 0.9, "emoji": "", "hand_raised": True}
        ws1, ws2 = _make_ws(att1), _make_ws(att2)
        ctx = _make_ctx(sockets=[ws1, ws2])
        do  = worker.PresenceDO(ctx, _make_presence_env())

        # First socket wins for the presence record
        assert do.presence["alice"]["x"] == pytest.approx(0.1)


# ===========================================================================
# 2.  on_fetch – WebSocket upgrade
# ===========================================================================

class TestPresenceDOOnFetch:
    async def test_rejects_non_websocket(self):
        do  = _make_presence_do()
        req = _make_request(upgrade="")
        resp = await do.on_fetch(req)
        assert resp.status == 426

    async def test_rejects_unauthenticated_when_anon_disabled(self):
        do  = _make_presence_do(allow_anon="false")
        req = _make_request(upgrade="websocket")  # no token, no user_id
        resp = await do.on_fetch(req)
        assert resp.status == 401

    async def test_rejects_when_anon_disabled_even_with_user_id(self):
        do  = _make_presence_do(allow_anon="false")
        req = _make_request(upgrade="websocket", user_id="bob")
        resp = await do.on_fetch(req)
        assert resp.status == 401

    async def test_accepts_anon_join(self):
        do  = _make_presence_do(allow_anon="true")
        req = _make_request(upgrade="websocket", user_id="bob", display_name="Bob")
        resp = await do.on_fetch(req)
        assert resp.status == 101
        assert len(do.sessions) == 1
        assert "bob" in do.presence

    async def test_authenticated_join_uses_token_identity(self):
        env = _make_presence_env(allow_anon="false")
        ctx = _make_ctx()
        do = worker.PresenceDO(ctx, env)
        token = worker.create_token("token-user", "TokenName", "student", env.JWT_SECRET)
        req = _make_request(
            upgrade="websocket",
            token=token,
            user_id="query-user",
            display_name="QueryName",
        )
        resp = await do.on_fetch(req)
        assert resp.status == 101
        assert "token-user" in do.presence
        assert "query-user" not in do.presence
        assert do.presence["token-user"]["display_name"] == "TokenName"

    async def test_rejects_empty_user_from_token(self):
        env = _make_presence_env(allow_anon="false")
        ctx = _make_ctx()
        do = worker.PresenceDO(ctx, env)
        token = worker.create_token("", "NoId", "student", env.JWT_SECRET)
        req = _make_request(upgrade="websocket", token=token)
        resp = await do.on_fetch(req)
        assert resp.status == 400

    async def test_welcome_message_contains_full_state(self):
        do = _make_presence_do()
        # Pre-populate an existing user
        do.presence["old-user"] = {
            "x": 0.1, "y": 0.9, "emoji": "", "hand_raised": False,
            "display_name": "Old",
        }

        req = _make_request(upgrade="websocket", user_id="newbie", display_name="Newbie")
        await do.on_fetch(req)

        sid = next(iter(do.sessions))
        server_ws = do.sessions[sid]["ws"]
        welcome = json.loads(server_ws.send.call_args_list[0][0][0])
        assert welcome["type"] == "welcome"
        assert "old-user" in welcome["state"]
        assert "newbie"   in welcome["state"]

    async def test_second_join_broadcasts_delta_to_first(self):
        do = _make_presence_do()

        await do.on_fetch(_make_request(upgrade="websocket", user_id="alice", display_name="Alice"))
        alice_sid = next(iter(do.sessions))
        alice_ws  = do.sessions[alice_sid]["ws"]
        alice_ws.send.reset_mock()

        await do.on_fetch(_make_request(upgrade="websocket", user_id="bob", display_name="Bob"))

        calls = [json.loads(c[0][0]) for c in alice_ws.send.call_args_list]
        assert any(c.get("type") == "delta" and c.get("user_id") == "bob"
                   for c in calls)

    async def test_user_id_sanitised_to_64_chars(self):
        do  = _make_presence_do()
        uid = "a" * 100
        await do.on_fetch(_make_request(upgrade="websocket", user_id=uid))
        assert uid[:64] in do.presence
        assert uid not in do.presence  # raw 100-char uid must not exist

    async def test_display_name_sanitised_to_64_chars(self):
        do = _make_presence_do()
        dname = "b" * 100
        await do.on_fetch(_make_request(upgrade="websocket", user_id="alice", display_name=dname))
        assert do.presence["alice"]["display_name"] == dname[:64]

    async def test_same_user_can_have_multiple_sessions(self):
        """Multi-tab: same user_id, two independent WS connections."""
        do = _make_presence_do()
        for _ in range(2):
            await do.on_fetch(
                _make_request(upgrade="websocket", user_id="alice", display_name="Alice")
            )
        alice_sessions = [s for s in do.sessions.values() if s["user_id"] == "alice"]
        assert len(alice_sessions) == 2
        # Presence has only one record for alice
        assert list(do.presence.keys()).count("alice") == 1


# ===========================================================================
# 3.  on_webSocketMessage – presence updates
# ===========================================================================

class TestPresenceDOMessage:
    async def _setup_user(self, user_id="alice", display_name="Alice"):
        """Helper: create DO, join one user, and return (do, session_id, ws)."""
        do  = _make_presence_do()
        req = _make_request(upgrade="websocket", user_id=user_id, display_name=display_name)
        await do.on_fetch(req)
        sid = next(s for s, info in do.sessions.items() if info["user_id"] == user_id)
        ws  = do.sessions[sid]["ws"]
        # Teach the fake ws to return its own attachment via deserializeAttachment
        ws.deserializeAttachment.return_value = json.dumps({
            "session_id": sid, "user_id": user_id, "display_name": display_name,
            "x": 0.5, "y": 0.5, "emoji": "", "hand_raised": False,
        })
        return do, sid, ws

    async def test_position_update_changes_presence(self):
        do, sid, ws = await self._setup_user()
        await do.on_webSocketMessage(ws, json.dumps({"type": "presence", "x": 0.8, "y": 0.2}))
        assert do.presence["alice"]["x"] == pytest.approx(0.8)
        assert do.presence["alice"]["y"] == pytest.approx(0.2)

    async def test_only_x_changed(self):
        """Sending only x must not modify y."""
        do, sid, ws = await self._setup_user()
        await do.on_webSocketMessage(ws, json.dumps({"type": "presence", "x": 0.9}))
        assert do.presence["alice"]["x"] == pytest.approx(0.9)
        assert do.presence["alice"]["y"] == pytest.approx(0.5)  # unchanged

    async def test_no_broadcast_on_no_change(self):
        """If nothing actually changed, skip broadcast entirely."""
        do, _sid, ws = await self._setup_user()
        ws.send.reset_mock()
        # Send the same values that are already stored (defaults)
        await do.on_webSocketMessage(ws, json.dumps({"type": "presence", "x": 0.5, "y": 0.5}))
        ws.send.assert_not_called()

    async def test_position_clamped_to_01(self):
        do, _sid, ws = await self._setup_user()
        await do.on_webSocketMessage(ws, json.dumps({"type": "presence", "x": 99.0, "y": -5.0}))
        assert do.presence["alice"]["x"] == pytest.approx(1.0)
        assert do.presence["alice"]["y"] == pytest.approx(0.0)

    async def test_emoji_update(self):
        do, _sid, ws = await self._setup_user()
        await do.on_webSocketMessage(ws, json.dumps({"type": "presence", "emoji": "🎉"}))
        assert do.presence["alice"]["emoji"] == "🎉"

    async def test_emoji_cleared(self):
        do, sid, ws = await self._setup_user()
        do.presence["alice"]["emoji"] = "🎉"
        # Reset attachment to reflect current emoji
        ws.deserializeAttachment.return_value = json.dumps({
            "session_id": sid, "user_id": "alice", "display_name": "Alice",
            "x": 0.5, "y": 0.5, "emoji": "🎉", "hand_raised": False,
        })
        await do.on_webSocketMessage(ws, json.dumps({"type": "presence", "emoji": ""}))
        assert do.presence["alice"]["emoji"] == ""

    async def test_hand_raised_toggle(self):
        do, sid, ws = await self._setup_user()
        await do.on_webSocketMessage(ws, json.dumps({"type": "presence", "hand_raised": True}))
        assert do.presence["alice"]["hand_raised"] is True
        # Update attachment to reflect raised state
        ws.deserializeAttachment.return_value = json.dumps({
            "session_id": sid, "user_id": "alice", "display_name": "Alice",
            "x": 0.5, "y": 0.5, "emoji": "", "hand_raised": True,
        })
        await do.on_webSocketMessage(ws, json.dumps({"type": "presence", "hand_raised": False}))
        assert do.presence["alice"]["hand_raised"] is False

    async def test_non_bool_hand_raised_ignored(self):
        do, _sid, ws = await self._setup_user()
        ws.send.reset_mock()
        await do.on_webSocketMessage(ws, json.dumps({"type": "presence", "hand_raised": "yes"}))
        # hand_raised must stay False (non-bool rejected)
        assert do.presence["alice"]["hand_raised"] is False
        ws.send.assert_not_called()

    async def test_join_message_returns_welcome(self):
        do, _sid, ws = await self._setup_user()
        ws.send.reset_mock()
        await do.on_webSocketMessage(ws, json.dumps({"type": "join"}))
        call = json.loads(ws.send.call_args_list[0][0][0])
        assert call["type"] == "welcome"
        assert "alice" in call["state"]

    async def test_oversized_message_ignored(self):
        do, _sid, ws = await self._setup_user()
        ws.send.reset_mock()
        big = json.dumps({"type": "presence", "x": 0.1, "data": "A" * 600})
        await do.on_webSocketMessage(ws, big)
        # Presence must NOT change
        assert do.presence["alice"]["x"] == pytest.approx(0.5)

    async def test_invalid_json_ignored(self):
        do, sid, ws = await self._setup_user()
        ws.send.reset_mock()
        await do.on_webSocketMessage(ws, "not-json{{")
        ws.send.assert_not_called()

    async def test_non_dict_payload_ignored(self):
        do, sid, ws = await self._setup_user()
        ws.send.reset_mock()
        await do.on_webSocketMessage(ws, json.dumps([1, 2, 3]))
        ws.send.assert_not_called()

    async def test_broadcast_reaches_second_client(self):
        """Delta for alice's move must reach bob but NOT be echoed back to alice."""
        do = _make_presence_do()

        await do.on_fetch(_make_request(upgrade="websocket", user_id="alice", display_name="Alice"))
        alice_sid = next(s for s, i in do.sessions.items() if i["user_id"] == "alice")
        alice_ws  = do.sessions[alice_sid]["ws"]
        alice_ws.deserializeAttachment.return_value = json.dumps({
            "session_id": alice_sid, "user_id": "alice", "display_name": "Alice",
            "x": 0.5, "y": 0.5, "emoji": "", "hand_raised": False,
        })

        await do.on_fetch(_make_request(upgrade="websocket", user_id="bob", display_name="Bob"))
        bob_sid = next(s for s, i in do.sessions.items() if i["user_id"] == "bob")
        bob_ws  = do.sessions[bob_sid]["ws"]

        alice_ws.send.reset_mock()
        bob_ws.send.reset_mock()

        await do.on_webSocketMessage(alice_ws, json.dumps({"type": "presence", "x": 0.1}))

        bob_msgs   = [json.loads(c[0][0]) for c in bob_ws.send.call_args_list]
        alice_msgs = [json.loads(c[0][0]) for c in alice_ws.send.call_args_list]

        assert any(m.get("type") == "delta" and m.get("user_id") == "alice"
                   for m in bob_msgs), "Bob should receive alice's delta"
        assert not any(m.get("type") == "delta" for m in alice_msgs), \
            "Alice should NOT receive her own delta"

    async def test_delta_contains_only_changed_fields(self):
        """Only the changed field (x) should appear in the broadcast delta."""
        do = _make_presence_do()

        await do.on_fetch(_make_request(upgrade="websocket", user_id="alice", display_name="Alice"))
        alice_sid = next(s for s, i in do.sessions.items() if i["user_id"] == "alice")
        alice_ws  = do.sessions[alice_sid]["ws"]
        alice_ws.deserializeAttachment.return_value = json.dumps({
            "session_id": alice_sid, "user_id": "alice", "display_name": "Alice",
            "x": 0.5, "y": 0.5, "emoji": "", "hand_raised": False,
        })

        await do.on_fetch(_make_request(upgrade="websocket", user_id="bob", display_name="Bob"))
        bob_sid = next(s for s, i in do.sessions.items() if i["user_id"] == "bob")
        bob_ws  = do.sessions[bob_sid]["ws"]
        bob_ws.send.reset_mock()

        # Alice moves only in x
        await do.on_webSocketMessage(alice_ws, json.dumps({"type": "presence", "x": 0.9}))

        bob_deltas = [json.loads(c[0][0]) for c in bob_ws.send.call_args_list
                      if json.loads(c[0][0]).get("type") == "delta"]
        assert len(bob_deltas) == 1
        delta = bob_deltas[0]
        assert "x" in delta
        assert "y" not in delta
        assert "emoji" not in delta
        assert "hand_raised" not in delta


# ===========================================================================
# 4.  on_webSocketClose – disconnect / leave
# ===========================================================================

class TestPresenceDODisconnect:
    async def test_single_user_disconnect_clears_presence(self):
        do  = _make_presence_do()
        req = _make_request(upgrade="websocket", user_id="alice", display_name="Alice")
        await do.on_fetch(req)

        sid = next(iter(do.sessions))
        ws  = do.sessions[sid]["ws"]
        ws.deserializeAttachment.return_value = json.dumps({
            "session_id": sid, "user_id": "alice", "display_name": "Alice",
            "x": 0.5, "y": 0.5, "emoji": "", "hand_raised": False,
        })

        await do.on_webSocketClose(ws, 1000, "normal", True)

        assert sid not in do.sessions
        assert "alice" not in do.presence

    async def test_disconnect_broadcasts_leave_to_others(self):
        do = _make_presence_do()

        await do.on_fetch(_make_request(upgrade="websocket", user_id="alice", display_name="Alice"))
        alice_sid = next(s for s, i in do.sessions.items() if i["user_id"] == "alice")
        alice_ws  = do.sessions[alice_sid]["ws"]
        alice_ws.deserializeAttachment.return_value = json.dumps({
            "session_id": alice_sid, "user_id": "alice", "display_name": "Alice",
            "x": 0.5, "y": 0.5, "emoji": "", "hand_raised": False,
        })

        await do.on_fetch(_make_request(upgrade="websocket", user_id="bob", display_name="Bob"))
        bob_sid = next(s for s, i in do.sessions.items() if i["user_id"] == "bob")
        bob_ws  = do.sessions[bob_sid]["ws"]
        bob_ws.send.reset_mock()

        await do.on_webSocketClose(alice_ws, 1000, "normal", True)

        leave_msgs = [json.loads(c[0][0]) for c in bob_ws.send.call_args_list if c[0]]
        assert any(m.get("type") == "leave" and m.get("user_id") == "alice"
                   for m in leave_msgs)

    async def test_multi_tab_not_evicted_until_last_socket_closes(self):
        """Presence stays alive until the very last socket for that user closes."""
        do = _make_presence_do()

        await do.on_fetch(_make_request(upgrade="websocket", user_id="alice", display_name="Alice"))
        await do.on_fetch(_make_request(upgrade="websocket", user_id="alice", display_name="Alice"))

        sids = [s for s, i in do.sessions.items() if i["user_id"] == "alice"]
        assert len(sids) == 2

        # Close first socket
        ws1 = do.sessions[sids[0]]["ws"]
        ws1.deserializeAttachment.return_value = json.dumps({
            "session_id": sids[0], "user_id": "alice", "display_name": "Alice",
            "x": 0.5, "y": 0.5, "emoji": "", "hand_raised": False,
        })
        await do.on_webSocketClose(ws1, 1000, "", True)
        assert "alice" in do.presence  # second tab still open

        # Close second socket
        ws2 = do.sessions[sids[1]]["ws"]
        ws2.deserializeAttachment.return_value = json.dumps({
            "session_id": sids[1], "user_id": "alice", "display_name": "Alice",
            "x": 0.5, "y": 0.5, "emoji": "", "hand_raised": False,
        })
        await do.on_webSocketClose(ws2, 1000, "", True)
        assert "alice" not in do.presence  # now fully gone

    async def test_unknown_ws_on_close_is_safe(self):
        """on_webSocketClose with an unrecognised ws must not raise."""
        do = _make_presence_do()
        orphan_ws = _make_ws()  # not registered in sessions
        await do.on_webSocketClose(orphan_ws, 1000, "", True)  # must not raise


# ===========================================================================
# 5.  Dispatcher – /api/presence/<room_id> route
# ===========================================================================

class TestPresenceDispatch:
    async def test_presence_route_dispatches_to_do(self):
        stub = MagicMock()
        stub.fetch = AsyncMock(return_value=MagicMock(status=101))

        do_ns = MagicMock()
        do_ns.idFromName.return_value = "fake-id"
        do_ns.get.return_value = stub

        env = make_env()
        env.CLASSROOM_DO = MagicMock()
        env.PRESENCE_DO  = do_ns

        req = MagicMock()
        req.method = "GET"
        req.headers = MagicMock()
        req.headers.get = lambda k, d=None: "websocket" if k == "Upgrade" else d
        req.url = "https://example.com/api/presence/room-42?user_id=alice"

        resp = await worker._dispatch(req, env)
        do_ns.idFromName.assert_called_once_with("room-42")
        stub.fetch.assert_awaited_once()

    async def test_invalid_room_id_not_matched(self):
        """Room IDs with special characters must NOT match the route."""
        env = make_env()
        env.CLASSROOM_DO = MagicMock()
        env.PRESENCE_DO  = MagicMock()

        req = MagicMock()
        req.method = "GET"
        req.headers = MagicMock()
        req.headers.get = lambda k, d=None: None
        req.url = "https://example.com/api/presence/room id with spaces"

        # Falls through to static serving → 404 (no static content in mock)
        resp = await worker._dispatch(req, env)
        # PRESENCE_DO must not have been touched
        env.PRESENCE_DO.idFromName.assert_not_called()
        assert resp.status == 404


class TestClassroomDOSignaling:
    """Tests for ClassroomDO WebRTC signaling, media states, and instructor controls."""

    def _make_classroom_do(self, db=None):
        """Helper to instantiate a ClassroomDO with mocked ctx and env."""
        ctx = _make_ctx()
        if db is None:
            db = MagicMock()
            db.prepare = MagicMock(side_effect=lambda sql: make_stmt(first=MockRow(role="instructor")))
        env = make_env(db=db)
        do = worker.ClassroomDO(ctx, env)
        do.room_id = "lobby"
        return do

    def _add_session(self, do, pid, dname="User", sid=None, can_interact=True):
        """Helper to add a session mock to ClassroomDO."""
        sid = sid or f"sid-{pid}"
        attachment = {
            "session_id": sid,
            "participant_id": pid,
            "display_name": dname,
            "position": {"x": 0.5, "y": 0.5},
            "direction": "down",
            "seat_id": "",
            "can_interact": can_interact,
            "media_state": {"audio": False, "video": False, "mic_enabled": False, "cam_enabled": False},
        }
        ws = _make_ws(attachment=attachment)
        do.sessions[sid] = {
            "ws": ws,
            "participant_id": pid,
            "display_name": dname,
            "position": {"x": 0.5, "y": 0.5},
            "direction": "down",
            "is_moving": False,
            "seat_id": "",
            "can_interact": can_interact,
            "media_state": {"audio": False, "video": False, "mic_enabled": False, "cam_enabled": False},
        }
        return ws

    @pytest.mark.asyncio
    async def test_signal_offer_routed_to_target_peer(self):
        """Verify signal_offer is forwarded to target peer."""
        do = self._make_classroom_do()
        ws_alice = self._add_session(do, "alice", "Alice")
        ws_bob   = self._add_session(do, "bob", "Bob")

        offer_payload = {"type": "offer", "sdp": "v=0\r\no=- 1234 2 IN IP4 127.0.0.1\r\n..."}
        msg = json.dumps({
            "type": "signal_offer",
            "target_peer_id": "bob",
            "offer": offer_payload,
        })
        await do.on_webSocketMessage(ws_alice, msg)

        ws_bob.send.assert_called_once()
        sent_data = json.loads(ws_bob.send.call_args[0][0])
        assert sent_data["type"] == "signal_offer"
        assert sent_data["sender_peer_id"] == "alice"
        assert sent_data["target_peer_id"] == "bob"
        assert sent_data["offer"] == offer_payload

    @pytest.mark.asyncio
    async def test_signal_answer_routed_to_target_peer(self):
        """Verify signal_answer is forwarded to target peer."""
        do = self._make_classroom_do()
        ws_alice = self._add_session(do, "alice", "Alice")
        ws_bob   = self._add_session(do, "bob", "Bob")

        answer_payload = {"type": "answer", "sdp": "v=0\r\no=- 5678 2 IN IP4 127.0.0.1\r\n..."}
        msg = json.dumps({
            "type": "signal_answer",
            "target_peer_id": "alice",
            "answer": answer_payload,
        })
        await do.on_webSocketMessage(ws_bob, msg)

        ws_alice.send.assert_called_once()
        sent_data = json.loads(ws_alice.send.call_args[0][0])
        assert sent_data["type"] == "signal_answer"
        assert sent_data["sender_peer_id"] == "bob"
        assert sent_data["target_peer_id"] == "alice"
        assert sent_data["answer"] == answer_payload

    @pytest.mark.asyncio
    async def test_ice_candidate_routed_to_target_peer(self):
        """Verify ice_candidate is forwarded to target peer."""
        do = self._make_classroom_do()
        ws_alice = self._add_session(do, "alice", "Alice")
        ws_bob   = self._add_session(do, "bob", "Bob")

        cand_payload = {"candidate": "candidate:1 1 UDP 2130706431 192.168.1.1 50000 typ host", "sdpMid": "0"}
        msg = json.dumps({
            "type": "ice_candidate",
            "target_peer_id": "bob",
            "candidate": cand_payload,
        })
        await do.on_webSocketMessage(ws_alice, msg)

        ws_bob.send.assert_called_once()
        sent_data = json.loads(ws_bob.send.call_args[0][0])
        assert sent_data["type"] == "ice_candidate"
        assert sent_data["sender_peer_id"] == "alice"
        assert sent_data["candidate"] == cand_payload

    @pytest.mark.asyncio
    async def test_media_state_broadcasts_mic_and_cam(self):
        """Verify media_state updates broadcast to all participants."""
        do = self._make_classroom_do()
        ws_alice = self._add_session(do, "alice", "Alice")
        ws_bob   = self._add_session(do, "bob", "Bob")

        msg = json.dumps({
            "type": "media_state",
            "audio": False,
            "video": True,
        })
        await do.on_webSocketMessage(ws_alice, msg)

        assert do.sessions["sid-alice"]["media_state"]["audio"] is False
        assert do.sessions["sid-alice"]["media_state"]["video"] is True

        for ws in (ws_alice, ws_bob):
            assert any(
                json.loads(call[0][0]).get("type") == "media_state"
                and json.loads(call[0][0]).get("audio") is False
                and json.loads(call[0][0]).get("video") is True
                and json.loads(call[0][0]).get("participant_id") == "alice"
                for call in ws.send.call_args_list
            )

    @pytest.mark.asyncio
    async def test_signaling_to_unknown_target_does_not_raise(self):
        """Assert that an unknown target receives no signaling message."""
        do = self._make_classroom_do()
        ws_alice = self._add_session(do, "alice", "Alice")
        ws_bob = self._add_session(do, "bob", "Bob")

        msg = json.dumps({
            "type": "signal_offer",
            "target_peer_id": "ghost-user",
            "offer": {"type": "offer", "sdp": "v=0..."},
        })
        await do.on_webSocketMessage(ws_alice, msg)
        ws_bob.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_read_only_viewer_cannot_send_signal(self):
        """Verify read-only viewer cannot send signaling messages."""
        do = self._make_classroom_do()
        ws_anon = self._add_session(do, "anon", "Anonymous", can_interact=False)
        ws_bob  = self._add_session(do, "bob", "Bob")

        msg = json.dumps({
            "type": "signal_offer",
            "target_peer_id": "bob",
            "offer": {"type": "offer", "sdp": "v=0..."},
        })
        await do.on_webSocketMessage(ws_anon, msg)
        ws_bob.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_screen_share_only_one_person_allowed(self):
        """Verify only one participant can share screen at a time."""
        do = self._make_classroom_do()
        ws_alice = self._add_session(do, "alice", "Alice")
        ws_bob   = self._add_session(do, "bob", "Bob")

        await do.on_webSocketMessage(ws_alice, json.dumps({
            "type": "start_screen_share",
            "stream_id": "stream-alice",
        }))
        assert do.screen_sharer is not None
        assert do.screen_sharer["participant_id"] == "alice"

        ws_bob.send.reset_mock()
        await do.on_webSocketMessage(ws_bob, json.dumps({
            "type": "start_screen_share",
            "stream_id": "stream-bob",
        }))

        assert do.screen_sharer["participant_id"] == "alice"
        rejected_call = any(
            json.loads(call[0][0]).get("type") == "screen_share_rejected"
            for call in ws_bob.send.call_args_list
        )
        assert rejected_call is True

    @pytest.mark.asyncio
    async def test_screen_share_stopped_broadcast(self):
        """Verify stopping screen share broadcasts screen_share_stopped."""
        do = self._make_classroom_do()
        ws_alice = self._add_session(do, "alice", "Alice")
        ws_bob   = self._add_session(do, "bob", "Bob")

        await do.on_webSocketMessage(ws_alice, json.dumps({
            "type": "start_screen_share",
            "stream_id": "stream-alice",
        }))

        ws_bob.send.reset_mock()
        await do.on_webSocketMessage(ws_alice, json.dumps({
            "type": "stop_screen_share",
        }))

        assert do.screen_sharer is None
        stopped_call = any(
            json.loads(call[0][0]).get("type") == "screen_share_stopped"
            and json.loads(call[0][0]).get("participant_id") == "alice"
            for call in ws_bob.send.call_args_list
        )
        assert stopped_call is True

    @pytest.mark.asyncio
    async def test_disconnect_clears_screen_share(self):
        """Verify disconnect cleans up active screen share."""
        do = self._make_classroom_do()
        ws_alice = self._add_session(do, "alice", "Alice")
        ws_bob   = self._add_session(do, "bob", "Bob")

        await do.on_webSocketMessage(ws_alice, json.dumps({
            "type": "start_screen_share",
            "stream_id": "stream-alice",
        }))

        ws_bob.send.reset_mock()
        await do.on_webSocketClose(ws_alice, 1000, "normal", True)

        assert do.screen_sharer is None
        stopped_call = any(
            json.loads(call[0][0]).get("type") == "screen_share_stopped"
            and json.loads(call[0][0]).get("participant_id") == "alice"
            for call in ws_bob.send.call_args_list
        )
        assert stopped_call is True

    @pytest.mark.asyncio
    async def test_reaction_broadcasts_to_peers(self):
        """Verify emoji reactions are broadcast to other peers."""
        do = self._make_classroom_do()
        ws_alice = self._add_session(do, "alice", "Alice")
        ws_bob   = self._add_session(do, "bob", "Bob")

        msg = json.dumps({"type": "reaction", "emoji": "🎉"})
        await do.on_webSocketMessage(ws_alice, msg)

        reaction_bob = any(
            json.loads(c[0][0]).get("type") == "reaction"
            and json.loads(c[0][0]).get("emoji") == "🎉"
            and json.loads(c[0][0]).get("participant_id") == "alice"
            for c in ws_bob.send.call_args_list
        )
        assert reaction_bob is True

    @pytest.mark.asyncio
    async def test_hand_raised_broadcasts_and_updates_queue(self):
        """Verify hand raises update hand_raise_queue and broadcast."""
        do = self._make_classroom_do()
        ws_alice = self._add_session(do, "alice", "Alice")
        ws_bob   = self._add_session(do, "bob", "Bob")

        await do.on_webSocketMessage(ws_alice, json.dumps({"type": "hand_raised", "hand_raised": True}))

        hand_bob = any(
            json.loads(c[0][0]).get("type") == "hand_raised"
            and json.loads(c[0][0]).get("hand_raised") is True
            and json.loads(c[0][0]).get("participant_id") == "alice"
            for c in ws_bob.send.call_args_list
        )
        assert hand_bob is True
        assert "alice" in do.hand_raise_queue

    @pytest.mark.asyncio
    async def test_default_media_state_muted_and_video_off(self):
        """Verify default media state on connection is muted with video off."""
        do = self._make_classroom_do()
        ws_bob = self._add_session(do, "bob", "Bob")

        req = _make_request(
            path="ws://localhost/api/classroom/room1",
            upgrade="websocket",
        )
        req.url = "ws://localhost/api/classroom/room1?participant_id=alice&display_name=Alice"
        resp = await do.on_fetch(req)
        assert resp.status == 101

        # Check session initialization in do.sessions
        alice_session = next(s for s in do.sessions.values() if s.get("display_name") == "Alice")
        assert alice_session["media_state"] == {
            "audio": False,
            "video": False,
            "mic_enabled": False,
            "cam_enabled": False,
        }

        # Check participant_joined payload broadcast to bob
        calls = [json.loads(c[0][0]) for c in ws_bob.send.call_args_list if c[0]]
        joined_msg = next((c for c in calls if c.get("type") == "participant_joined" and c.get("display_name") == "Alice"), None)
        assert joined_msg is not None
        assert joined_msg["media_state"] == {
            "audio": False,
            "video": False,
            "mic_enabled": False,
            "cam_enabled": False,
        }

    @pytest.mark.asyncio
    async def test_on_fetch_classifies_host_and_guest_roles(self):
        """Verify activity host is classified as instructor and guest as non-instructor."""
        do = self._make_classroom_do()
        do.activity_host_id = "host-user"
        do.activity_host_name = "HostUser"

        env = do.env
        token_host = worker.create_token("host-user", "HostUser", "user", env.JWT_SECRET)
        req_host = _make_request(
            path="ws://localhost/api/classroom/room1",
            upgrade="websocket",
            token=token_host,
        )
        resp_host = await do.on_fetch(req_host)
        assert resp_host.status == 101
        host_sess = next(s for s in do.sessions.values() if s["participant_id"] == "host-user")
        assert host_sess["is_instructor"] is True
        assert host_sess["role"] == "instructor"

        req_guest = _make_request(
            path="ws://localhost/api/classroom/room1",
            upgrade="websocket",
        )
        req_guest.url = "ws://localhost/api/classroom/room1?participant_id=guest-user&display_name=GuestUser"
        resp_guest = await do.on_fetch(req_guest)
        assert resp_guest.status == 101
        guest_sess = next(s for s in do.sessions.values() if s.get("display_name") == "GuestUser")
        assert guest_sess["is_instructor"] is False
        assert guest_sess["role"] == "student"

    @pytest.mark.asyncio
    async def test_instructor_mute_all_broadcasts_force_mute(self):
        """Verify instructor mute_all triggers force_mute broadcast."""
        do = self._make_classroom_do()
        ws_instructor = self._add_session(do, "teacher", "Teacher")
        do.sessions["sid-teacher"]["is_instructor"] = True
        ws_student = self._add_session(do, "student1", "Student 1")

        msg = json.dumps({"type": "mute_all"})
        await do.on_webSocketMessage(ws_instructor, msg)

        calls = [json.loads(c[0][0]) for c in ws_student.send.call_args_list if c[0]]
        assert any(c.get("type") == "force_mute" for c in calls)

    @pytest.mark.asyncio
    async def test_non_instructor_mute_all_ignored(self):
        """Verify non-instructor mute_all has no effect."""
        do = self._make_classroom_do()
        ws_student = self._add_session(do, "student1", "Student 1")
        ws_other = self._add_session(do, "student2", "Student 2")

        msg = json.dumps({"type": "mute_all"})
        await do.on_webSocketMessage(ws_student, msg)

        calls = [json.loads(c[0][0]) for c in ws_other.send.call_args_list if c[0]]
        assert not any(c.get("type") == "force_mute" for c in calls)

    @pytest.mark.asyncio
    async def test_instructor_spotlight_broadcasts_spotlight_changed(self):
        """Verify instructor spotlight triggers spotlight_changed broadcast."""
        do = self._make_classroom_do()
        ws_instructor = self._add_session(do, "teacher", "Teacher")
        do.sessions["sid-teacher"]["is_instructor"] = True
        ws_student = self._add_session(do, "student1", "Student 1")

        msg = json.dumps({"type": "spotlight", "target_peer_id": "student1"})
        await do.on_webSocketMessage(ws_instructor, msg)

        assert do.spotlight_peer_id == "student1"
        calls = [json.loads(c[0][0]) for c in ws_student.send.call_args_list if c[0]]
        assert any(c.get("type") == "spotlight_changed" and c.get("spotlight_peer_id") == "student1" for c in calls)

    @pytest.mark.asyncio
    async def test_live_caption_broadcasts_to_all(self):
        """Verify live_caption messages are broadcast to peers."""
        do = self._make_classroom_do()
        ws_alice = self._add_session(do, "alice", "Alice")
        ws_bob = self._add_session(do, "bob", "Bob")

        msg = json.dumps({"type": "live_caption", "text": "Hello world, welcome to class", "is_final": True})
        await do.on_webSocketMessage(ws_alice, msg)

        calls = [json.loads(c[0][0]) for c in ws_bob.send.call_args_list if c[0]]
        assert any(c.get("type") == "live_caption" and c.get("text") == "Hello world, welcome to class" for c in calls)

    @pytest.mark.asyncio
    async def test_media_state_merged_across_tabs(self):
        """Verify media_state broadcasts merged audio/video across multiple tabs for same participant."""
        do = self._make_classroom_do()
        ws_alice1 = self._add_session(do, "alice", "Alice")
        ws_alice2 = MagicMock()
        ws_alice2.deserializeAttachment.return_value = json.dumps({"session_id": "sid-alice2"})
        do.sessions["sid-alice2"] = {
            "ws": ws_alice2,
            "session_id": "sid-alice2",
            "participant_id": "alice",
            "display_name": "Alice",
            "can_interact": True,
            "media_state": {"audio": True, "video": False, "mic_enabled": True, "cam_enabled": False},
        }
        ws_bob = self._add_session(do, "bob", "Bob")

        # Tab 1 sets audio to False, but Tab 2 still has audio True
        ws_bob.send.reset_mock()
        await do.on_webSocketMessage(ws_alice1, json.dumps({
            "type": "media_state",
            "audio": False,
            "video": False,
        }))

        calls = [json.loads(c[0][0]) for c in ws_bob.send.call_args_list if c[0]]
        media_msg = next((c for c in calls if c.get("type") == "media_state" and c.get("participant_id") == "alice"), None)
        assert media_msg is not None
        assert media_msg["audio"] is True
        assert media_msg["mic_enabled"] is True

    @pytest.mark.asyncio
    async def test_whiteboard_event_sets_server_participant_id(self):
        """Verify server sets participant_id ignoring client spoofed value."""
        do = self._make_classroom_do()
        ws_alice = self._add_session(do, "alice", "Alice")
        storage_put = AsyncMock()
        do.ctx = SimpleNamespace(storage=SimpleNamespace(get=AsyncMock(return_value="[]"), put=storage_put))

        event_payload = {
            "from": {"x": 0.1, "y": 0.1},
            "to": {"x": 0.2, "y": 0.2},
            "participant_id": "spoofed_id",
            "alpha": 0.8,
        }
        await do.on_webSocketMessage(ws_alice, json.dumps({
            "type": "whiteboard_event",
            "event": event_payload,
        }))

        storage_put.assert_called_once()
        saved = json.loads(storage_put.call_args[0][1])
        assert saved[-1]["participant_id"] == "alice"
        assert saved[-1]["alpha"] == 0.8

    @pytest.mark.asyncio
    async def test_screen_share_instructor_override_and_liveness(self):
        """Verify instructor can override screen share and stale sharer is cleared."""
        do = self._make_classroom_do()
        ws_alice = self._add_session(do, "alice", "Alice")
        ws_teacher = self._add_session(do, "teacher", "Teacher")
        do.sessions["sid-teacher"]["is_instructor"] = True

        # Alice shares
        await do.on_webSocketMessage(ws_alice, json.dumps({
            "type": "start_screen_share",
            "stream_id": "stream-alice",
        }))
        assert do.screen_sharer["participant_id"] == "alice"

        # Teacher overrides
        await do.on_webSocketMessage(ws_teacher, json.dumps({
            "type": "start_screen_share",
            "stream_id": "stream-teacher",
        }))
        assert do.screen_sharer["participant_id"] == "teacher"

    @pytest.mark.asyncio
    async def test_update_seat_range_validation(self):
        """Verify numeric seat IDs are bounded to 1-15."""
        do = self._make_classroom_do()
        ws_alice = self._add_session(do, "alice", "Alice")

        # Invalid seats: 0 and 16
        await do.on_webSocketMessage(ws_alice, json.dumps({"type": "update_seat", "seat_id": "seat-0"}))
        assert do.sessions["sid-alice"].get("seat_id", "") != "seat-0"

        await do.on_webSocketMessage(ws_alice, json.dumps({"type": "update_seat", "seat_id": "seat-16"}))
        assert do.sessions["sid-alice"].get("seat_id", "") != "seat-16"

        # Valid seat: 15
        await do.on_webSocketMessage(ws_alice, json.dumps({"type": "update_seat", "seat_id": "seat-15"}))
        assert do.sessions["sid-alice"].get("seat_id") == "seat-15"

    @pytest.mark.asyncio
    async def test_create_and_close_breakout_rooms(self):
        """Verify instructor can create and close breakout rooms, while student cannot."""
        do = self._make_classroom_do()
        ws_alice = self._add_session(do, "alice", "Alice")
        ws_teacher = self._add_session(do, "teacher", "Teacher")
        do.sessions["sid-teacher"]["is_instructor"] = True

        storage_put = AsyncMock()
        storage_del = AsyncMock()
        do.ctx.storage = SimpleNamespace(put=storage_put, delete=storage_del)

        # Alice (student) attempts to create breakout rooms -> rejected
        await do.on_webSocketMessage(ws_alice, json.dumps({
            "type": "create_breakouts",
            "count": 2,
        }))
        assert do.breakout_rooms == []

        # Teacher (instructor) creates breakout rooms
        ws_alice.send.reset_mock()
        await do.on_webSocketMessage(ws_teacher, json.dumps({
            "type": "create_breakouts",
            "count": 3,
        }))
        assert len(do.breakout_rooms) == 3
        assert do.breakout_rooms[0]["breakout_room_id"] == f"{do.room_id}:breakout:1"

        calls = [json.loads(c[0][0]) for c in ws_alice.send.call_args_list if c[0]]
        created_msg = next((c for c in calls if c.get("type") == "breakout_rooms_created"), None)
        assert created_msg is not None
        assert len(created_msg["rooms"]) == 3

        # Teacher closes breakout rooms
        ws_alice.send.reset_mock()
        await do.on_webSocketMessage(ws_teacher, json.dumps({
            "type": "close_breakouts",
        }))
        assert do.breakout_rooms == []
        storage_del.assert_called_once_with("breakout_rooms")

        calls = [json.loads(c[0][0]) for c in ws_alice.send.call_args_list if c[0]]
        closed_msg = next((c for c in calls if c.get("type") == "breakout_rooms_closed"), None)
        assert closed_msg is not None

    @pytest.mark.asyncio
    async def test_breakout_announcement_broadcast(self):
        """Verify instructor can broadcast announcements across breakout rooms."""
        do = self._make_classroom_do()
        ws_alice = self._add_session(do, "alice", "Alice")
        ws_teacher = self._add_session(do, "teacher", "Teacher")
        do.sessions["sid-teacher"]["is_instructor"] = True

        ws_alice.send.reset_mock()
        await do.on_webSocketMessage(ws_teacher, json.dumps({
            "type": "broadcast_to_breakouts",
            "message": "Class resuming in 2 minutes!",
        }))

        calls = [json.loads(c[0][0]) for c in ws_alice.send.call_args_list if c[0]]
        ann_msg = next((c for c in calls if c.get("type") == "breakout_announcement"), None)
        assert ann_msg is not None
        assert ann_msg["message"] == "Class resuming in 2 minutes!"

    @pytest.mark.asyncio
    async def test_connection_mode_changed_broadcast(self):
        """Verify changing connection mode updates session and broadcasts to room."""
        do = self._make_classroom_do()
        ws_alice = self._add_session(do, "alice", "Alice")
        ws_bob = self._add_session(do, "bob", "Bob")

        ws_bob.send.reset_mock()
        await do.on_webSocketMessage(ws_alice, json.dumps({
            "type": "connection_mode",
            "mode": "audio_only",
        }))

        assert do.sessions["sid-alice"]["connection_mode"] == "audio_only"
        calls = [json.loads(c[0][0]) for c in ws_bob.send.call_args_list if c[0]]
        mode_msg = next((c for c in calls if c.get("type") == "connection_mode_changed"), None)
        assert mode_msg is not None
        assert mode_msg["participant_id"] == "alice"
        assert mode_msg["mode"] == "audio_only"

    @pytest.mark.asyncio
    async def test_live_caption_persists_to_storage_and_d1(self):
        """Verify final live captions are broadcast and persisted to storage and D1."""
        do = self._make_classroom_do()
        ws_alice = self._add_session(do, "alice", "Alice")
        ws_bob = self._add_session(do, "bob", "Bob")

        storage_put = AsyncMock()
        do.ctx.storage = SimpleNamespace(put=storage_put)

        ws_bob.send.reset_mock()
        await do.on_webSocketMessage(ws_alice, json.dumps({
            "type": "live_caption",
            "text": "Hello world, welcome to class",
            "is_final": True,
        }))

        calls = [json.loads(c[0][0]) for c in ws_bob.send.call_args_list if c[0]]
        cap_msg = next((c for c in calls if c.get("type") == "live_caption"), None)
        assert cap_msg is not None
        assert cap_msg["text"] == "Hello world, welcome to class"
        assert cap_msg["is_final"] is True

        assert len(do.transcripts) == 1
        assert do.transcripts[0]["text"] == "Hello world, welcome to class"
        storage_put.assert_called_once()

    @pytest.mark.asyncio
    async def test_presence_do_persist_user_attachments_keeps_is_authenticated(self):
        """Verify PresenceDO._persist_user_attachments preserves is_authenticated flag."""
        do = worker.PresenceDO.__new__(worker.PresenceDO)
        do.presence = {"u1": {"x": 0.5, "y": 0.5, "emoji": "👋", "hand_raised": False}}
        ws = MagicMock()
        do.sessions = {
            "s1": {
                "ws": ws,
                "user_id": "u1",
                "display_name": "User 1",
                "can_interact": True,
                "is_authenticated": True,
            }
        }
        do._persist_user_attachments("u1")
        ws.serializeAttachment.assert_called_once()
        saved = json.loads(ws.serializeAttachment.call_args[0][0])
        assert saved["is_authenticated"] is True


@pytest.mark.asyncio
async def test_api_classroom_transcripts_search():
    """Verify GET /api/classroom/:room_id/transcripts returns filtered transcripts."""
    row1 = MockRow(id="t1", room_id="lobby", session_id="s1", participant_id="p1", display_name="Alice", text="Introduction to Physics", timestamp="2026-11-03T10:00:00", source="live")
    stmt = make_stmt(all_results=[row1])
    env = make_env(db=MockDB([stmt]))

    req = MockRequest(method="GET", url="http://localhost/api/classroom/lobby/transcripts?q=Physics")
    res = await worker.api_classroom_transcripts(req, env, "lobby")
    assert res.status == 200
    body = json.loads(res.body)
    assert body["success"] is True
    assert len(body["data"]["transcripts"]) == 1
    assert body["data"]["transcripts"][0]["text"] == "Introduction to Physics"


@pytest.mark.asyncio
async def test_api_classroom_breakouts_list():
    """Verify GET /api/classroom/:room_id/breakouts returns list of breakout rooms."""
    row = MockRow(id="b1", parent_room_id="lobby", breakout_room_id="lobby:breakout:1", title="Team Alpha", created_at="2026-11-03T10:00:00")
    stmt = make_stmt(all_results=[row])
    env = make_env(db=MockDB([stmt]))

    req = MockRequest(method="GET", url="http://localhost/api/classroom/lobby/breakouts")
    res = await worker.api_classroom_breakouts(req, env, "lobby")
    assert res.status == 200
    body = json.loads(res.body)
    assert body["success"] is True
    assert len(body["data"]["breakouts"]) == 1
    assert body["data"]["breakouts"][0]["breakout_room_id"] == "lobby:breakout:1"


@pytest.mark.asyncio
async def test_api_classroom_caption_transcribe():
    """Verify POST /api/classroom/:room_id/caption accepts audio and returns transcript."""
    env = make_env()
    env.AI = MagicMock()
    env.AI.run = AsyncMock(return_value={"text": "Transcribed speech from audio snippet"})

    audio_bytes = b"RIFFmockwavcontent"
    b64_audio = base64.b64encode(audio_bytes).decode("ascii")

    req = MockRequest(
        method="POST",
        url="http://localhost/api/classroom/lobby/caption",
        body=json.dumps({
            "audio": b64_audio,
            "participant_id": "alice",
            "display_name": "Alice",
        }),
    )
    res = await worker.api_classroom_caption(req, env, "lobby")
    assert res.status == 200
    body = json.loads(res.body)
    assert body["success"] is True
    assert body["data"]["text"] == "Transcribed speech from audio snippet"
    assert body["data"]["room_id"] == "lobby"


@pytest.mark.asyncio
async def test_deleted_instructor_cannot_mute_all():
    """Verify deleted user cannot mute_all even if session has is_instructor=True."""
    db = MagicMock()
    db.prepare = MagicMock(side_effect=lambda sql: make_stmt(first=MockRow(role="deleted")))
    ctx = _make_ctx()
    env = make_env(db=db)
    do = worker.ClassroomDO(ctx, env)
    do.room_id = "lobby"

    ws_instructor = MagicMock()
    ws_student = MagicMock()
    attachment = {
        "session_id": "sid-teacher",
        "participant_id": "teacher",
        "display_name": "Teacher",
        "position": {"x": 0.5, "y": 0.5},
        "direction": "down",
        "seat_id": "",
        "can_interact": True,
        "is_instructor": True,
        "media_state": {},
    }
    ws_instructor.deserializeAttachment.return_value = json.dumps(attachment)
    ws_student.deserializeAttachment.return_value = json.dumps({
        "session_id": "sid-student",
        "participant_id": "student",
        "display_name": "Student",
        "position": {"x": 0.5, "y": 0.5},
        "direction": "down",
        "seat_id": "",
        "can_interact": True,
        "is_instructor": False,
        "media_state": {},
    })
    do.sessions["sid-teacher"] = {
        "ws": ws_instructor,
        "participant_id": "teacher",
        "display_name": "Teacher",
        "is_instructor": True,
        "can_interact": True,
        "role": "instructor",
    }
    do.sessions["sid-student"] = {
        "ws": ws_student,
        "participant_id": "student",
        "display_name": "Student",
        "is_instructor": False,
        "can_interact": True,
        "role": "student",
    }

    msg = json.dumps({"type": "mute_all"})
    await do.on_webSocketMessage(ws_instructor, msg)
    assert not any(json.loads(c[0][0]).get("type") == "force_mute" for c in ws_student.send.call_args_list if c[0])


@pytest.mark.asyncio
async def test_screen_share_instructor_override_persists_cleared_previous_sharer():
    """Verify instructor override clears previous sharer's persisted attachment."""
    do = worker.ClassroomDO(_make_ctx(), make_env())
    do.room_id = "lobby"
    ws_alice = MagicMock()
    ws_teacher = MagicMock()
    do.sessions["sid-alice"] = {
        "ws": ws_alice,
        "participant_id": "alice",
        "display_name": "Alice",
        "is_instructor": False,
        "can_interact": True,
        "position": {"x": 0.5, "y": 0.5},
        "direction": "down",
    }
    do.sessions["sid-teacher"] = {
        "ws": ws_teacher,
        "participant_id": "teacher",
        "display_name": "Teacher",
        "is_instructor": True,
        "can_interact": True,
        "position": {"x": 0.5, "y": 0.5},
        "direction": "down",
    }

    # Alice shares
    await do.on_webSocketMessage(ws_alice, json.dumps({"type": "start_screen_share", "stream_id": "stream-1"}))
    assert do.screen_sharer_session_id == "sid-alice"

    # Teacher overrides
    await do.on_webSocketMessage(ws_teacher, json.dumps({"type": "start_screen_share", "stream_id": "stream-2"}))
    assert do.screen_sharer_session_id == "sid-teacher"

    # Alice's serialized attachment was updated and is_screen_sharing is False
    calls = [json.loads(c[0][0]) for c in ws_alice.serializeAttachment.call_args_list if c[0]]
    assert len(calls) > 0
    last_call = calls[-1]
    assert last_call.get("is_screen_sharing") is False


@pytest.mark.asyncio
async def test_screen_share_stop_from_different_tab_ignored():
    """Verify stop_screen_share from another tab does not stop active share."""
    do = worker.ClassroomDO(_make_ctx(), make_env())
    do.room_id = "lobby"
    ws_tab1 = MagicMock()
    ws_tab2 = MagicMock()
    do.sessions["sid-tab1"] = {
        "ws": ws_tab1,
        "participant_id": "alice",
        "display_name": "Alice",
        "is_instructor": False,
        "can_interact": True,
        "position": {"x": 0.5, "y": 0.5},
        "direction": "down",
    }
    do.sessions["sid-tab2"] = {
        "ws": ws_tab2,
        "participant_id": "alice",
        "display_name": "Alice",
        "is_instructor": False,
        "can_interact": True,
        "position": {"x": 0.5, "y": 0.5},
        "direction": "down",
    }

    # Tab 1 starts share
    await do.on_webSocketMessage(ws_tab1, json.dumps({"type": "start_screen_share", "stream_id": "stream-tab1"}))
    assert do.screen_sharer_session_id == "sid-tab1"

    # Tab 2 attempts stop share -> ignored because sharer_sid != sid-tab2
    await do.on_webSocketMessage(ws_tab2, json.dumps({"type": "stop_screen_share"}))
    assert do.screen_sharer_session_id == "sid-tab1"
    assert do.screen_sharer is not None


@pytest.mark.asyncio
async def test_seat_id_length_bounded():
    """Verify seat_id with oversized digits is rejected without error."""
    do = worker.ClassroomDO(_make_ctx(), make_env())
    ws_alice = MagicMock()
    do.sessions["sid-alice"] = {
        "ws": ws_alice,
        "participant_id": "alice",
        "display_name": "Alice",
        "is_instructor": False,
        "can_interact": True,
        "position": {"x": 0.5, "y": 0.5},
        "direction": "down",
        "seat_id": "",
    }
    await do.on_webSocketMessage(ws_alice, json.dumps({
        "type": "update_seat",
        "seat_id": "seat-999999999999999999999999999999999999999999",
    }))
    assert do.sessions["sid-alice"]["seat_id"] == ""


@pytest.mark.asyncio
async def test_presence_owner_join_revokes_anonymous_session():
    """Verify authenticated user join revokes anonymous session for same user_id."""
    ctx = _make_ctx()
    env = _make_presence_env(allow_anon="true")
    do = worker.PresenceDO(ctx, env)

    req_anon = MockRequest(
        method="GET",
        url="http://localhost/presence/lobby?user_id=target_user&display_name=AnonTarget",
        headers={"Upgrade": "websocket"},
    )
    res_anon = await do.on_fetch(req_anon)
    assert res_anon.status == 101
    anon_sid = list(do.sessions.keys())[0]
    assert do.sessions[anon_sid]["can_interact"] is True

    # Authenticated owner joins with token
    token = worker.create_token("target_user", "real_owner", "student", env.JWT_SECRET)
    req_auth = MockRequest(
        method="GET",
        url=f"http://localhost/presence/lobby?token={token}",
        headers={"Upgrade": "websocket"},
    )
    res_auth = await do.on_fetch(req_auth)
    assert res_auth.status == 101

    # Check anonymous session had can_interact set to False
    assert do.sessions[anon_sid]["can_interact"] is False
