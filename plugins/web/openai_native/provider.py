"""OpenAI Responses server-side web search provider.

Selecting ``web.search_backend: openai-native`` tells the Codex Responses
transport to declare OpenAI's provider-executed ``web_search`` tool instead of
sending Anakot's client-side function. Search execution stays on the provider;
URL extraction continues to use the configured extraction backend.
"""

from __future__ import annotations

import json
from typing import Any

from plugins.web._common import BaseWebSearchProvider, search_fail, setup_schema

_UNSUPPORTED_MSG = (
    "openai-native uses OpenAI's server-side web_search tool and requires the "
    "Codex Responses transport (provider openai-codex). For client-side search, "
    "choose another web backend."
)


def _get(obj: Any, key: str) -> Any:
    return obj.get(key) if isinstance(obj, dict) else None


def has_codex_credentials() -> bool:
    """Cheap, read-only credential probe used by the tools picker.

    Do not resolve or refresh tokens here: this method runs during every tools
    repaint and must not acquire the auth-store lock or perform network I/O.
    """
    try:
        from anakot_constants import get_anakot_home

        auth_path = get_anakot_home() / "auth.json"
        if not auth_path.exists():
            return False
        store = json.loads(auth_path.read_text(encoding="utf-8-sig"))
        tokens = _get(_get(_get(store, "providers"), "openai-codex"), "tokens")
        if str(_get(tokens, "access_token") or "").strip():
            return True
        entries = _get(_get(store, "credential_pool"), "openai-codex")
        return isinstance(entries, list) and any(
            isinstance(entry, dict) and str(entry.get("access_token") or "").strip()
            for entry in entries
        )
    except Exception:
        return False


class OpenAINativeWebSearchProvider(BaseWebSearchProvider):
    NAME = "openai-native"
    DISPLAY_NAME = "OpenAI Native Web Search (Codex Responses)"

    def is_available(self) -> bool:
        return has_codex_credentials()

    def search(self, query: str, limit: int = 5) -> dict[str, Any]:
        del query, limit
        return search_fail(_UNSUPPORTED_MSG)

    def get_setup_schema(self) -> dict[str, Any]:
        return setup_schema(
            self.DISPLAY_NAME,
            "native",
            "Search runs provider-side through Codex Responses; extraction uses another backend",
        )
