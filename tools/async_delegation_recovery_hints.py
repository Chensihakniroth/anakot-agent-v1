"""Bounded evidence attached to abandoned async-delegation recovery events.

The owner can die before a child records its terminal result. Recovery should
carry enough evidence for the parent to decide whether to continue or resend,
without requiring an immediate transcript or git inspection.
"""

from __future__ import annotations

import os
import subprocess
from typing import Optional

TAIL_LINES = 20
TAIL_CHARS = 2_000
_GIT_TIMEOUT_S = 5


def transcript_tail(path: str, *, lines: int = TAIL_LINES, chars: int = TAIL_CHARS) -> Optional[str]:
    """Return a bounded UTF-8 tail, or ``None`` when the transcript is unreadable."""
    try:
        with open(path, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - chars * 4))
            raw = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    tail = "\n".join(raw.splitlines()[-lines:]).strip()
    if len(tail) > chars:
        tail = "…" + tail[-chars:]
    return tail or None


def transcript_tails(paths: dict[str, str] | None) -> dict[str, str]:
    return {
        index: tail
        for index, path in (paths or {}).items()
        if (tail := transcript_tail(path))
    }


def git_state_hint(cwd: Optional[str]) -> Optional[str]:
    """Return a bounded branch/commit/dirty-count snapshot for a git checkout."""
    if not cwd or not os.path.isdir(cwd):
        return None
    try:
        from anakot_cli._subprocess_compat import harden_git_argv, noninteractive_repo_git_env
        env = noninteractive_repo_git_env(cwd)
    except Exception:
        return None
    if env is None:
        return None

    def run(*args: str) -> Optional[str]:
        try:
            result = subprocess.run(
                ["git", "-C", cwd, *harden_git_argv(args)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                stdin=subprocess.DEVNULL, timeout=_GIT_TIMEOUT_S, env=env, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return result.stdout if result.returncode == 0 else None

    head = run("log", "-1", "--format=%h %s")
    if head is None:
        return None
    branch = (run("rev-parse", "--abbrev-ref", "HEAD") or "?").strip()
    status = run("status", "--porcelain")
    dirty = len(status.splitlines()) if status is not None else "?"
    return f"{branch} @ {head.strip()} ({dirty} uncommitted file(s)) in {cwd}"
