"""Account-scoped Codex service-tier negotiation.

The Codex model catalog advertises speed tiers per signed-in account. A requested
priority tier is only sent when the selected account explicitly advertises it;
unknown/unreachable catalogs preserve the user's request so transient discovery
failures do not disable fast mode.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

_CATALOG_CACHE: dict[str, tuple[dict[str, frozenset[str]], float]] = {}
_CATALOG_TTL = 3600
_MAX_CATALOGS = 128


def _advertised_tiers(entry: dict[str, Any]) -> frozenset[str] | None:
    tiers = entry.get("service_tiers")
    if isinstance(tiers, list):
        if any(not isinstance(item, dict) or not isinstance(item.get("id"), str) for item in tiers):
            return None
        return frozenset(item["id"] for item in tiers) if tiers else frozenset()
    speeds = entry.get("additional_speed_tiers")
    if isinstance(speeds, list) and all(isinstance(item, str) for item in speeds):
        return frozenset({"fast": "priority"}.get(item, item) for item in speeds)
    return None


def remember_catalog(cache_key: str, entries: list[Any]) -> None:
    """Cache only model speed metadata; never retain response payloads or tokens."""
    models: dict[str, frozenset[str]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("slug"), str):
            continue
        tiers = _advertised_tiers(entry)
        if tiers is not None:
            models[entry["slug"].strip()] = tiers
    if cache_key not in _CATALOG_CACHE and len(_CATALOG_CACHE) >= _MAX_CATALOGS:
        del _CATALOG_CACHE[min(_CATALOG_CACHE, key=lambda key: _CATALOG_CACHE[key][1])]
    _CATALOG_CACHE[cache_key] = (models, time.time())


def _load_catalog(access_token: str, base_url: str) -> frozenset[str] | None:
    from agent.codex_headers import codex_account_headers, is_official_codex_base_url
    from agent.model_metadata import CODEX_MODELS_CATALOG_URL, _codex_oauth_token_fingerprint

    if not is_official_codex_base_url(base_url):
        return None
    key = _codex_oauth_token_fingerprint(access_token) + ":tiers"
    cached = _CATALOG_CACHE.get(key)
    if cached is None or time.time() - cached[1] >= _CATALOG_TTL:
        try:
            import requests
            response = requests.get(
                CODEX_MODELS_CATALOG_URL,
                headers={"Authorization": f"Bearer {access_token}", **codex_account_headers(access_token)},
                timeout=(5, 10),
            )
            if response.status_code != 200:
                return None
            payload = response.json()
            remember_catalog(key, payload.get("models", []) if isinstance(payload, dict) else [])
            cached = _CATALOG_CACHE.get(key)
        except Exception as exc:  # best-effort discovery
            logger.debug("Codex service-tier catalog probe failed: %s", exc)
            return None
    return None


def _bare_model(model: str) -> str:
    raw = str(model or "").strip()
    if "/" in raw:
        raw = raw.split("/", 1)[1]
    return raw.removesuffix("-900k").removesuffix(".900k")


def _tiers_for_model(access_token: str, base_url: str, model: str) -> frozenset[str] | None:
    from agent.codex_headers import is_official_codex_base_url
    from agent.model_metadata import _codex_oauth_token_fingerprint

    if not is_official_codex_base_url(base_url):
        return None
    key = _codex_oauth_token_fingerprint(access_token) + ":tiers"
    _load_catalog(access_token, base_url)
    cached = _CATALOG_CACHE.get(key)
    if cached is None or time.time() - cached[1] >= _CATALOG_TTL:
        return None
    return cached[0].get(_bare_model(model))


def codex_account_offers_tier(model: Any, tier: str, *, base_url: Any, access_token: Any) -> bool | None:
    token = str(access_token or "").strip()
    if not token:
        return None
    supported = _tiers_for_model(token, str(base_url or ""), str(model or ""))
    return None if supported is None else tier in supported


def negotiate_request_tier(agent: Any, overrides: dict[str, Any]) -> None:
    """Remove an unsupported priority request while preserving unknown discoveries."""
    requested = overrides.get("service_tier")
    if (
        requested not in {"priority", "ultrafast"}
        or getattr(agent, "provider", None) != "openai-codex"
        or getattr(agent, "api_mode", None) != "codex_responses"
    ):
        return
    if requested == "ultrafast":
        ultrafast = codex_account_offers_tier(
            getattr(agent, "model", None), "ultrafast",
            base_url=getattr(agent, "base_url", None), access_token=getattr(agent, "api_key", None),
        )
        if ultrafast is True:
            return
        priority = codex_account_offers_tier(
            getattr(agent, "model", None), "priority",
            base_url=getattr(agent, "base_url", None), access_token=getattr(agent, "api_key", None),
        )
        if priority is False:
            overrides.pop("service_tier", None)
        elif priority is True:
            overrides["service_tier"] = "priority"
        return
    supported = codex_account_offers_tier(
        getattr(agent, "model", None), "priority",
        base_url=getattr(agent, "base_url", None), access_token=getattr(agent, "api_key", None),
    )
    if supported is False:
        overrides.pop("service_tier", None)
