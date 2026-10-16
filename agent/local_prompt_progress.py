"""Prompt-reading progress from llama-server.

llama-server reads a long prompt for minutes before it writes the first token. Asked with
``return_progress``, it streams a progress chunk after each batch it reads. Anakot uses those
chunks as signs of life: stall timers stay quiet while the server works, and compression can
exclude prompt-reading time from its total deadline.
"""

from __future__ import annotations

import contextlib
import threading
import time
from typing import Any, Callable, Optional

_reading = threading.local()

_CONTENT_FIELDS = ("content", "tool_calls", "reasoning_content", "reasoning", "refusal")


def with_prompt_progress(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Copy chat-completions kwargs and ask llama-server for prompt progress chunks."""
    extra_body = kwargs.get("extra_body")
    merged = dict(extra_body) if isinstance(extra_body, dict) else {}
    merged.setdefault("return_progress", True)
    return {**kwargs, "extra_body": merged}


def prompt_progress(chunk: Any) -> Optional[dict]:
    """Return a progress-only chunk payload, or ``None`` for a real response chunk."""
    extra = getattr(chunk, "model_extra", None)
    progress = extra.get("prompt_progress") if isinstance(extra, dict) else None
    if progress is None and isinstance(chunk, dict):
        progress = chunk.get("prompt_progress")
    if not isinstance(progress, dict):
        return None
    choices = getattr(chunk, "choices", None)
    if choices is None and isinstance(chunk, dict):
        choices = chunk.get("choices")
    for choice in choices or []:
        finish = choice.get("finish_reason") if isinstance(choice, dict) else getattr(choice, "finish_reason", None)
        delta = choice.get("delta") if isinstance(choice, dict) else getattr(choice, "delta", None)
        if finish:
            return None
        for field in _CONTENT_FIELDS:
            value = delta.get(field) if isinstance(delta, dict) else getattr(delta, field, None)
            if value:
                return None
    return progress


def _count(progress: dict, key: str) -> Optional[int]:
    try:
        return int(progress[key])
    except (KeyError, TypeError, ValueError):
        return None


def prompt_progress_percent(progress: dict) -> Optional[int]:
    """Return the prompt progress percentage, clamped to 0-100."""
    try:
        total = int(progress.get("total") or 0)
        processed = int(progress.get("processed") or 0)
    except (TypeError, ValueError):
        return None
    if total <= 0:
        return None
    return max(0, min(100, round(processed / total * 100)))


@contextlib.contextmanager
def prompt_reading_hook(hook: Optional[Callable[[float], None]]):
    """Install ``hook(seconds)`` for this thread; it hears each reading stretch."""
    previous = getattr(_reading, "hook", None)
    _reading.hook = hook
    try:
        yield
    finally:
        _reading.hook = previous


def current_prompt_reading_hook() -> Optional[Callable[[float], None]]:
    """Return this thread's prompt-reading hook."""
    return getattr(_reading, "hook", None)


class PromptReadingClock:
    """Track time spent reading prompt tokens, counting only newly-read progress."""

    def __init__(self, started: float):
        self._mark = started
        self._processed = -1
        self._server_ms = 0
        self.seconds = 0.0

    def tick(self, progress: dict) -> bool:
        """Count reading time up to this chunk; false when no new tokens were read."""
        now = time.monotonic()
        wall, self._mark = now - self._mark, now
        processed, server_ms = _count(progress, "processed"), _count(progress, "time_ms")
        if processed is None or processed <= self._processed:
            return False
        server = wall if server_ms is None else (server_ms - self._server_ms) / 1000
        self._processed, self._server_ms = processed, self._server_ms if server_ms is None else server_ms
        spent = max(0.0, min(wall, server))
        self.seconds += spent
        hook = current_prompt_reading_hook()
        if hook is not None:
            hook(spent)
        return True
