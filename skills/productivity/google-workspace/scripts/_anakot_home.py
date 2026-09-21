"""Resolve ANAKOT_HOME for standalone skill scripts.

Skill scripts may run outside the Anakot process (e.g. system Python,
nix env, CI) where ``anakot_constants`` is not importable.  This module
provides the same ``get_anakot_home()`` and ``display_anakot_home()``
contracts as ``anakot_constants`` without requiring it on ``sys.path``.

When ``anakot_constants`` IS available it is used directly so that any
future enhancements (profile resolution, Docker detection, etc.) are
picked up automatically.  The fallback path replicates the core logic
from ``anakot_constants.py`` using only the stdlib.

All scripts under ``google-workspace/scripts/`` should import from here
instead of duplicating the ``ANAKOT_HOME = Path(os.getenv(...))`` pattern.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from anakot_constants import display_anakot_home as display_anakot_home
    from anakot_constants import get_anakot_home as get_anakot_home
except (ModuleNotFoundError, ImportError):

    def get_anakot_home() -> Path:
        """Return the Anakot home directory (default: ~/.anakot).

        Mirrors ``anakot_constants.get_anakot_home()``."""
        val = os.environ.get("ANAKOT_HOME", "").strip()
        return Path(val) if val else Path.home() / ".anakot"

    def display_anakot_home() -> str:
        """Return a user-friendly ``~/``-shortened display string.

        Mirrors ``anakot_constants.display_anakot_home()``."""
        home = get_anakot_home()
        try:
            return "~/" + home.relative_to(Path.home()).as_posix()
        except ValueError:
            return str(home)
