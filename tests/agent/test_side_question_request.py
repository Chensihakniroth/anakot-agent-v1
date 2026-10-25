"""Request-shape and lifecycle guards for plugin side questions."""

import contextvars
import weakref
from types import SimpleNamespace

from unittest.mock import Mock

from agent.side_question_request import has_server_side_tools


def test_client_function_tools_are_safe():
    assert has_server_side_tools({"tools": [{"type": "function", "function": {"name": "read_file"}}]}) is False
    assert has_server_side_tools({"tools": [{"type": "custom", "name": "lookup"}]}) is False


def test_server_side_tool_types_are_refused():
    assert has_server_side_tools({"tools": [{"type": "web_search"}]}) is True
    assert has_server_side_tools({"extra_body": {"tools": [{"type": "computer_use"}]}}) is True
    assert has_server_side_tools({"web_search_options": {}}) is True


def test_routing_only_plugin_is_safe_but_other_plugins_are_not():
    assert has_server_side_tools({"plugins": [{"id": "pareto-router"}]}) is False
    assert has_server_side_tools({"plugins": [{"id": "web-search"}]}) is True


def test_detached_request_suppresses_turn_hooks_and_wraps_auxiliary_hooks(monkeypatch):
    from agent import auxiliary_hooks, background_review, relay_llm, side_question, turn_api_call
    from agent.side_question_request import SideQuestionCapture, ask_text_only, runtime_key

    class Parent:
        model = "test/model"
        provider = "test-provider"
        base_url = "https://example.invalid/v1"
        api_mode = "openai"
        reasoning_config = None
        _cached_system_prompt = "system"
        _cached_system_prompt_static = "static"
        tools = []
        session_id = "session"
        _current_turn_id = "turn-1"
        _persist_disabled = False

    parent = Parent()
    fork = SimpleNamespace(
        model=parent.model,
        provider=parent.provider,
        base_url=parent.base_url,
        api_mode=parent.api_mode,
        reasoning_config=parent.reasoning_config,
        client=Mock(),
        tools=[],
        valid_tool_names=set(),
        session_id=parent.session_id,
        _strip_think_blocks=lambda text: text,
        shutdown_memory_provider=Mock(),
        close=Mock(),
        _persist_disabled=True,
    )
    fork._reset_stream_delivery_tracking = lambda: None
    fork._reapply_reasoning_echo_for_provider = lambda _messages: None
    fork._build_api_kwargs = lambda messages, tools_for_api=None: {
        "messages": messages, "tools": tools_for_api or [],
    }
    fork._empty_content_retries = 0
    fork._is_openrouter_url = lambda: False
    fork._is_copilot_url = lambda: False
    fork._usage_summary_for_api_request_hook = lambda _response: None
    fork._use_prompt_caching = False
    fork._force_ascii_payload = False
    fork.platform = "telegram"
    capture = SideQuestionCapture(
        parent_ref=weakref.ref(parent), messages=[], system_prompt="system",
        system_prompt_static="static", tools=[], session_id="session", turn_id="turn-1",
        runtime=runtime_key(parent), context=contextvars.copy_context(),
    )
    assembled = SimpleNamespace(
        api_messages=[{"role": "user", "content": "q"}], tools_for_api=[],
        _moa_prepared_request=None, approx_tokens=1, total_chars=1,
    )
    built = SimpleNamespace(
        api_kwargs={"messages": assembled.api_messages, "tools": []},
        _original_api_kwargs={}, _llm_middleware_trace=None,
        api_messages=assembled.api_messages,
    )
    response = SimpleNamespace(
        choices=[SimpleNamespace(
            message=SimpleNamespace(content="answer", tool_calls=None), finish_reason="stop",
        )],
        usage=None,
    )
    verdict = SimpleNamespace(action="fallthrough", response=response)
    calls = []

    monkeypatch.setattr(background_review, "build_cache_parity_fork", lambda *a, **k: (fork, None, False))
    monkeypatch.setattr(side_question, "trim_snapshot_for_fork", lambda messages: list(messages))
    monkeypatch.setattr(background_review, "_snapshot_review_usage", lambda _fork: {"api_calls": 1})
    monkeypatch.setattr(background_review, "_record_review_usage_to_parent", lambda *a, **k: None)
    monkeypatch.setattr(
        auxiliary_hooks,
        "run_with_aux_hooks",
        lambda call, **kwargs: (calls.append(kwargs), call())[1],
    )
    monkeypatch.setattr(turn_api_call, "perform_api_call", lambda *a, **k: verdict)
    monkeypatch.setattr(relay_llm, "complete_logical_call", lambda *a, **k: None)
    monkeypatch.setattr("agent.turn_request_assembly.assemble_api_request", lambda *a, **k: assembled)
    monkeypatch.setattr("agent.turn_api_request.build_api_request", lambda *a, **k: (calls.append(k), built)[1])
    monkeypatch.setattr("agent.turn_truncation.normalize_response_for_agent", lambda *a, **k: response.choices[0].message)
    monkeypatch.setattr("agent.turn_usage.record_response_usage", lambda *a, **k: None)
    monkeypatch.setattr("anakot_cli.plugins.set_thread_tool_whitelist", lambda *a, **k: None)
    monkeypatch.setattr("anakot_cli.plugins.clear_thread_tool_whitelist", lambda: None)

    assert ask_text_only(capture, "q", plugin_id="observer") == "answer"
    assert calls == []
    fork.shutdown_memory_provider.assert_called_once_with()
    fork.close.assert_called_once_with()
