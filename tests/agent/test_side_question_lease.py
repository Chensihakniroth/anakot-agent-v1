"""Lease invariants for plugin-owned ``ctx.side_question`` requests."""

from __future__ import annotations

import weakref
from types import SimpleNamespace
from unittest.mock import patch

import pytest


class _Agent:
    _persist_disabled = False
    platform = "cli"
    _delegate_depth = 0
    _cached_system_prompt = "system"
    _cached_system_prompt_static = "stable"
    tools = []
    session_id = "session-a"
    _current_turn_id = "turn-a"
    model = "model"
    provider = "provider"
    base_url = "https://provider.example/v1"
    api_mode = "chat_completions"
    reasoning_config = None


@pytest.fixture(autouse=True)
def clean_leases():
    from agent import side_question_lease

    with side_question_lease._lock:
        side_question_lease._leases.clear()
    yield
    with side_question_lease._lock:
        side_question_lease._leases.clear()


def test_issue_requires_a_consented_plugin(monkeypatch):
    from agent.side_question_lease import issue_side_question_token

    agent = _Agent()
    monkeypatch.setattr("agent.side_question_lease._consented_plugin_loaded", lambda: False)
    assert issue_side_question_token(agent, [{"role": "assistant", "content": "done"}], "turn-a") is None


def test_unattended_turns_receive_no_lease(monkeypatch):
    from agent.side_question_lease import issue_side_question_token

    monkeypatch.setattr("agent.side_question_lease._consented_plugin_loaded", lambda: True)
    for platform, depth, persist_disabled in (("cron", 0, False), ("cli", 1, False), ("cli", 0, True)):
        agent = _Agent()
        agent.platform = platform
        agent._delegate_depth = depth
        agent._persist_disabled = persist_disabled
        assert issue_side_question_token(agent, [], "turn-a") is None


def test_lease_is_single_use_and_calls_text_only_request(monkeypatch):
    from agent.side_question_lease import issue_side_question_token, redeem_side_question

    agent = _Agent()
    monkeypatch.setattr("agent.side_question_lease._consented_plugin_loaded", lambda: True)
    with patch("agent.side_question_lease.ask_text_only", return_value="answer") as ask:
        token = issue_side_question_token(agent, [{"role": "assistant", "content": "done"}], "turn-a")
        assert token
        assert redeem_side_question(token, "what now?", plugin_id="capplug") == "answer"
        assert redeem_side_question(token, "again?", plugin_id="capplug") is None
    ask.assert_called_once()
    capture = ask.call_args.args[0]
    assert capture.session_id == "session-a"
    assert capture.turn_id == "turn-a"


def test_new_turn_invalidates_the_previous_lease(monkeypatch):
    from agent.side_question_lease import issue_side_question_token, redeem_side_question

    agent = _Agent()
    monkeypatch.setattr("agent.side_question_lease._consented_plugin_loaded", lambda: True)
    old = issue_side_question_token(agent, [], "turn-a")
    agent._current_turn_id = "turn-b"
    new = issue_side_question_token(agent, [], "turn-b")
    with patch("agent.side_question_lease.ask_text_only", return_value="new"):
        assert redeem_side_question(old, "old?", plugin_id="capplug") is None
        assert redeem_side_question(new, "new?", plugin_id="capplug") == "new"


def test_other_profile_cannot_redeem_lease(monkeypatch, tmp_path):
    from agent.side_question_lease import issue_side_question_token, redeem_side_question

    home_a = tmp_path / "a"
    home_b = tmp_path / "b"
    home_a.mkdir()
    home_b.mkdir()
    monkeypatch.setenv("ANAKOT_HOME", str(home_a))
    monkeypatch.setattr("agent.side_question_lease._consented_plugin_loaded", lambda: True)
    agent = _Agent()
    token = issue_side_question_token(agent, [], "turn-a")
    monkeypatch.setenv("ANAKOT_HOME", str(home_b))
    with patch("agent.side_question_lease.ask_text_only", return_value="answer") as ask:
        assert redeem_side_question(token, "cross profile?", plugin_id="capplug") is None
        ask.assert_not_called()
    monkeypatch.setenv("ANAKOT_HOME", str(home_a))
    with patch("agent.side_question_lease.ask_text_only", return_value="answer"):
        assert redeem_side_question(token, "owner?", plugin_id="capplug") == "answer"


def test_plugin_context_checks_consent_before_redeeming(monkeypatch, tmp_path):
    from anakot_cli.plugins_capability_ctx import PluginCapabilityCtxMixin

    class Context(PluginCapabilityCtxMixin):
        @property
        def plugin_id(self):
            return "capplug"

    context = Context()
    context.manifest = SimpleNamespace(source="user")
    context._manager = SimpleNamespace(home_path=tmp_path)
    monkeypatch.setattr(
        "anakot_cli.plugins_capability_ctx.plugin_capability_granted",
        lambda *args, **kwargs: True,
    )
    with patch(
        "agent.side_question_lease.redeem_side_question",
        return_value="answer",
    ) as redeem:
        assert context.side_question("token", "question?") == "answer"
    redeem.assert_called_once()
    assert redeem.call_args.kwargs["home"] == tmp_path
