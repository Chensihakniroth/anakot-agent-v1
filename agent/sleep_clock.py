"""Clocks that stop while the computer sleeps.

A laptop that sleeps in the middle of a request freezes the agent and local model together.
Watchdogs that judge a lack of progress therefore use an awake-time clock where available.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable

_SLEEP_THRESHOLD_S = 5.0


def _windows_unbiased_clock() -> Callable[[], float] | None:
    """Return Windows' unbiased interrupt clock, or ``None`` when unavailable."""
    try:
        import ctypes
        query = ctypes.windll.kernel32.QueryUnbiasedInterruptTime
    except (AttributeError, OSError):
        return None

    def clock() -> float:
        value = ctypes.c_ulonglong(0)
        query(ctypes.byref(value))
        return value.value / 10_000_000

    return clock


#: Seconds the machine has spent awake. Windows excludes sleep/hibernation; POSIX monotonic clocks
#: already stop during suspend on supported platforms.
awake_seconds: Callable[[], float] = (
    (_windows_unbiased_clock() if sys.platform == "win32" else None) or time.monotonic)


class SleepWatch:
    """Report a long wall-clock gap since the previous check."""

    def __init__(self, interval: float) -> None:
        self._interval = interval
        self._wall = time.time()

    def slept(self) -> float:
        """Return seconds stopped since the previous call, or 0.0 for normal scheduling noise."""
        wall = time.time()
        stopped, self._wall = wall - self._wall - self._interval, wall
        return stopped if stopped >= _SLEEP_THRESHOLD_S else 0.0
