"""Transcript repair for SessionDB batch appends: reconcile in-memory assistant rows with committed SQLite
rows (blank-row in-place update, concurrent-winner adoption, watermark-compaction clone lookup) and sync
markers after commit."""

from __future__ import annotations

import sqlite3
import json
from typing import Any, Callable, Dict, List

from agent.context_compressor import _DB_PERSISTED_MARKER


def is_content_blank(content: Any) -> bool:
    """True when decoded message content is None, whitespace-only, or has no visible text parts."""
    if content is None:
        return True
    if isinstance(content, str):
        return not content.strip()
    if isinstance(content, list):
        return not "".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text").strip()
    return False


def resolve_and_repair_transcript_batch(
    conn: sqlite3.Connection,
    session_id: str,
    messages: List[Dict[str, Any]],
    encode_content_fn: Callable[[Any], Any],
    decode_content_fn: Callable[[Any], Any],
) -> List[Dict[str, Any]]:
    """Partition a message batch within an active write transaction. An assistant message carrying an
    existing integer ``_row_id`` targets its active SQLite row (or the active clone a watermark compaction
    made of it): a blank row is updated in place; a non-blank one (concurrent winner) has its canonical
    content adopted without overwrite. Returns the messages that must be inserted as fresh rows."""
    inserted_rows: List[Dict[str, Any]] = []
    for msg in messages:
        existing_row_id = msg.get("_row_id") if isinstance(msg, dict) else None
        target_row = None
        if isinstance(existing_row_id, int) and msg.get("role", "unknown") == "assistant":
            target_row = _active_assistant_row(conn, session_id, existing_row_id)
        if target_row is None:
            inserted_rows.append(msg)
            continue
        target_id = int(target_row["id"])
        decoded = decode_content_fn(target_row["content"])
        msg["_row_id"] = target_id
        if is_content_blank(decoded) or decoded == msg.get("content"):
            conn.execute(
                "UPDATE messages SET content = ?, tool_calls = ?, message_uid = ?, "
                "absorbed_message_uids = ?, tool_call_uids = ?, tool_call_uid = ? "
                "WHERE id = ? AND session_id = ? AND active = 1",
                _row_rewrite_params(target_row, msg, encode_content_fn, target_id, session_id),
            )
        else:
            msg["_canonical_content"] = decoded  # concurrent winner: adopt, don't overwrite
    return inserted_rows


def _row_rewrite_params(target_row, msg, encode_content_fn, target_id: int, session_id: str) -> tuple:
    """Rewrite a same-content assistant row's calls and durable identities without losing legacy metadata."""
    from agent.message_metadata import (
        ABSORBED_MESSAGE_UIDS, MESSAGE_UID, TOOL_CALL_UID, TOOL_CALL_UIDS, stamp_message_uid,
    )
    from anakot_state_identity import (
        _absorbed_uids_json, _fill_missing_tool_call_uids, _tool_call_uid_or_none, _tool_call_uids_json,
    )

    _fill_missing_tool_call_uids(target_row, msg)
    calls = msg.get("tool_calls")
    if isinstance(calls, str):
        try:
            calls = json.loads(calls)
        except json.JSONDecodeError:
            calls = []
    encoded_calls = json.dumps(calls) if isinstance(calls, list) and calls else None
    if not msg.get(MESSAGE_UID) and target_row["message_uid"]:
        msg[MESSAGE_UID] = target_row["message_uid"]
    uid = stamp_message_uid(msg)
    absorbed = (_absorbed_uids_json(msg) if ABSORBED_MESSAGE_UIDS in msg
                else target_row["absorbed_message_uids"])
    tool_uids = (_tool_call_uids_json(msg) if TOOL_CALL_UIDS in msg
                 else target_row["tool_call_uids"])
    tool_call_uid = (_tool_call_uid_or_none(msg) if TOOL_CALL_UID in msg
                     else target_row["tool_call_uid"])
    return (encode_content_fn(msg.get("content")), encoded_calls, uid, absorbed, tool_uids,
            tool_call_uid, target_id, session_id)


def _active_assistant_row(conn: sqlite3.Connection, session_id: str, row_id: int):
    """The active assistant row for ``row_id``, or the active clone a watermark compaction made of it."""
    row = conn.execute(
        "SELECT id, role, active, timestamp, content, tool_calls, message_uid, "
        "absorbed_message_uids, tool_call_uids, tool_call_uid FROM messages "
        "WHERE id = ? AND session_id = ?",
        (row_id, session_id),
    ).fetchone()
    if row is None or row["role"] != "assistant":
        return None
    if int(row["active"] or 0) == 1:
        return row
    # Watermark compaction soft-archived the concurrent tail and cloned it.
    return conn.execute(
        "SELECT id, role, active, timestamp, content, tool_calls, message_uid, "
        "absorbed_message_uids, tool_call_uids, tool_call_uid FROM messages "
        "WHERE session_id = ? AND active = 1 AND role = 'assistant' "
        "AND timestamp IS ? AND id != ? "
        "ORDER BY id DESC LIMIT 1",
        (session_id, row["timestamp"], row["id"]),
    ).fetchone()


def sync_flushed_message_markers(batch_msgs: List[Dict[str, Any]], batch_rows: List[Dict[str, Any]]) -> None:
    """Stamp _DB_PERSISTED_MARKER and sync canonical row ID / content onto live dicts after commit."""
    from agent.message_metadata import copy_identity_fields

    for written, row in zip(batch_msgs, batch_rows):
        written[_DB_PERSISTED_MARKER] = True
        if isinstance(row.get("_row_id"), int):
            written["_row_id"] = row["_row_id"]
        if "timestamp" in row:
            written["timestamp"] = row["timestamp"]
        copy_identity_fields(row, written)
        if "_canonical_content" in row:
            written["content"] = row["_canonical_content"]


# ---- BEGIN PLUGIN-COMPAT (revert-scheduled; see COMPAT_MANIFEST.md) ----
# Names external plugins imported from this module before the Sep 2026 decomposition.
# Internal code MUST NOT use these (scripts/check_compat_pointers.py fails CI if it does).
# The whole block is removed by reverting the commit that added it.
from typing import Optional  # noqa: F401,E402
# ---- END PLUGIN-COMPAT ----
