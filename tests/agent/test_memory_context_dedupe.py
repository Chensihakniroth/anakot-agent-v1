"""A recalled bullet is stated once per memory-context section.

Providers and stores can surface the same fact repeatedly. The composed block is replayed on later
requests, so byte-identical self-contained bullet repeats cost context forever. Structure and
entries with continuation lines must remain untouched.
"""

from __future__ import annotations

import pytest

from agent.memory_manager import build_memory_context_block


def _body(block: str) -> str:
    """Return provider content without the wrapper and system note."""
    return block.split("]\n\n", 1)[1].rsplit("\n</memory-context>", 1)[0]


def test_repeated_bullet_is_kept_once_per_section():
    """Repeats are removed only inside one section; any column-0 non-bullet starts a new section."""
    raw = "- alpha\n- beta\n- alpha\n- gamma\n"

    assert _body(build_memory_context_block(raw)).splitlines() == [
        "- alpha",
        "- beta",
        "- gamma",
    ]

    prose = "Profile:\n- None\nRelevant memories:\n- None\n"
    markdown = "## A\n- (none recorded)\n\n## B\n- (none recorded)\n"
    bold = "**A**\n- repeated\n**B**\n- repeated\n"
    numbered = "1. repeated\ntext\n2. repeated\n"

    assert _body(build_memory_context_block(prose)) == prose
    assert _body(build_memory_context_block(markdown)) == markdown
    assert _body(build_memory_context_block(bold)) == bold
    assert _body(build_memory_context_block(numbered)) == numbered


def test_bullet_with_continuation_or_indentation_is_never_deduped():
    """Continuation lines carry provenance, so neither they nor their parent bullet may be dropped."""
    continued = (
        "- prefers draft PRs\n  (logged 12 Jan, source: supermemory)\n"
        "- prefers draft PRs\n  (logged 3 Feb, source: builtin)\n"
    )
    blank_separated = (
        "- prefers draft PRs\n\n  (logged 12 Jan, source: supermemory)\n"
        "- prefers draft PRs\n\n  (logged 3 Feb, source: builtin)\n"
    )
    nested = "- Project A\n  - status: active\n- Project B\n  - status: active\n"
    indented = "  - repeated\n  - repeated\n"

    assert _body(build_memory_context_block(continued)) == continued
    assert _body(build_memory_context_block(blank_separated)) == blank_separated
    assert _body(build_memory_context_block(nested)) == nested
    assert _body(build_memory_context_block(indented)) == indented


@pytest.mark.parametrize(
    "rule",
    ["* * *", "- - -", "+ + +", "  ---", "   ***", "    ---"],
)
def test_thematic_break_resets_dedupe_section(rule):
    raw = f"- repeated\n{rule}\n- repeated\n"
    assert _body(build_memory_context_block(raw)) == raw


@pytest.mark.parametrize("separator", ["\u00a0", "\u000c", "\u000b"])
def test_non_commonmark_marker_separator_is_plain_continuation(separator):
    raw = f"- alpha\n-{separator}section\n- alpha\n"
    assert _body(build_memory_context_block(raw)) == raw


def test_lazy_nonindented_continuation_keeps_duplicate_bullet():
    raw = "- alpha\n- alpha\nlazy provenance\n"
    assert _body(build_memory_context_block(raw)) == raw


def test_bullets_inside_markdown_fences_are_untouched():
    fenced = "```text\n- example\n- example\n```\n"
    indented_fence = "  ```text\n  - example\n  - example\n  ```\n"

    assert _body(build_memory_context_block(fenced)) == fenced
    assert _body(build_memory_context_block(indented_fence)) == indented_fence


def test_dedupe_key_is_byte_identical_and_crlf_safe():
    trailing_space = "- alpha \n- alpha\n- alpha\n"
    assert _body(build_memory_context_block(trailing_space)) == "- alpha \n- alpha\n"

    body = _body(build_memory_context_block("- alpha\r\n- alpha\r\n"))
    assert body == "- alpha\r\n"
