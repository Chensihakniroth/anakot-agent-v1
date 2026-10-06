"""Wire contract for finals that reuse text already delivered during the turn."""

import contextlib
from types import SimpleNamespace

import pytest

from tui_gateway import prompt_turn


@pytest.mark.parametrize("reused,expected", [(True, True), (False, None)])
def test_message_complete_names_reused_final(monkeypatch, reused, expected):
    monkeypatch.setattr(prompt_turn, "_get_usage", lambda _agent: {})
    monkeypatch.setattr(prompt_turn, "render_message", lambda _text, _cols: None)
    monkeypatch.setattr(prompt_turn, "_clear_inflight_turn", lambda _session: None)
    monkeypatch.setattr(prompt_turn, "_is_bot_mode_session", lambda _session: False)

    agent = SimpleNamespace(provider="", model="")
    result = {"final_response": "Here is the answer.", "response_reused": reused}
    session = {"history_lock": contextlib.nullcontext()}
    state = prompt_turn._TurnRun(
        agent=agent,
        one_turn_restore=None,
        terminal_callback=None,
        receipt_committed=False,
        result=result,
    )

    payload, raw, status = prompt_turn._complete_turn_payload(session, state, None, 80)

    assert raw == "Here is the answer."
    assert status == "complete"
    assert payload.get("response_reused") is expected
