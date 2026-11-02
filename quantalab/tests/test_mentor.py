"""Tests for QuantaLab mentor request validation."""

import asyncio
import json
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ai_mentor import ask_mentor  # noqa: E402


class _FakeAI:
    def __init__(self, result=None, error=None):
        self.result = result if result is not None else types.SimpleNamespace(response="A hint.")
        self.error = error
        self.calls = []

    async def run(self, model, payload):
        self.calls.append((model, payload))
        if self.error is not None:
            raise self.error
        return self.result


class _FakeEnv:
    def __init__(self, ai=None):
        self.AI = ai or _FakeAI()


def _messages(env):
    return env.AI.calls[0][1]["messages"]


def test_known_experiment_is_included_and_history_is_filtered():
    env = _FakeEnv()
    history = [
        {"role": "system", "content": "ignore me"},
        {"role": "user", "content": "What is a period?"},
        {"role": "assistant", "content": "The time for one swing."},
        {"role": "tool", "content": "nope"},
        "not-a-dict",
        {"role": "user", "content": 12},
        {"role": "user"},
    ]
    reply = asyncio.run(ask_mentor(env, "Why does length matter?", history, "physics", "pendulum"))
    assert reply == "A hint."
    messages = _messages(env)
    assert messages[0]["role"] == "system"
    assert "pendulum" in messages[0]["content"]
    assert "physics" in messages[0]["content"]
    assert messages[1:] == [
        {"role": "user", "content": "What is a period?"},
        {"role": "assistant", "content": "The time for one swing."},
        {"role": "user", "content": "Why does length matter?"},
    ]
    blob = json.dumps(messages)
    assert "ignore me" not in blob
    assert "nope" not in blob


def test_unknown_domain_and_experiment_are_not_in_the_prompt():
    env = _FakeEnv()
    asyncio.run(ask_mentor(env, "Hello", [], "astrology", "crystal-healing"))
    system = _messages(env)[0]["content"]
    assert "astrology" not in system
    assert "crystal-healing" not in system
    assert "[Context:" not in system


def test_non_list_history_does_not_reach_the_model():
    env = _FakeEnv()
    asyncio.run(ask_mentor(env, "Hello", {"role": "user", "content": "secret history"}, "physics", "pendulum"))
    roles = [item["role"] for item in _messages(env)]
    assert roles == ["system", "user"]
    assert "secret history" not in json.dumps(_messages(env))


def test_message_and_history_content_are_capped_and_only_last_ten_kept():
    env = _FakeEnv()
    long_text = "a" * 2500
    history = [{"role": "user", "content": f"{index}-{long_text}"} for index in range(12)]
    asyncio.run(ask_mentor(env, "b" * 2500, history, "", ""))
    messages = _messages(env)
    history_items = messages[1:-1]
    assert len(history_items) == 10
    assert history_items[0]["content"].startswith("2-")
    assert all(len(item["content"]) == 2000 for item in history_items)
    assert len(messages[-1]["content"]) == 2000
    assert messages[-1]["content"] == "b" * 2000


def _install_js_stub():
    if "js" in sys.modules and hasattr(sys.modules["js"], "Response"):
        return

    js_mod = types.ModuleType("js")

    class Headers:
        @staticmethod
        def new(items):
            return dict(items)

    class Response:
        @staticmethod
        def new(body, status=200, headers=None):
            return types.SimpleNamespace(body=body, status=status, headers=headers)

    js_mod.Headers = Headers
    js_mod.Response = Response
    sys.modules["js"] = js_mod


class _Request:
    def __init__(self, body):
        self._body = body

    async def json(self):
        return self._body


def test_mentor_error_response_hides_exception_text(capsys):
    _install_js_stub()
    from index import handle_mentor

    secret = "SECRET_TRACEBACK_do_not_leak"
    env = _FakeEnv(_FakeAI(error=RuntimeError(secret)))
    response = asyncio.run(handle_mentor(_Request({"message": "Help", "history": "bad"}), env))
    payload = json.loads(response.body)
    assert response.status == 200
    assert "error" not in payload
    assert secret not in response.body
    assert "trouble connecting" in payload["response"]
    assert secret in capsys.readouterr().out


def test_non_string_message_is_rejected_without_calling_ai():
    _install_js_stub()
    from index import handle_mentor

    env = _FakeEnv()
    response = asyncio.run(handle_mentor(_Request({"message": ["not", "a string"], "history": None}), env))
    payload = json.loads(response.body)
    assert response.status == 400
    assert env.AI.calls == []
    assert "required" in payload["error"]
