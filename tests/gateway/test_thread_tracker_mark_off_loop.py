"""The thread-participation tracker's persist must not block the event loop.

``ThreadParticipationTracker._save`` ends in ``atomic_json_write`` ->
``os.replace``, whose duration is unbounded under filesystem pressure. Every
coroutine caller sits on an inbound-message path, so the rename must not be
paid inline on the loop.

Moving the persist to a worker thread removes the accidental serialization the
event loop used to provide, so the check/insert/trim/write sequence can now
interleave and lose an entry. The in-memory half must stay synchronous: the
Discord and Matrix mention gates check membership immediately after marking.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import threading

import pytest

from gateway.platforms import helpers
from gateway.platforms.helpers import ThreadParticipationTracker


@pytest.fixture()
def tracker(tmp_path, monkeypatch):
    """A tracker whose state file lives in an isolated directory."""
    path = tmp_path / "matrix_threads.json"
    monkeypatch.setattr(
        ThreadParticipationTracker, "_state_path", lambda self: path, raising=True
    )
    obj = ThreadParticipationTracker("matrix")
    obj.state_path = path
    return obj


def test_two_concurrent_marks_do_not_lose_an_entry(tracker, monkeypatch):
    """Two overlapping off-loop marks must both reach the durable file."""
    entered = threading.Barrier(2, timeout=10.0)
    real_write = helpers.atomic_json_write

    def _synchronised_write(path, payload, *a, **kw):
        try:
            entered.wait()
        except threading.BrokenBarrierError:  # pragma: no cover - timeout path
            pass
        return real_write(path, payload, *a, **kw)

    monkeypatch.setattr(helpers, "atomic_json_write", _synchronised_write, raising=True)

    async def scenario():
        await asyncio.gather(
            tracker.mark_async("!a:example.org"),
            tracker.mark_async("!b:example.org"),
        )

    asyncio.run(scenario())

    persisted = json.loads(tracker.state_path.read_text(encoding="utf-8"))
    assert sorted(persisted) == ["!a:example.org", "!b:example.org"]


def test_a_mark_is_visible_in_memory_before_the_persist_completes(
    tracker, monkeypatch
):
    """Membership must be true before the persist runs at all.

    The handoff never invokes the callable, so a deferred in-memory insert
    cannot be mistaken for a correct one.
    """
    handed_off = asyncio.Event()

    async def _never(fn, *a, **kw):
        handed_off.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(helpers, "_to_thread", _never, raising=True)

    async def scenario():
        mark = asyncio.create_task(tracker.mark_async("!first:example.org"))
        await asyncio.wait_for(handed_off.wait(), timeout=5.0)
        try:
            assert "!first:example.org" in tracker
        finally:
            mark.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await mark

    asyncio.run(scenario())
