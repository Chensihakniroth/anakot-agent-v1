"""MCP server deadlines must survive the outer tool executor."""

from __future__ import annotations

import json
from types import SimpleNamespace

import agent.tool_dispatch_helpers as dispatch_helpers
from tools.registry import registry


_TOOL_NAME = "mcp__deadline_probe__slow"


def _tool_call(name: str, arguments: dict | None = None):
    return SimpleNamespace(
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments or {}))
    )


def test_registered_deadline_extends_only_its_own_call():
    from agent.tool_dispatch_helpers import _extend_tool_timeout

    registry.register(
        name=_TOOL_NAME,
        toolset="mcp-deadline-probe",
        schema={"name": _TOOL_NAME, "parameters": {"type": "object"}},
        handler=lambda _args, **_kwargs: "ok",
        execution_timeout=1000,
    )
    try:
        assert _extend_tool_timeout(_TOOL_NAME, 420) == 1000
        assert _extend_tool_timeout("read_file", 420) == 420
        assert _extend_tool_timeout(_TOOL_NAME, 1200) == 1200
        assert _extend_tool_timeout(_TOOL_NAME, None) is None
    finally:
        registry.deregister(_TOOL_NAME)


def test_extended_deadline_is_a_sequential_barrier(monkeypatch):
    registry.register(
        name=_TOOL_NAME,
        toolset="mcp-deadline-probe",
        schema={"name": _TOOL_NAME, "parameters": {"type": "object"}},
        handler=lambda _args, **_kwargs: "ok",
        execution_timeout=1000,
    )
    monkeypatch.setattr(
        dispatch_helpers,
        "_PARALLEL_SAFE_TOOLS",
        dispatch_helpers._PARALLEL_SAFE_TOOLS | {_TOOL_NAME},
    )
    try:
        assert dispatch_helpers._batch_admission(_tool_call(_TOOL_NAME), None) is None
    finally:
        registry.deregister(_TOOL_NAME)


def test_mcp_registration_carries_server_timeout_to_registry():
    from tools.mcp_tool_registration import _Candidate, _register_candidates

    candidate = _Candidate(
        registry_name=_TOOL_NAME,
        origin="slow",
        schema={"name": _TOOL_NAME, "parameters": {"type": "object"}},
        handler=lambda _args, **_kwargs: "ok",
    )
    registered = _register_candidates(
        "deadline_probe",
        [candidate],
        check_fn=lambda: True,
        scope=lambda: None,
        lazy=False,
        execution_timeout=1000,
    )
    try:
        assert registered == [_TOOL_NAME]
        entry = registry.get_entry(_TOOL_NAME)
        assert entry is not None
        assert entry.execution_timeout == 1000
    finally:
        registry.deregister(_TOOL_NAME)
