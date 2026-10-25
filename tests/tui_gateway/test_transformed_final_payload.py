"""Wire contract for transformed final replies carried by message.complete."""

import contextlib
from types import SimpleNamespace

import tui_gateway.server as srv


def _turn(result):
    return SimpleNamespace(
        result=result,
        agent=SimpleNamespace(provider="", model=""),
        terminal_callback=None,
        receipt_committed=False,
        marker_key="",
        error_retained=False,
        error_detail="",
        prompt_text="ping",
    )


def test_message_complete_reports_transformed_flag(monkeypatch):
    monkeypatch.setattr(srv, "_get_usage", lambda _agent: {})
    monkeypatch.setattr(srv, "render_message", lambda _text, _cols: None)
    monkeypatch.setattr(srv, "_clear_inflight_turn", lambda _session: None)
    monkeypatch.setattr(srv, "_is_bot_mode_session", lambda _session: False)

    session = {"history_lock": contextlib.nullcontext()}
    result = {
        "final_response": "rewritten final",
        "response_transformed": True,
    }
    payload, raw, status = srv._complete_turn_payload(session, _turn(result), None, 80)

    assert raw == "rewritten final"
    assert status == "complete"
    assert payload["response_transformed"] is True
    assert payload["text"] == "rewritten final"


def test_message_complete_surfaces_transformed_final_when_stream_delivered_none(monkeypatch):
    monkeypatch.setattr(srv, "_get_usage", lambda _agent: {})
    monkeypatch.setattr(srv, "render_message", lambda _text, _cols: None)
    monkeypatch.setattr(srv, "_clear_inflight_turn", lambda _session: None)
    monkeypatch.setattr(srv, "_is_bot_mode_session", lambda _session: False)

    session = {"history_lock": contextlib.nullcontext()}
    result = {
        "final_response": "rewritten final",
        "response_transformed": True,
    }
    payload, raw, status = srv._complete_turn_payload(session, _turn(result), None, 80)

    assert raw == "rewritten final"
    assert payload["response_transformed"] is True
    assert payload["text"] == "rewritten final"
