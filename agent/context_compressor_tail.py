"""Lean-tail helpers and compaction-only Skill Safety Rule handoff."""

from __future__ import annotations

import re
from typing import Any

_LEAN_TAIL_KEEP_TOOL_ROUNDS = 6
_LEAN_TAIL_DEMOTE_MIN_CHARS = 1_500
TAIL_MAX_THRESHOLD_FRACTION = 0.50
_DEMOTED_STUB_RE = re.compile(
    r"\[[^\s\]]* output demoted at compaction — [\d,]+ chars preserved in session history\."
)


def lean_tail_budget(context_length: int, threshold_tokens: int) -> int:
    """Return the lean tail budget, bounded by half of the compression trigger."""
    from agent.context_compressor import _MIN_SUMMARY_TOKENS, LEAN_TAIL_CAP_TOKENS, LEAN_TAIL_FLOOR_TOKENS

    floor = LEAN_TAIL_FLOOR_TOKENS
    window_term = min(LEAN_TAIL_CAP_TOKENS, int(context_length * 0.025))
    if threshold_tokens > 0:
        share = int(threshold_tokens * TAIL_MAX_THRESHOLD_FRACTION)
        floor = min(floor, share)
        if threshold_tokens > _MIN_SUMMARY_TOKENS:
            window_term = min(window_term, share)
    return max(floor, window_term)


def is_demoted_stub(content: str) -> bool:
    """Return whether a tool row is already a compaction recovery stub."""
    return len(content) < 1_000 and _DEMOTED_STUB_RE.match(content) is not None


def _lean_recovery_stub(tool_name: str, content_len: int, session_id: str) -> str:
    hint = f" Recover with session_search(query=..., session_id='{session_id}')" if session_id else ""
    return (
        f"[{tool_name or 'tool'} output demoted at compaction — {content_len:,} "
        f"chars preserved in session history.{hint}]"
    )


def skill_view_names_by_call_id(messages: list[dict[str, Any]]) -> dict[str, str]:
    """Map ``skill_view`` call ids to the skill name loaded by the call."""
    from agent.context_compressor import _json_dict, _tc_get

    names: dict[str, str] = {}
    for msg in messages:
        if msg.get("role") != "assistant":
            continue
        for tc in msg.get("tool_calls") or []:
            fn = _tc_get(tc, "function", {})
            if _tc_get(fn, "name") != "skill_view":
                continue
            skill = _json_dict(_tc_get(fn, "arguments")).get("name")
            if isinstance(skill, str) and skill:
                names[str(_tc_get(tc, "id") or "")] = skill
    return names


def demote_stale_tail_tools(
    messages: list[dict[str, Any]], tail_start: int, session_id: str,
) -> tuple[list[dict[str, Any]], int]:
    """Demote stale tail tool output and preserve a reload marker for skill results."""
    from agent.context_compressor import (
        SKILL_PRUNED_MARKER_PREFIX, _is_summary_stub, _rewritten, _skill_pruned_marker,
    )

    rounds_seen = 0
    protected: set[int] = set()
    previous = None
    for i in (i for i in range(len(messages) - 1, tail_start - 1, -1) if messages[i].get("role") == "tool"):
        rounds_seen += previous is None or previous - i > 1
        previous = i
        if rounds_seen > _LEAN_TAIL_KEEP_TOOL_ROUNDS:
            break
        protected.add(i)

    result = list(messages)
    skills: dict[str, str] | None = None
    demoted = 0
    for i in range(tail_start, len(messages)):
        msg = messages[i]
        content = msg.get("content")
        if msg.get("role") != "tool" or i in protected or not isinstance(content, str):
            continue
        if (
            len(content) < _LEAN_TAIL_DEMOTE_MIN_CHARS
            or SKILL_PRUNED_MARKER_PREFIX in content
            or _is_summary_stub(content)
            or is_demoted_stub(content)
        ):
            continue
        stub = _lean_recovery_stub(msg.get("tool_name") or "", len(content), session_id)
        if skills is None:
            skills = skill_view_names_by_call_id(messages)
        skill = skills.get(str(msg.get("tool_call_id") or ""))
        if skill and not content.lstrip().lower().startswith(("error", "[error")):
            stub += " " + _skill_pruned_marker(skill)
        result[i] = _rewritten(msg, stub)
        demoted += 1
    return result, demoted


SKILL_SAFETY_HEADING = "## Skill Safety Rule"
SKILL_SAFETY_RULE = (
    f"{SKILL_SAFETY_HEADING}\n"
    "A skill placeholder containing `[SKILL_PRUNED]` lost its content in context compression and is inaccessible — "
    "reload it with skill_view(name='...') before acting on anything that depends on it. After reloading, ignore any "
    "remaining `[SKILL_PRUNED]` markers for that same skill; they are historical artifacts of earlier compactions."
)
_SKILL_SAFETY_SUFFIX = f"\n\n{SKILL_SAFETY_RULE}"


def without_skill_safety_rule(content: str) -> str:
    """Remove a previously attached safety rule from a compaction row."""
    return content.replace(_SKILL_SAFETY_SUFFIX, "")


def with_skill_safety_rule(
    summary: str, head: list[dict[str, Any]], tail: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    """Attach the rule exactly once when a kept compaction row contains a prune marker."""
    from agent.context_compressor import SKILL_PRUNED_MARKER_PREFIX, _content_text_for_contains

    def unrule(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {**row, "content": without_skill_safety_rule(row["content"])}
            if isinstance(row, dict) and row.get("role") != "system"
            and isinstance(row.get("content"), str) and SKILL_SAFETY_RULE in row["content"]
            else row
            for row in rows
        ]

    head, tail = unrule(head), unrule(tail)
    texts = (
        summary,
        *(_content_text_for_contains(row.get("content")) for row in (*head, *tail) if isinstance(row, dict)),
    )
    if any(SKILL_SAFETY_RULE in text for text in texts) or not any(
        SKILL_PRUNED_MARKER_PREFIX in text for text in texts
    ):
        return summary, head, tail
    return f"{summary}{_SKILL_SAFETY_SUFFIX}", head, tail


def with_pruned_row_skill_safety_rule(
    original: list[dict[str, Any]], pruned: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Put the rule on a prune-only row when no summary handoff exists."""
    from agent.context_compressor import SKILL_PRUNED_MARKER_PREFIX, _content_text_for_contains

    if any(SKILL_SAFETY_RULE in _content_text_for_contains(row.get("content")) for row in pruned):
        return pruned
    for i, (before, after) in enumerate(zip(original, pruned)):
        content = after.get("content") if isinstance(after, dict) else None
        if (
            isinstance(content, str)
            and SKILL_PRUNED_MARKER_PREFIX in content
            and content != before.get("content")
        ):
            return [
                *pruned[:i],
                {**after, "content": content + _SKILL_SAFETY_SUFFIX},
                *pruned[i + 1:],
            ]
    return pruned
