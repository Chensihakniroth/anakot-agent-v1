"""Regression coverage for refresh gates and proactive-prune watermark forwarding."""

from types import SimpleNamespace


def _tool(name):
    return {"type": "function", "function": {"name": name, "description": "", "parameters": {}}}


def test_refresh_override_preserves_one_shot_disabled_surface(monkeypatch):
    from tools import mcp_tool_agent
    import model_tools

    agent = SimpleNamespace(
        enabled_toolsets=["anakot-cli"],
        disabled_toolsets=[],
        platform="cli",
        _oneshot_session=True,
        tools=[_tool("read_file")],
        valid_tool_names={"read_file"},
    )
    monkeypatch.setattr(
        model_tools,
        "get_tool_definitions",
        lambda **_: [_tool("read_file"), _tool("clarify")],
    )
    enabled, disabled = mcp_tool_agent._resolve_refresh_toolsets(agent, None, [])

    assert enabled == ["anakot-cli"]
    assert "clarify" in disabled
    assert agent.disabled_toolsets == disabled


def test_prune_forwards_active_watermark_and_preserves_concurrent_tail(monkeypatch):
    from agent.context_compressor_prune import ProactivePruneMixin

    class Compressor(ProactivePruneMixin):
        proactive_prune_tokens = 1
        proactive_prune_min_reclaim_tokens = 0
        proactive_prune_min_result_chars = 1
        protect_last_n = 0
        _proactive_prune_rearm_tokens = 0
        _last_reclaim_block_warn = None

        def _protect_head_size(self, messages):
            return 0

        def _billed_basis_over_threshold(self, current_tokens):
            return False

        def _warn_reclamation_no_op(self, *args, **kwargs):
            return None

        def _prune_old_tool_results(self, messages, **kwargs):
            copied = [dict(message) for message in messages]
            copied[0]["content"] = "short"
            return copied, 1

    class DB:
        def get_active_message_watermark(self, session_id):
            assert session_id == "s1"
            return 41

        def archive_and_compact(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    compressor = Compressor()
    compressor._session_db = DB()
    compressor._session_id = "s1"
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "tool", "content": "x" * 100},
    ]
    monkeypatch.setattr("agent.context_compressor._estimate_msg_budget_tokens", lambda _: 100)

    result, count = compressor.prune_tool_results_only(messages, current_tokens=10)

    assert count == 1
    assert result is not messages
    assert compressor._session_db.kwargs["watermark"] == 41
