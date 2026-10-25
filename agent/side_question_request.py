"""One text-only request for a plugin-owned side question.

The first vertical slice keeps the request on a detached cache-parity fork and never dispatches
its tool calls. The lease layer owns consent, turn ownership, expiry, and profile binding.
"""

from __future__ import annotations

import contextvars
import copy
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

PLUGIN_SIDE_QUESTION_TASK = "side_question"
_CLIENT_TOOL_TYPES = frozenset({"function", "custom"})
_ROUTING_ONLY_OPENROUTER_PLUGINS = frozenset({"pareto-router"})


@dataclass(frozen=True)
class SideQuestionCapture:
    """Frozen parent inputs captured after a completed turn."""

    parent_ref: Any
    messages: list[dict[str, Any]]
    system_prompt: Optional[str]
    system_prompt_static: Optional[str]
    tools: list[dict[str, Any]]
    session_id: str
    turn_id: str
    runtime: tuple
    context: contextvars.Context = field(repr=False)


def runtime_key(agent: Any) -> tuple:
    """Runtime fields whose change would invalidate the captured request."""
    return tuple(
        getattr(agent, name, None)
        for name in ("model", "provider", "base_url", "api_mode", "reasoning_config")
    )


def _agent_provider_refusal(agent: Any) -> Optional[str]:
    """Refuse runtimes where the remote provider could execute tools outside our control."""
    if getattr(agent, "provider", None) == "moa":
        return "moa"
    if getattr(agent, "api_mode", None) == "codex_app_server":
        return "agent_provider"
    base_url = str(getattr(agent, "base_url", "") or "").lower()
    if base_url.startswith(("acp://", "acp+tcp://")):
        return "agent_provider"
    try:
        from agent.background_review import _parent_can_emit_tool_calls
        if not _parent_can_emit_tool_calls(agent):
            return "agent_provider"
    except Exception:
        pass
    return None


def _record_usage(parent: Any, fork: Any, plugin_id: str) -> dict[str, Any]:
    """Attribute the detached request to the issuing session without touching its transcript."""
    from agent.background_review import _snapshot_review_usage

    usage = _snapshot_review_usage(fork)
    try:
        session_db = getattr(parent, "_session_db", None)
        session_id = getattr(parent, "session_id", None)
        if session_db is not None and session_id and int(usage.get("api_calls") or 0):
            counts = {
                key: int(usage.get(key) or 0)
                for key in (
                    "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens",
                    "reasoning_tokens",
                )
            }
            session_db.record_auxiliary_usage(
                session_id,
                task=f"{PLUGIN_SIDE_QUESTION_TASK}:{plugin_id or '?'}",
                model=usage.get("model"),
                billing_provider=usage.get("provider"),
                billing_base_url=usage.get("base_url"),
                estimated_cost_usd=usage.get("estimated_cost_usd"),
                api_call_count=int(usage.get("api_calls") or 0),
                **counts,
            )
    except Exception:
        logger.debug("Plugin side-question usage recording failed", exc_info=True)
    return usage


def has_server_side_tools(api_kwargs: dict[str, Any]) -> bool:
    """Refuse request payloads that ask the provider to execute a server-side tool."""
    extra_body = api_kwargs.get("extra_body") if isinstance(api_kwargs.get("extra_body"), dict) else {}
    tools = [*(api_kwargs.get("tools") or ()), *(extra_body.get("tools") or ())]
    if any(
        isinstance(tool, dict)
        and tool.get("type")
        and tool.get("type") not in _CLIENT_TOOL_TYPES
        for tool in tools
    ):
        return True
    if "web_search_options" in api_kwargs or "web_search_options" in extra_body:
        return True
    plugins = [*(api_kwargs.get("plugins") or ()), *(extra_body.get("plugins") or ())]
    return any(
        not (isinstance(item, dict) and item.get("id") in _ROUTING_ONLY_OPENROUTER_PLUGINS)
        for item in plugins
    )


def ask_text_only(
    capture: SideQuestionCapture,
    prompt: str,
    *,
    plugin_id: str = "",
    timeout: float = 15.0,
) -> Optional[str]:
    """Run one detached, tool-denied side question and return visible text or None."""
    parent = capture.parent_ref()
    if parent is None:
        return None
    refusal = _agent_provider_refusal(parent)
    if refusal is not None:
        logger.info("side_question plugin=%s outcome=refused:%s", plugin_id, refusal)
        return None
    from agent.background_review import build_cache_parity_fork
    from agent.side_question import trim_snapshot_for_fork
    from anakot_cli.plugins import clear_thread_tool_whitelist, set_thread_tool_whitelist
    from agent.auxiliary_hooks import finish_aux_call_hooks, start_aux_call_hooks
    from agent.relay_llm import complete_logical_call
    from agent.turn_api_call import perform_api_call
    from agent.turn_api_request import build_request_payload
    from agent.turn_context import _PER_TURN_RESET_STATE
    from agent.turn_request_assembly import assemble_api_request
    from agent.turn_retry_state import TurnRetryState
    from agent.turn_truncation import normalize_response_for_agent
    from agent.turn_usage import record_response_usage

    fork = None
    timed_out = threading.Event()
    timer = None

    def _interrupt() -> None:
        timed_out.set()
        if fork is not None:
            try:
                fork.interrupt(None, tool_reason="plugin side question timed out")
            except Exception:
                logger.debug("Plugin side-question timeout interrupt failed", exc_info=True)

    try:
        timer = threading.Timer(max(float(timeout), 0.001), _interrupt)
        timer.daemon = True
        timer.start()
        fork, _runtime, _routed = build_cache_parity_fork(
            parent, {}, max_iterations=1, write_origin=PLUGIN_SIDE_QUESTION_TASK,
        )
        if timed_out.is_set() or runtime_key(parent) != capture.runtime:
            return None
        fork._cached_system_prompt = capture.system_prompt
        fork._cached_system_prompt_static = capture.system_prompt_static
        fork.tools = copy.deepcopy(capture.tools)
        fork.valid_tool_names = {
            tool["function"]["name"]
            for tool in fork.tools
            if isinstance(tool, dict) and isinstance(tool.get("function"), dict)
            and isinstance(tool["function"].get("name"), str)
        }
        fork.session_id = capture.session_id
        set_thread_tool_whitelist(
            set(),
            deny_msg_fmt=(
                "Plugin side question denied tool call: {tool_name}. "
                "Tools are disabled; answer directly from the captured conversation."
            ),
        )
        snapshot = trim_snapshot_for_fork(capture.messages)
        turn_id = f"{capture.turn_id}:{PLUGIN_SIDE_QUESTION_TASK}"
        task_id = str(uuid.uuid4())
        api_request_id = f"{turn_id}:api:1"
        for name, value in _PER_TURN_RESET_STATE:
            setattr(fork, name, value)
        fork._current_turn_timestamp = time.time()
        fork._current_turn_id = turn_id
        fork._current_task_id = task_id
        fork._current_api_request_id = api_request_id
        fork._disable_streaming = True
        messages = snapshot + [{
            "role": "user",
            "content": (
                "Answer ONLY this plugin side question from the captured conversation. "
                "Do not continue the main task, call tools, or guess.\n\n"
                f"Side question: {prompt}"
            ),
        }]
        assembled = assemble_api_request(
            fork,
            messages=messages,
            current_turn_user_idx=len(messages) - 1,
            _ext_prefetch_cache=None,
            _plugin_user_context=None,
            moa_config=None,
            active_system_prompt=fork._cached_system_prompt,
            original_user_message=prompt,
            pending_moa_prepared_request=None,
            request_logger=logger,
        )
        built = build_request_payload(
            fork,
            api_messages=assembled.api_messages,
            _moa_prepared_request=assembled._moa_prepared_request,
            tools_for_api=assembled.tools_for_api,
            system_message=None,
            api_call_count=1,
            api_request_id=api_request_id,
            effective_task_id=task_id,
            turn_id=turn_id,
        )
        if has_server_side_tools(built.api_kwargs) or timed_out.is_set():
            return None
        hooks = start_aux_call_hooks(
            aux_task=PLUGIN_SIDE_QUESTION_TASK,
            metadata={"api_request_id": api_request_id, "plugin_id": plugin_id},
            client=fork.client,
            kwargs=built.api_kwargs,
            provider=str(fork.provider or ""),
            model=str(fork.model or ""),
            api_mode=str(fork.api_mode or ""),
            streaming=False,
        )
        start = time.time()
        try:
            verdict = perform_api_call(
                fork,
                api_kwargs=built.api_kwargs,
                _original_api_kwargs=built._original_api_kwargs,
                _llm_middleware_trace=built._llm_middleware_trace,
                _moa_prepared_request=None,
                _retry=TurnRetryState(),
                thinking_spinner=None,
                retry_count=0,
                api_call_count=1,
                api_request_id=api_request_id,
                effective_task_id=task_id,
                turn_id=turn_id,
                interrupted=False,
            )
            response = None if verdict.action == "break" else verdict.response
            if response is not None:
                record_response_usage(
                    fork,
                    response,
                    messages=messages,
                    api_call_count=1,
                    api_duration=time.time() - start,
                    compression_attempts=0,
                    max_compression_attempts=0,
                )
                assistant_message = normalize_response_for_agent(fork, response)
                normalized = (
                    assistant_message,
                    getattr(assistant_message, "finish_reason", "stop"),
                    getattr(fork, "_usage_summary_for_api_request_hook", lambda _response: None)(response),
                )
        except BaseException as exc:
            finish_aux_call_hooks(hooks, error=exc)
            complete_logical_call(api_request_id, outcome="failed")
            raise
        if response is None:
            finish_aux_call_hooks(hooks, error=InterruptedError("side question cancelled"))
            complete_logical_call(api_request_id, outcome="cancelled")
            return None
        complete_logical_call(api_request_id, outcome="success")
        finish_aux_call_hooks(hooks, response, normalized=normalized)
        content = assistant_message.content
        if not isinstance(content, str):
            from agent.message_content import flatten_message_text
            content = flatten_message_text(content)
        return fork._strip_think_blocks(content or "").strip() or None
    except Exception:
        logger.warning("Plugin side question failed", exc_info=True)
        return None
    finally:
        if timer is not None:
            timer.cancel()
        clear_thread_tool_whitelist()
        if fork is not None:
            _record_usage(parent, fork, plugin_id)
            for cleanup in (fork.shutdown_memory_provider, fork.close):
                try:
                    cleanup()
                except Exception:
                    logger.debug("Plugin side-question cleanup failed", exc_info=True)
