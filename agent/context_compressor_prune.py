"""Proactive tool-result pruning mixin.

The main compressor owns the deterministic pruning mechanics; this sibling owns the
cache-breaking admission/commit boundary and keeps it separate from summary generation.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger("agent.context_compressor")


def _cc():
    from agent import context_compressor
    return context_compressor


class ProactivePruneMixin:
    """No-LLM tool-result reclamation with profile/session-safe persistence."""

    def _prune_history_is_current(self, session_db: Any, session_id: str, messages: list[dict[str, Any]]) -> bool:
        """Fail closed when the newest durable row this prune held was superseded."""
        role_getter = getattr(session_db, "get_message_role", None)
        if not callable(role_getter):
            return True
        marker = _cc()._DB_PERSISTED_MARKER
        held_ids = [
            message.get("_row_id")
            for message in messages
            if isinstance(message, dict)
            and message.get(marker)
            and isinstance(message.get("_row_id"), int)
            and not isinstance(message.get("_row_id"), bool)
        ]
        if not held_ids:
            return True
        try:
            return role_getter(session_id, max(held_ids)) is not None
        except Exception as exc:
            logger.info("Proactive prune skipped: unable to validate the held history generation: %s", exc)
            return False

    def prune_tool_results_only(
        self, messages: list[dict[str, Any]], current_tokens: int | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        if self.proactive_prune_tokens <= 0 or (
            current_tokens is not None and current_tokens < self.proactive_prune_tokens
        ):
            return messages, 0
        if len(messages) <= self.protect_last_n + self._protect_head_size(messages) + 1:
            self._warn_reclamation_no_op("prune:tail_only", current_tokens)
            return messages, 0
        estimate = _cc()._estimate_msg_budget_tokens
        before = sum(estimate(message) for message in messages)
        if before < self._proactive_prune_rearm_tokens and not self._billed_basis_over_threshold(current_tokens):
            return messages, 0

        session_db = getattr(self, "_session_db", None)
        session_id = getattr(self, "_session_id", "")
        if session_db and session_id and not callable(getattr(session_db, "archive_and_compact", None)):
            self._warn_reclamation_no_op("prune:store_cannot_persist", current_tokens)
            return messages, 0
        watermark = None
        watermark_getter = getattr(session_db, "get_active_message_watermark", None)
        if session_db and session_id and callable(watermark_getter):
            try:
                # Capture this before the deterministic pass. Rows appended while
                # the prune is being prepared must remain a concurrent tail.
                watermark = watermark_getter(session_id)
            except Exception as exc:
                logger.info("Proactive prune skipped: unable to capture the history watermark: %s", exc)
                return messages, 0

        pruned, count = self._prune_old_tool_results(
            messages,
            protect_tail_count=self.protect_last_n,
            protect_tail_tokens=None,
            min_prune_chars=self.proactive_prune_min_result_chars,
        )
        from agent.context_compressor_tail import with_pruned_row_skill_safety_rule
        pruned = with_pruned_row_skill_safety_rule(messages, pruned)
        if not count:
            self._warn_reclamation_no_op("prune:nothing_eligible", current_tokens)
            return messages, 0

        after = sum(estimate(message) for message in pruned)
        reclaimed = max(0, before - after)
        if reclaimed < self.proactive_prune_min_reclaim_tokens:
            self._warn_reclamation_no_op("prune:reclaim_below_minimum", current_tokens, before=before)
            return messages, 0

        runway = max(reclaimed, self.proactive_prune_tokens, self.proactive_prune_min_reclaim_tokens)
        next_rearm = after + runway
        if session_db and session_id:
            try:
                if not self._prune_history_is_current(session_db, session_id, messages):
                    self._warn_reclamation_no_op("prune:stale_generation", current_tokens, before=before)
                    return messages, 0
                session_db.archive_and_compact(
                    session_id,
                    pruned,
                    model_config_patch={_cc().PROACTIVE_PRUNE_REARM_MODEL_CONFIG_KEY: next_rearm},
                    watermark=watermark,
                )
            except Exception as exc:
                logger.warning("Proactive tool-result prune DB commit failed; keeping the original transcript: %s", exc)
                return messages, 0
            _cc().stamp_db_persisted_markers(pruned)
        self._proactive_prune_rearm_tokens = next_rearm
        self._last_reclaim_block_warn = None
        return pruned, count

    def _rewrite_pruned_rows_in_place(
        self, session_db: Any, session_id: str, messages: list[dict[str, Any]],
        pruned_msgs: list[dict[str, Any]], model_config_patch: dict[str, Any],
    ) -> Optional[int]:
        rewrite = getattr(session_db, "rewrite_pruned_rows", None)
        if not callable(rewrite) or len(messages) != len(pruned_msgs):
            return None
        ignored = {_cc()._DB_PERSISTED_MARKER, "_row_id"}
        changes: list[tuple] = []
        unwritten_seen = False
        for original, replacement in zip(messages, pruned_msgs):
            if not isinstance(original, dict) or not isinstance(replacement, dict):
                return None
            if not original.get(_cc()._DB_PERSISTED_MARKER):
                unwritten_seen = True
                continue
            if unwritten_seen:
                return None
            old = {key: value for key, value in original.items() if key not in ignored}
            new = {key: value for key, value in replacement.items() if key not in ignored}
            if old != new:
                changes.append((original, replacement))
        try:
            return rewrite(session_id, changes, model_config_patch=model_config_patch)
        except Exception as exc:
            logger.info("Proactive prune in-place rewrite refused: %s", exc)
            return None
