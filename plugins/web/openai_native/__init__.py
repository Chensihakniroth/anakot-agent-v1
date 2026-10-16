"""OpenAI native web search plugin — bundled and auto-loaded."""

from __future__ import annotations

from plugins.web.openai_native.provider import OpenAINativeWebSearchProvider


def register(ctx) -> None:
    ctx.register_web_search_provider(OpenAINativeWebSearchProvider())
