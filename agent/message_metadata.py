"""Internal metadata attached to durable conversation messages."""

from __future__ import annotations

from collections import Counter
from time import time as wall_time
from typing import Any, List, Mapping, MutableMapping, Optional, TypeVar
from uuid import uuid4


# Transcript repair bookkeeping and durable message identity are not provider-visible content.
DB_ROW_SNAPSHOT = "_db_row_snapshot"
CANONICAL_ROW = "_canonical_row"
REPAIR_BOOKKEEPING_FIELDS = frozenset({DB_ROW_SNAPSHOT, CANONICAL_ROW})
MESSAGE_UID = "message_uid"
ABSORBED_MESSAGE_UIDS = "_absorbed_message_uids"
TOOL_CALL_UIDS = "_tool_call_uids"
TOOL_CALL_UID = "_tool_call_uid"
MERGED_TURN_PREFIX = "_merged_turn_prefix"
PERSISTENCE_ONLY_MESSAGE_FIELDS = frozenset({
    "timestamp", "display_kind", "display_metadata", "_row_id", "_submit_row_session_id",
    "_canonical_content", MERGED_TURN_PREFIX, MESSAGE_UID, ABSORBED_MESSAGE_UIDS,
    TOOL_CALL_UIDS, TOOL_CALL_UID,
}) | REPAIR_BOOKKEEPING_FIELDS


def without_persistence_fields(msg: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return *msg* unchanged unless it contains fields that must stay out of provider requests."""
    if PERSISTENCE_ONLY_MESSAGE_FIELDS.isdisjoint(msg):
        return msg
    return {key: value for key, value in msg.items() if key not in PERSISTENCE_ONLY_MESSAGE_FIELDS}


def mint_uid() -> str:
    """Return a fresh durable message or tool-call identity."""
    return uuid4().hex


def uid_list(value: Any) -> List[str]:
    """Unique non-empty string uids from a live list, preserving order."""
    return list(dict.fromkeys(uid for uid in (value if isinstance(value, list) else ())
                              if isinstance(uid, str) and uid))


def message_uid_or_none(msg: Mapping[str, Any]) -> Optional[str]:
    uid = msg.get(MESSAGE_UID)
    return uid if isinstance(uid, str) and uid else None


def stamp_message_uid(msg: MutableMapping[str, Any]) -> str:
    """Stamp a logical message once so copies retain the same durable identity."""
    uid = message_uid_or_none(msg)
    if uid is None:
        uid = msg[MESSAGE_UID] = mint_uid()
    return uid


_IDENTITY_FIELD_TYPES = (
    (MESSAGE_UID, str),
    (ABSORBED_MESSAGE_UIDS, list),
    (TOOL_CALL_UIDS, dict),
    (TOOL_CALL_UID, str),
)


def copy_identity_fields(src: Mapping[str, Any], dst: MutableMapping[str, Any]) -> None:
    """Copy the non-empty durable identity fields between live and flush-row dictionaries."""
    for key, kind in _IDENTITY_FIELD_TYPES:
        value = src.get(key)
        if isinstance(value, kind) and value:
            dst[key] = kind(value)


def message_identity(msg: MutableMapping[str, Any], *, with_tool_uids: bool = False) -> dict:
    """Identity payload for a row copy; tool-call identity is retained only with its calls."""
    stamp_message_uid(msg)
    identity: dict = {}
    copy_identity_fields(msg, identity)
    if not with_tool_uids:
        identity.pop(TOOL_CALL_UIDS, None)
        identity.pop(TOOL_CALL_UID, None)
    return identity


def record_absorbed_message(
    survivor: MutableMapping[str, Any], dropped: Mapping[str, Any], *, dropped_leads: bool = False,
) -> None:
    """Record the identities folded into a composite message in transcript order."""
    survivor_uid = message_uid_or_none(survivor)
    dropped_uid = message_uid_or_none(dropped)
    own = uid_list(survivor.get(ABSORBED_MESSAGE_UIDS))
    theirs = uid_list(dropped.get(ABSORBED_MESSAGE_UIDS))
    if dropped_leads and dropped_uid:
        survivor[MESSAGE_UID] = dropped_uid
        ordered = theirs + ([survivor_uid] if survivor_uid else []) + own
    else:
        ordered = own + ([dropped_uid] if dropped_uid else []) + theirs
    if absorbed := [uid for uid in dict.fromkeys(ordered) if uid != survivor.get(MESSAGE_UID)]:
        survivor[ABSORBED_MESSAGE_UIDS] = absorbed


def merge_tool_call_uids(into: Mapping[str, Any], extra: Mapping[str, Any]) -> dict:
    """Union tool-call identity maps without losing repeated provider-id occurrences."""
    merged = dict(into)
    for call_id, uid in extra.items():
        merged[call_id] = (
            _uid_occurrences(merged[call_id]) + _uid_occurrences(uid)
            if call_id in merged else uid
        )
    return merged


def _uid_occurrences(value: Any) -> list:
    return list(value) if isinstance(value, list) else [value]


def per_occurrence_tool_call_uids(
    uids: Mapping[str, Any], tool_calls: List[Mapping[str, Any]],
) -> dict:
    """Expand repeated call ids into one uid slot per occurrence before folding rows."""
    from agent.message_sanitization import coalesce_tool_call_id

    counts = Counter(call_id for tc in tool_calls if (call_id := coalesce_tool_call_id(tc)))
    expanded = dict(uids)
    for call_id, count in counts.items():
        if count > 1 and isinstance(uid := uids.get(call_id), str):
            expanded[call_id] = [uid] * count
    return expanded


def index_tool_call_uids(index: MutableMapping[str, str], assistant: Mapping[str, Any]) -> frozenset:
    """Index the nearest assistant's call identities under each provider id spelling."""
    from agent.message_sanitization import coalesce_tool_call_id, tool_call_id_variants

    calls = [(tc, tool_call_id_variants(tc)) for tc in assistant.get("tool_calls") or ()]
    named = frozenset(variant for _, variants in calls for variant in variants)
    for variant in named:
        index.pop(variant, None)
    uids = assistant.get(TOOL_CALL_UIDS)
    if not isinstance(uids, dict) or not uids:
        return named
    occurrence: dict = {}
    for tc, variants in calls:
        call_id = coalesce_tool_call_id(tc)
        uid = uids.get(call_id)
        if isinstance(uid, list):
            nth = occurrence[call_id] = occurrence.get(call_id, -1) + 1
            uid = uid[nth] if nth < len(uid) else None
        if isinstance(uid, str) and uid:
            for variant in variants:
                index[variant] = uid
    return named


def resolve_tool_call_uid(index: MutableMapping[str, str], tool_call_id: Any) -> Optional[str]:
    """Resolve a tool result's identity against provider-id spelling variants."""
    from agent.message_sanitization import tool_result_id_variants

    if not index or not isinstance(tool_call_id, str) or not tool_call_id:
        return None
    for variant in tool_result_id_variants(tool_call_id):
        uid = index.get(variant)
        if uid:
            return uid
    return None


def tool_call_uid_from_history(messages: List[dict], tool_index: int, owners: dict) -> Optional[str]:
    """Resolve a tool result against the nearest preceding assistant call in the same user turn."""
    tool_call_id = messages[tool_index].get("tool_call_id")
    if not isinstance(tool_call_id, str) or not tool_call_id:
        return None
    from agent.message_sanitization import tool_result_id_variants

    result_variants = set(tool_result_id_variants(tool_call_id))
    for prior_index in range(tool_index - 1, -1, -1):
        prior = messages[prior_index]
        if not isinstance(prior, dict):
            continue
        if prior.get("role") == "user":
            return None
        if prior.get("role") != "assistant":
            continue
        if (entry := owners.get(id(prior))) is None:
            index: dict = {}
            entry = owners[id(prior)] = (index_tool_call_uids(index, prior), index)
        named, index = entry
        if result_variants.isdisjoint(named):
            continue
        return resolve_tool_call_uid(index, tool_call_id)
    return None

_Message = TypeVar("_Message", bound=MutableMapping[str, Any])


def stamp_message_timestamp(
    message: _Message,
    *,
    timestamp: Optional[float] = None,
) -> _Message:
    """Attach a creation timestamp without replacing source-provided time.

    Gateway adapters can supply the platform event time; all other callers use
    the local wall clock. Returns the same mapping for use at append sites.
    """
    if message.get("timestamp") is None:
        message["timestamp"] = wall_time() if timestamp is None else timestamp
    return message


def append_message(
    messages: list[Any],
    message: _Message,
    *,
    timestamp: Optional[float] = None,
) -> _Message:
    """Stamp and append one live transcript message."""
    messages.append(stamp_message_timestamp(message, timestamp=timestamp))
    return message
