"""
Unit tests for PresenceDO.

Stubs are installed by conftest.py before any test file imports worker.py.
All WebSocket interactions use unittest.mock.MagicMock so no real runtime
primitives are needed.
"""

import json
import pytest
from unittest.mock import MagicMock, AsyncMock

from tests.helpers import load_worker, make_env

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
