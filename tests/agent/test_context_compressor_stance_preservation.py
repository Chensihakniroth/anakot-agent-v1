"""Uncertain claims stay labelled through compaction (upstream ``73bfb9ce``).

Compression sheds qualifier words first, so "I suspect X" either hardens into "X" — a fact the
resumed agent acts on — or drops out and loses the investigative thread. The summarizer prompt
therefore asks for an explicit labelled UNVERIFIED section on both the fresh and the
iterative-update path, and the rule text lives in a sibling module so it can never leak into the
system prompt or the persisted handoff prefix.
"""

from types import SimpleNamespace

from agent.context_compressor import ContextCompressor
from agent.context_compressor_prompt_rules import (
    EPISTEMIC_STANCE_RULE,
    UNVERIFIED_HYPOTHESES_SECTION,
    UNVERIFIED_SECTION_HEADING,
    _today_for_prompt,
)


def _stub(*, previous_summary=None):
    stub = SimpleNamespace(
        tail_mode="lean",
        _previous_summary=previous_summary,
        _bound_summary_input=lambda text: text,
    )
    stub._summary_template_sections = ContextCompressor._summary_template_sections
    stub._build_summary_prompt = ContextCompressor._build_summary_prompt.__get__(stub)
    return stub


def test_the_stance_rule_is_in_both_summarizer_prompt_forms():
    fresh = _stub()._build_summary_prompt("NEW TURNS", 2000, None, "", True)
    update = _stub(previous_summary="PREVIOUS SUMMARY BODY")._build_summary_prompt("NEW TURNS", 2000, None, "", True)

    for prompt in (fresh, update):
        assert EPISTEMIC_STANCE_RULE in prompt
        assert "UNVERIFIED: <claim> — <basis>" in prompt


def test_the_template_advertises_the_section_exactly_once():
    template = ContextCompressor._summary_template_sections(
        {"historical_task": "h", "goal": "g", "constraints": "c", "resolved_questions": "r"},
        2000, "")
    assert template.count(UNVERIFIED_SECTION_HEADING) == 1
    assert UNVERIFIED_HYPOTHESES_SECTION.strip() in template


def test_the_rule_text_never_reaches_the_system_prompt():
    """The rule is interpolated into the summarizer prompt only; a system-prompt leak would
    re-parse it on every turn and break prompt-cache stability."""
    import agent.prompt_builder as prompt_builder

    source = prompt_builder.__file__
    with open(source, encoding="utf-8") as fh:
        body = fh.read()
    assert "EPISTEMIC_STANCE_RULE" not in body
    assert "UNVERIFIED: <claim>" not in body


def test_the_moved_date_helper_still_resolves():
    assert _today_for_prompt() == "" or len(_today_for_prompt()) == 10
