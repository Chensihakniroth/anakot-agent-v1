"""Gemini long decode: one response spread over several generateContent hops.

Gemini 4 caps each request (32,768 tokens unary, 65,536 streamed) but lets
``maxOutputTokens`` reach 1,048,576 minus the input. A hop that hits the
per-request cap with budget left ends with ``finishReason: CONTINUATION`` plus
a ``continuationToken``; the client resends the same request with that token
until any other finish reason. Usage is summed for billing while the first
hop's prompt remains the context-size signal.
"""

from __future__ import annotations

from typing import Any, Optional

_LONG_DECODE_BUDGETS = {"xhigh": 262_144, "max": 1_048_576, "ultra": 1_048_576}
_USAGE_COUNT_KEYS = (
    "promptTokenCount",
    "cachedContentTokenCount",
    "candidatesTokenCount",
    "thoughtsTokenCount",
    "toolUsePromptTokenCount",
    "totalTokenCount",
)


def long_decode_max_output_tokens(model: str, reasoning_config: Any) -> Optional[int]:
    """Return the Gemini 4 total output budget for effort above ``high``."""
    name = (model or "").strip().lower().removeprefix("google/")
    if not name.startswith("gemini-4") or not isinstance(reasoning_config, dict):
        return None
    if reasoning_config.get("enabled") is False:
        return None
    return _LONG_DECODE_BUDGETS.get(str(reasoning_config.get("effort") or "").strip().lower())


def _candidate(payload: dict[str, Any]) -> dict[str, Any]:
    candidates = payload.get("candidates") if isinstance(payload, dict) else None
    first = candidates[0] if isinstance(candidates, list) and candidates else None
    return first if isinstance(first, dict) else {}


def continuation_token(payload: dict[str, Any]) -> Optional[str]:
    """Return the token from a ``CONTINUATION`` response, if present."""
    candidate = _candidate(payload)
    token = candidate.get("continuationToken")
    if str(candidate.get("finishReason") or "").upper() != "CONTINUATION":
        return None
    return token if isinstance(token, str) and token else None


def merge_hop_usage(hops: list[dict[str, Any]]) -> dict[str, Any]:
    """Sum usage counts while preserving the first hop's prompt as initial context size."""
    merged = {
        key: sum(int(hop.get(key) or 0) for hop in hops)
        for key in _USAGE_COUNT_KEYS
        if any(key in hop for hop in hops)
    }
    merged["initialPromptTokenCount"] = int(hops[0].get("promptTokenCount") or 0) if hops else 0
    return merged


def merge_hop_responses(hops: list[dict[str, Any]]) -> dict[str, Any]:
    """Join every hop's model parts and attach summed usage to the final response."""
    if not hops:
        return {"candidates": [], "usageMetadata": merge_hop_usage([])}
    parts = [
        part
        for hop in hops
        for part in ((_candidate(hop).get("content") or {}).get("parts") or [])
    ]
    last = _candidate(hops[-1])
    candidate = {
        **last,
        "content": {**(last.get("content") or {}), "role": "model", "parts": parts},
    }
    usage = merge_hop_usage([hop.get("usageMetadata") or {} for hop in hops])
    return {**hops[-1], "candidates": [candidate], "usageMetadata": usage}


def split_stream_continuation(
    event: dict[str, Any], hop_usage: list[dict[str, Any]]
) -> tuple[dict[str, Any], Optional[str]]:
    """Strip a held continuation finish and return its token for the next stream hop."""
    token = continuation_token(event)
    if token:
        hop_usage.append(event.get("usageMetadata") or {})
        candidate = {
            key: value
            for key, value in _candidate(event).items()
            if key not in ("finishReason", "continuationToken")
        }
        return {
            **{key: value for key, value in event.items() if key != "usageMetadata"},
            "candidates": [candidate],
        }, token

    candidate = _candidate(event)
    if hop_usage and candidate.get("finishReason"):
        return {
            **event,
            "usageMetadata": merge_hop_usage([*hop_usage, event.get("usageMetadata") or {}]),
        }, None
    return event, None
