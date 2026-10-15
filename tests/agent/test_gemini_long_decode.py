"""Gemini 4 long-decode hop and continuation contracts."""

from __future__ import annotations

import json
from types import SimpleNamespace


def _hop(text: str, finish: str, *, token: str | None, prompt: int, output: int) -> dict:
    candidate = {
        "content": {"role": "model", "parts": [{"text": text}]},
        "finishReason": finish,
    }
    if token is not None:
        candidate["continuationToken"] = token
    return {
        "candidates": [candidate],
        "usageMetadata": {
            "promptTokenCount": prompt,
            "candidatesTokenCount": output,
            "totalTokenCount": prompt + output,
        },
    }


def test_gemini_profile_passes_long_decode_budget_to_native_adapter():
    from providers import get_provider_profile

    body = get_provider_profile("gemini").build_extra_body(
        model="gemini-4-argon", reasoning_config={"enabled": True, "effort": "xhigh"},
    )

    assert body["thinking_config"]["thinkingLevel"] == "high"
    assert body["max_output_tokens"] == 262_144


def test_native_client_replays_continuation_hops_and_merges_usage(monkeypatch):
    from agent.gemini_native_adapter import GeminiNativeClient

    first = _hop("part one ", "CONTINUATION", token="tok-1", prompt=100, output=32_768)
    second = _hop("part two", "STOP", token=None, prompt=32_868, output=500)
    sent: list[dict] = []

    class DummyResponse:
        status_code = 200

        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    class DummyHTTP:
        def post(self, _url, json=None, headers=None, timeout=None):
            sent.append(json)
            return DummyResponse((first, second)[len(sent) - 1])

        def close(self):
            return None

    monkeypatch.setattr("agent.gemini_native_adapter.httpx.Client", lambda *args, **kwargs: DummyHTTP())
    client = GeminiNativeClient(
        api_key="AQ.test",
        base_url="https://generativelanguage.googleapis.com/v1beta",
    )
    response = client.chat.completions.create(
        model="gemini-4-argon",
        messages=[{"role": "user", "content": "prove it"}],
        max_tokens=262_144,
    )

    assert len(sent) == 2
    assert sent[1] == {**sent[0], "continuationToken": "tok-1"}
    assert response.choices[0].message.content == "part one part two"
    assert response.choices[0].finish_reason == "stop"
    assert response.usage.initial_prompt_tokens == 100
    assert response.usage.prompt_tokens == 32_968
    assert response.usage.completion_tokens == 33_268


def test_gemini4_effort_selects_long_decode_budget():
    from agent.gemini_long_decode import long_decode_max_output_tokens

    assert long_decode_max_output_tokens("gemini-4-argon", {"effort": "xhigh"}) == 262_144
    assert long_decode_max_output_tokens("google/gemini-4-argon", {"effort": "max"}) == 1_048_576
    assert long_decode_max_output_tokens("gemini-4-argon", {"effort": "medium"}) is None
    assert long_decode_max_output_tokens("gemini-3.8-flash", {"effort": "max"}) is None
    assert long_decode_max_output_tokens("gemini-4-argon", {"enabled": False, "effort": "max"}) is None








def test_turn_usage_uses_first_hop_prompt_for_context_but_keeps_billing_totals(monkeypatch):
    from agent import turn_usage
    from agent.usage_pricing import CanonicalUsage

    class Compressor:
        threshold_tokens = 100_000
        awaiting_real_usage_after_compression = False
        _verify_compaction_cleared_threshold = False
        _context_probed = False

        def update_from_response(self, usage):
            self.usage = usage

    agent = SimpleNamespace(
        context_compressor=Compressor(), session_api_calls=0, model="gemini-4-argon", provider="gemini",
        api_mode="chat_completions", base_url="https://generativelanguage.googleapis.com/v1beta", client=None,
        session_id="s", _session_db=None, _session_db_created=False, verbose_logging=False, quiet_mode=True,
        log_prefix="", session_estimated_cost_usd=0.0, session_cost_status=None, session_cost_source=None,
        session_prompt_tokens=0, session_completion_tokens=0, session_total_tokens=0, session_input_tokens=0,
        session_output_tokens=0, session_cache_read_tokens=0, session_cache_write_tokens=0, session_reasoning_tokens=0,
        _api_latency_history=[], _api_output_history=[], _safe_print=lambda *args: None,
    )
    response = SimpleNamespace(
        usage=SimpleNamespace(initial_prompt_tokens=100), id=None, provider=None,
    )
    monkeypatch.setattr(turn_usage, "normalize_usage", lambda *args, **kwargs: CanonicalUsage(
        input_tokens=32_968, output_tokens=33_268,
    ))
    monkeypatch.setattr(turn_usage, "calibrate_from_usage", lambda *args: None)
    monkeypatch.setattr(turn_usage, "capture_usage_anchor", lambda *args: None)
    monkeypatch.setattr(turn_usage, "estimate_usage_cost", lambda *args, **kwargs: SimpleNamespace(
        amount_usd=None, status="unknown", source="none",
    ))
    monkeypatch.setattr(turn_usage, "_loop_mod", lambda: SimpleNamespace(
        _should_rearm_compression_budget=lambda *args, **kwargs: False,
    ))

    turn_usage.record_response_usage(
        agent, response, messages=[{"role": "user", "content": "hi"}], api_call_count=1,
        api_duration=0.1, compression_attempts=0, max_compression_attempts=3,
    )

    assert agent._last_turn_usage["prompt_tokens"] == 100
    assert agent._last_turn_usage["total_tokens"] == 33_368
    assert agent._last_prompt_size_tokens == 100
    assert agent.session_prompt_tokens == 32_968
    assert agent.session_total_tokens == 66_236


def test_native_stream_replays_continuation_hops(monkeypatch):
    from agent.gemini_native_adapter import GeminiNativeClient

    first = _hop("part one", "CONTINUATION", token="tok-1", prompt=100, output=32_768)
    second = _hop("part two", "STOP", token=None, prompt=32_868, output=500)
    sent: list[dict] = []

    class StreamResponse:
        status_code = 200

        def __init__(self, payload):
            self._payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def iter_text(self):
            yield f"data: {json.dumps(self._payload)}\n\n"
            yield "data: [DONE]\n\n"

    class DummyHTTP:
        def stream(self, _method, _url, json=None, headers=None, timeout=None):
            sent.append(json)
            return StreamResponse((first, second)[len(sent) - 1])

        def close(self):
            return None

    monkeypatch.setattr("agent.gemini_native_adapter.httpx.Client", lambda *args, **kwargs: DummyHTTP())
    client = GeminiNativeClient(api_key="AQ.test", base_url="https://generativelanguage.googleapis.com/v1beta")
    chunks = list(client.chat.completions.create(
        model="gemini-4-argon", messages=[{"role": "user", "content": "prove it"}], stream=True,
        max_tokens=262_144,
    ))

    assert len(sent) == 2
    assert sent[1]["continuationToken"] == "tok-1"
    assert [chunk.choices[0].delta.content for chunk in chunks[:-1]] == ["part one", "part two"]
    assert chunks[-1].choices[0].finish_reason == "stop"
    assert chunks[-1].usage.prompt_tokens == 32_968
    assert chunks[-1].usage.initial_prompt_tokens == 100


def test_gemini_usage_exposes_hidden_thought_tokens_as_reasoning():
    from agent.gemini_native_adapter import translate_gemini_response

    response = translate_gemini_response(
        {
            "candidates": [{"content": {"parts": [{"text": "answer"}]}, "finishReason": "STOP"}],
            "usageMetadata": {
                "promptTokenCount": 10,
                "candidatesTokenCount": 5,
                "thoughtsTokenCount": 20,
                "totalTokenCount": 35,
            },
        },
        model="gemini-4-argon",
    )

    assert response.usage.completion_tokens == 25
    assert response.usage.total_tokens == 35
    assert response.usage.completion_tokens_details.reasoning_tokens == 20


def test_continuation_hops_merge_parts_and_usage():
    from agent.gemini_long_decode import merge_hop_responses, continuation_token

    first = _hop("part one ", "CONTINUATION", token="tok-1", prompt=100, output=32_768)
    second = _hop("part two", "STOP", token=None, prompt=32_868, output=500)

    assert continuation_token(first) == "tok-1"
    assert continuation_token(second) is None
    merged = merge_hop_responses([first, second])
    candidate = merged["candidates"][0]
    assert [part["text"] for part in candidate["content"]["parts"]] == ["part one ", "part two"]
    assert merged["usageMetadata"] == {
        "promptTokenCount": 32_968,
        "candidatesTokenCount": 33_268,
        "totalTokenCount": 66_236,
        "initialPromptTokenCount": 100,
    }


def test_stream_continuation_holds_finish_and_restores_usage_on_final_event():
    from agent.gemini_long_decode import split_stream_continuation

    held_usage: list[dict] = []
    first = _hop("part one", "CONTINUATION", token="tok-1", prompt=100, output=32_768)
    final = _hop("part two", "STOP", token=None, prompt=32_868, output=500)

    visible, token = split_stream_continuation(first, held_usage)
    assert token == "tok-1"
    assert visible["candidates"][0]["finishReason"] is None if "finishReason" in visible["candidates"][0] else True
    assert held_usage == [first["usageMetadata"]]

    visible, token = split_stream_continuation(final, held_usage)
    assert token is None
    assert visible["usageMetadata"]["initialPromptTokenCount"] == 100
    assert visible["usageMetadata"]["totalTokenCount"] == 66_236
