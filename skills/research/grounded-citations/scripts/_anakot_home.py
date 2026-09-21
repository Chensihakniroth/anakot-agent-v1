"""Resolve ANAKOT_HOME for standalone skill scripts.

Skill scripts may run outside the Anakot process (system Python, nix env,
CI) where ``anakot_constants`` is not importable.  This module provides the
same ``get_anakot_home()`` contract without requiring it on ``sys.path``.

When ``anakot_constants`` IS available it is used directly so profile
resolution and any future enhancements are picked up automatically.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from anakot_constants import get_anakot_home as get_anakot_home
except (ModuleNotFoundError, ImportError):

    def get_anakot_home() -> Path:
        """Return the Anakot home directory (default: ``~/.anakot``)."""
        val = os.environ.get("ANAKOT_HOME", "").strip()
        return Path(val) if val else Path.home() / ".anakot"
