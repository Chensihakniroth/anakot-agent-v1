"""Cached account-usage snapshots for model pickers and status surfaces.

Usage fetches run in the background and are keyed by profile home, provider,
account identity, and base URL so pooled credentials never contaminate one
another. Unknown or stale data is fail-open: callers can show an unknown state
rather than blocking a model picker on network I/O.
"""

from __future__ import annotations

import hashlib
import threading
import time
from contextvars import copy_context
from typing import TYPE_CHECKING, Any, Iterable, Optional

if TYPE_CHECKING:
    from agent.account_usage import AccountUsageSnapshot

REFRESH_AFTER_S = 120.0
SNAPSHOT_STALE_AFTER_S = 15 * 60.0

_lock = threading.Lock()
_snapshots: dict[tuple[str, str, str, str], AccountUsageSnapshot] = {}
_started: dict[tuple[str, str, str, str], float] = {}
_last_try: dict[tuple[str, str, str, str], float] = {}
_inflight: set[tuple[str, str, str, str]] = set()


def _key(provider: str, identity_id: Optional[str] = None, base_url: Optional[str] = None) -> tuple[str, str, str, str]:
    from anakot_constants import anakot_home_key

    return (
        anakot_home_key(),
        str(provider or "").strip().lower(),
        str(identity_id or "").strip(),
        str(base_url or "").strip().rstrip("/"),
    )


def has_account_usage(provider: str) -> bool:
    """Whether a built-in or provider-profile usage fetcher exists."""
    from agent.account_usage import _USAGE_FETCHERS

    slug = str(provider or "").strip().lower()
    return slug in _USAGE_FETCHERS


def _identity_id_for(provider: str, entry: Any) -> str:
    token = str(getattr(entry, "runtime_api_key", "") or "").strip()
    if not token:
        return f"entry:{getattr(entry, 'id', '')}"
    if provider == "openai-codex":
        from agent.credential_pool import _codex_principal_identity
        principal = _codex_principal_identity(token)
        if principal:
            return f"codex:{principal[0]}:{principal[1]}"
    return f"fp:{hashlib.sha256(token.encode('utf-8')).hexdigest()[:16]}"


def remember_account_usage(
    provider: Optional[str], snapshot: Optional[AccountUsageSnapshot], *,
    identity_id: Optional[str] = None, base_url: Optional[str] = None,
    started_monotonic: Optional[float] = None,
) -> None:
    if not provider or snapshot is None or not snapshot.windows:
        return
    started = time.monotonic() if started_monotonic is None else started_monotonic
    with _lock:
        snapshot_identity = getattr(snapshot, "identity", None)
        targets = [_key(provider, None, base_url)] if identity_id is None else []
        if identity_id is None and snapshot_identity:
            targets.append(_key(provider, snapshot_identity, None))
        elif identity_id is not None:
            targets.append(_key(provider, snapshot_identity or identity_id, None))
        for key in targets:
            if key in _started and _started[key] > started:
                continue
            _snapshots[key] = snapshot
            _started[key] = started


def cached_account_usage(provider: str, *, identity_id: Optional[str] = None, base_url: Optional[str] = None) -> Optional[AccountUsageSnapshot]:
    with _lock:
        return _snapshots.get(_key(provider, identity_id, base_url))


def snapshot_is_stale(snapshot: Optional[AccountUsageSnapshot]) -> bool:
    from agent.account_usage import AccountUsageSnapshot as _Snapshot
    if not isinstance(snapshot, _Snapshot):
        return True
    try:
        age = time.time() - snapshot.fetched_at.timestamp()
    except (AttributeError, TypeError, ValueError, OSError, OverflowError):
        return True
    return age < 0 or age > SNAPSHOT_STALE_AFTER_S


def _claim_refresh(key: tuple[str, str, str, str], now: float) -> bool:
    with _lock:
        if key in _inflight or now - _last_try.get(key, float("-inf")) < REFRESH_AFTER_S:
            return False
        _inflight.add(key)
        _last_try[key] = now
        return True


def _release_refresh(key: tuple[str, str, str, str]) -> None:
    with _lock:
        _inflight.discard(key)


def refresh_account_usage_async(providers: Iterable[str]) -> list[threading.Thread]:
    started: list[threading.Thread] = []
    now = time.monotonic()
    for provider in dict.fromkeys(providers):
        key = _key(provider)
        if not _claim_refresh(key, now):
            continue
        thread = threading.Thread(
            target=copy_context().run, args=(_refresh_legacy, provider, key),
            name="anakot-account-usage-refresh", daemon=True,
        )
        thread.start()
        started.append(thread)
    return started


def _refresh_legacy(provider: str, key: tuple[str, str, str, str]) -> None:
    from agent.account_usage import fetch_account_usage
    try:
        fetch_account_usage(provider)
    finally:
        _release_refresh(key)


def refresh_account_usage_entries_async(requests: Iterable[dict]) -> list[threading.Thread]:
    due: list[dict] = []
    now = time.monotonic()
    for request in requests:
        provider = str(request.get("provider") or "").strip().lower()
        identity_id = str(request.get("identity_id") or "").strip()
        if not provider or not identity_id or not str(request.get("api_key") or "").strip():
            continue
        if _claim_refresh(_key(provider, identity_id), now):
            due.append(request)
    if not due:
        return []
    thread = threading.Thread(
        target=copy_context().run, args=(_refresh_entries, list(due)),
        name="anakot-account-usage-refresh", daemon=True,
    )
    thread.start()
    return [thread]


def _refresh_entries(requests: list[dict]) -> None:
    from agent.account_usage import fetch_account_usage
    for request in requests:
        provider = request["provider"]
        key = _key(provider, request["identity_id"])
        try:
            fetch_account_usage(
                provider, base_url=request.get("base_url"), api_key=request.get("api_key"),
                read_only=True, identity_id=request["identity_id"],
            )
        finally:
            _release_refresh(key)
