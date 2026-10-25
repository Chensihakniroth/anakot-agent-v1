"""One-use side-question lease invariants for the plugin capability."""

from __future__ import annotations

import contextvars
import weakref
from types import SimpleNamespace
from unittest.mock import patch

from agent.side_question_lease import issue_side_question_token, redeem_side_question, _leases


class _Agent(SimpleNamespace):
    """Weak-referenceable stand-in for the live AIAgent."""


def _agent(turn_id="turn-1", **overrides):
    return _Agent(
        _persist_disabled=False,
        platform="telegram",
        _delegate_depth=0,
        _cached_system_prompt="sys",
        _cached_system_prompt_static=None,
        tools=[],
        session_id="session",
        _current_turn_id=turn_id,
        model="test/model",
        provider="test-provider",
        base_url="https://example.invalid/v1",
        api_mode="openai",
        reasoning_config=None,
        **overrides,
    )


def test_runtime_change_invalidates_redeem_before_provider_call(monkeypatch, tmp_path):
    parent = _agent()
    monkeypatch.setenv("ANAKOT_HOME", str(tmp_path))
    with patch("agent.side_question_lease._consented_plugin_loaded", return_value=True):
        token = issue_side_question_token(parent, [], "turn-1")
    parent.model = "other/model"
    monkeypatch.setattr("agent.side_question_lease.ask_text_only", lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not call provider")))
    assert redeem_side_question(token, "question", plugin_id="observer") is None
    _leases.clear()


def test_runtime_key_is_captured_without_mutating_parent():
    parent = _agent()
    assert parent.model == "test/model"
    assert contextvars.copy_context() is not None
    assert weakref.ref(parent)() is parent
