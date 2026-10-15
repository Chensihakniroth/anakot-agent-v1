"""Mistral Chat Completions routes require paired nine-character tool ids."""

from __future__ import annotations

import re

from agent.transports.chat_completions import (
    ChatCompletionsTransport,
    _mistral_tool_id,
    _route_requires_mistral_tool_ids,
)

_BAD_ID = "call_04c3699a572b"
_NATIVE_ID = "c9Abb5ZtX"


def test_mistral_route_gate_covers_provider_host_and_model_marker():
    assert _route_requires_mistral_tool_ids("mistral", "large", "https://example.test/v1")
    assert _route_requires_mistral_tool_ids("openai", "large", "https://api.mistral.ai/v1")
    assert _route_requires_mistral_tool_ids("openai", "mistral-large-3", "https://nim.example.test/v1")
    assert not _route_requires_mistral_tool_ids("openai", "gpt-4o", "https://api.openai.com/v1")


def test_mistral_tool_id_is_stable_and_preserves_valid_ids():
    mapped = _mistral_tool_id(_BAD_ID)

    assert mapped == "uzvbkiH61"
    assert re.fullmatch(r"[A-Za-z0-9]{9}", mapped)
    assert _mistral_tool_id(_BAD_ID) == mapped
    assert _mistral_tool_id(_NATIVE_ID) == _NATIVE_ID


def test_mistral_wire_maps_each_call_and_matching_result_without_mutating_history():
    messages = [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": f"{_BAD_ID}|fc_response_item",
                    "type": "function",
                    "function": {"name": "lookup", "arguments": "{}"},
                },
                {
                    "id": _NATIVE_ID,
                    "type": "function",
                    "function": {"name": "other", "arguments": "{}"},
                },
            ],
        },
        {"role": "tool", "tool_call_id": f"{_BAD_ID}|fc_response_item", "content": "ok"},
    ]

    result = ChatCompletionsTransport().convert_messages(
        messages,
        provider="mistral",
        model="mistral-large-3",
        base_url="https://api.mistral.ai/v1",
    )

    assert result[0]["tool_calls"][0]["id"] == "uzvbkiH61"
    assert result[1]["tool_call_id"] == "uzvbkiH61"
    assert result[0]["tool_calls"][1]["id"] == _NATIVE_ID
    assert messages[0]["tool_calls"][0]["id"] == f"{_BAD_ID}|fc_response_item"
    assert messages[1]["tool_call_id"] == f"{_BAD_ID}|fc_response_item"


def test_non_mistral_route_keeps_tool_ids():
    messages = [
        {
            "role": "assistant",
            "tool_calls": [{"id": _BAD_ID, "type": "function", "function": {"name": "x", "arguments": "{}"}}],
        },
        {"role": "tool", "tool_call_id": _BAD_ID, "content": "ok"},
    ]

    assert ChatCompletionsTransport().convert_messages(
        messages, provider="openai", model="gpt-4o", base_url="https://api.openai.com/v1"
    ) is messages
