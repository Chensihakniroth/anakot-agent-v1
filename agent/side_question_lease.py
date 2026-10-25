"""Profile-bound, one-use leases for plugin ``ctx.side_question``."""

from __future__ import annotations

import contextvars
import copy
import logging
import secrets
import threading
import time
import weakref
from dataclasses import dataclass
from typing import Any, Optional

from agent.side_question_request import SideQuestionCapture, ask_text_only, runtime_key

logger = logging.getLogger(__name__)

SIDE_QUESTION_CAPABILITY = "llm.side_question"
LEASE_TTL_SECONDS = 60.0
MAX_PROMPT_CHARS = 4096
DEFAULT_TIMEOUT_SECONDS = 15.0
MAX_TIMEOUT_SECONDS = 60.0


@dataclass(frozen=True)
class _Lease:
    capture: SideQuestionCapture
    expires_at: float
    home_key: str


_leases: dict[str, _Lease] = {}
_lock = threading.Lock()


def _consented_plugin_loaded() -> bool:
    """True when this profile has an enabled, consented side-question plugin."""
    from anakot_cli.plugin_capabilities import plugin_capability_granted
    from anakot_cli.plugins import get_plugin_manager

    manager = get_plugin_manager()
    return any(
        loaded.enabled
        and SIDE_QUESTION_CAPABILITY in loaded.manifest.capabilities
        and plugin_capability_granted(key, SIDE_QUESTION_CAPABILITY, config=None)
        for key, loaded in list(manager._plugins.items())
    )


def _unattended(agent: Any) -> bool:
    """Do not issue a token when nobody is waiting for a plugin answer."""
    return (
        getattr(agent, "_persist_disabled", False)
        or getattr(agent, "platform", None) == "cron"
        or getattr(agent, "_delegate_depth", 0) > 0
    )


def _purge_locked(now: float, agent: Any = None) -> None:
    stale = []
    for token, lease in _leases.items():
        parent = lease.capture.parent_ref()
        if lease.expires_at < now or parent is None or parent is agent:
            stale.append(token)
    for token in stale:
        _leases.pop(token, None)


def issue_side_question_token(
    agent: Any,
    messages: list[dict[str, Any]],
    turn_id: str,
) -> Optional[str]:
    """Capture a completed attended turn and return a single-use opaque token."""
    if _unattended(agent) or not _consented_plugin_loaded():
        return None
    from anakot_constants import anakot_home_key

    capture = SideQuestionCapture(
        parent_ref=weakref.ref(agent),
        messages=copy.deepcopy(messages),
        system_prompt=getattr(agent, "_cached_system_prompt", None),
        system_prompt_static=getattr(agent, "_cached_system_prompt_static", None),
        tools=copy.deepcopy(getattr(agent, "tools", None) or []),
        session_id=str(getattr(agent, "session_id", "") or ""),
        turn_id=turn_id,
        runtime=runtime_key(agent),
        context=contextvars.copy_context(),
    )
    token = secrets.token_urlsafe(24)
    now = time.monotonic()
    with _lock:
        _purge_locked(now, agent)
        _leases[token] = _Lease(capture, now + LEASE_TTL_SECONDS, anakot_home_key())
    return token


def _redeemable(lease: Optional[_Lease], prompt: Any) -> Optional[str]:
    if lease is None:
        return "unknown_token"
    if time.monotonic() > lease.expires_at:
        return "expired"
    parent = lease.capture.parent_ref()
    if parent is None:
        return "parent_gone"
    if getattr(parent, "_current_turn_id", None) != lease.capture.turn_id:
        return "turn_moved_on"
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > MAX_PROMPT_CHARS:
        return "bad_prompt"
    return None


def redeem_side_question(
    token: Any,
    prompt: Any,
    *,
    plugin_id: str,
    home: Any = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> Optional[str]:
    """Consume a token for one text-only question, refusing cross-profile redemption."""
    from anakot_constants import anakot_home_key

    home_key = anakot_home_key(home)
    with _lock:
        lease = _leases.get(token) if isinstance(token, str) else None
        if lease is not None and lease.home_key != home_key:
            logger.info("side_question plugin=%s outcome=rejected:other_profile", plugin_id)
            return None
        if lease is not None:
            del _leases[token]
        _purge_locked(time.monotonic())
    reason = _redeemable(lease, prompt)
    if reason is not None:
        logger.info("side_question plugin=%s outcome=rejected:%s", plugin_id, reason)
        return None
    if runtime_key(lease.capture.parent_ref()) != lease.capture.runtime:
        logger.info("side_question plugin=%s outcome=rejected:runtime_changed", plugin_id)
        return None
    try:
        timeout_value = float(timeout)
    except (TypeError, ValueError):
        timeout_value = DEFAULT_TIMEOUT_SECONDS
    timeout_value = min(timeout_value, MAX_TIMEOUT_SECONDS) if timeout_value > 0 else DEFAULT_TIMEOUT_SECONDS
    return lease.capture.context.copy().run(
        ask_text_only,
        lease.capture,
        prompt,
        plugin_id=plugin_id,
        timeout=timeout_value,
    )
