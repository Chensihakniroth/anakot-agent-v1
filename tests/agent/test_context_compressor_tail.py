"""Compression-handoff safety rules and lean-tail budgeting."""

from agent.context_compressor_tail import (
    SKILL_SAFETY_RULE,
    lean_tail_budget,
    with_skill_safety_rule,
)


def test_skill_safety_rule_is_attached_once_to_compaction_handoff():
    marker = "[SKILL_PRUNED: content lost in compression; reload with skill_view(name='demo')]"
    summary, head, tail = with_skill_safety_rule("summary", [{"role": "tool", "content": marker}], [])
    assert SKILL_SAFETY_RULE in summary
    assert summary.count(SKILL_SAFETY_RULE) == 1
    assert head == [{"role": "tool", "content": marker}] and tail == []

    summary_again, _, _ = with_skill_safety_rule(summary, [], [])
    assert summary_again == summary


def test_skill_safety_rule_is_not_paid_for_in_fresh_compactions():
    summary, _, _ = with_skill_safety_rule("ordinary summary", [], [])
    assert SKILL_SAFETY_RULE not in summary


def test_lean_tail_budget_respects_small_trigger_cap():
    assert lean_tail_budget(1_000_000, 12_000) == 6_000
