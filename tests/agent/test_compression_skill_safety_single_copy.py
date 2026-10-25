"""Skill Safety Rule must survive prune-only, compaction, and salvage rewrites."""

from agent.context_compressor import salvage_grown_transcript
from agent.context_compressor_tail import SKILL_SAFETY_RULE, with_pruned_row_skill_safety_rule


def test_prune_only_attaches_rule_once_to_changed_skill_marker():
    marker = "[SKILL_PRUNED: content lost in compression; reload with skill_view(name='demo')]"
    original = [{"role": "tool", "content": "full skill body"}]
    pruned = [{"role": "tool", "content": marker}]
    result = with_pruned_row_skill_safety_rule(original, pruned)
    assert result[0]["content"].count(SKILL_SAFETY_RULE) == 1


def test_salvage_keeps_attached_rule_on_summary():
    summary = {
        "role": "user",
        "_compressed_summary": True,
        "content": "[CONTEXT COMPACTION]\n" + "x" * 9000 + "\n\n" + SKILL_SAFETY_RULE + "\n\n--- END OF CONTEXT SUMMARY — respond to the message below, not the summary above ---",
    }
    original = [{"role": "user", "content": "old"}, {"role": "assistant", "content": "answer"}]
    result = salvage_grown_transcript(original, [summary], budget=5000)
    assert result is not None
    assert SKILL_SAFETY_RULE in result[0]["content"]
