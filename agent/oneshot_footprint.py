"""What a finite one-shot session (``anakot chat -q`` / ``--oneshot``, ``anakot -z``) does NOT do.

A one-shot run has no later session in its ANAKOT_HOME to learn for: the process answers one query and
exits. It keeps skill authoring available so a requested deliverable can still be created, but it drops
interactive-only clarification and live-control surfaces. The marker is the same
``ANAKOT_SINGLE_QUERY_SESSION`` the approval gate and delegation dispatcher read, so an interactive
session keeps the full surface.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

# A finite run still permits skill authoring when the task explicitly requires it.
# Interactive-only clarification is removed at the tool surface instead.
ONESHOT_HIDDEN_TOOLS = frozenset({"clarify"})
ONESHOT_DISABLED_TOOLSETS = ("clarify",)


def is_single_query_session() -> bool:
    """The finite ``-q`` marker, read through the session env so gateway-bound sessions never see it."""
    try:
        from gateway.session_context import get_session_env
    except Exception:
        import os
        get_session_env = os.environ.get
    return str(get_session_env("ANAKOT_SINGLE_QUERY_SESSION", "") or "") == "1"


def prune_oneshot_tools(tools: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """*tools* minus ``ONESHOT_HIDDEN_TOOLS``; identity when the session is not one-shot."""
    tools = list(tools)
    if not is_single_query_session():
        return tools
    return [t for t in tools if (t.get("function") or {}).get("name") not in ONESHOT_HIDDEN_TOOLS]


ONESHOT_SKILLS_LOAD_GUIDANCE = (
    "## Skills\n"
    "Scan the skills below and load one with skill_view(name) only when it carries domain knowledge you lack "
    "for THIS task (an API, a tool's commands, a project's conventions). Do not load general process skills "
    "(testing, debugging, review methodology) for work you already know how to do, and do not create or edit "
    "skills: this is a one-shot run with no later session to reuse them.\n"
)
