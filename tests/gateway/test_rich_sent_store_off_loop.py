"""The rich-sent index write runs off the event loop for coroutine callers."""

import asyncio
import threading

import pytest

from gateway import rich_sent_store


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(
        rich_sent_store, "_store_path", lambda: str(tmp_path / "rich_sent.json")
    )


def test_record_async_runs_off_the_loop_thread(isolated_store, monkeypatch):
    writer_thread: list[int] = []
    real_update = rich_sent_store._update

    def spy_update(chat_id, message_id, fields):
        writer_thread.append(threading.get_ident())
        real_update(chat_id, message_id, fields)

    monkeypatch.setattr(rich_sent_store, "_update", spy_update)

    async def go():
        await rich_sent_store.record_async("chat", "42", "hello")
        return threading.get_ident()

    loop_thread = asyncio.run(go())
    assert writer_thread and writer_thread[0] != loop_thread
    assert rich_sent_store.lookup("chat", "42") == "hello"


def test_concurrent_record_async_calls_lose_no_entry(isolated_store, monkeypatch):
    """Two overlapping read-modify-writes must both land in the durable file."""
    real_write = rich_sent_store.atomic_json_write
    entered = threading.Barrier(2, timeout=10.0)

    def barrier_write(path, data, *a, **kw):
        try:
            entered.wait()
        except threading.BrokenBarrierError:  # pragma: no cover - timeout path
            pass
        return real_write(path, data, *a, **kw)

    monkeypatch.setattr(rich_sent_store, "atomic_json_write", barrier_write)

    async def go():
        await asyncio.gather(
            rich_sent_store.record_async("chat", "1", "one"),
            rich_sent_store.record_async("chat", "2", "two"),
        )

    asyncio.run(go())
    assert rich_sent_store.lookup("chat", "1") == "one"
    assert rich_sent_store.lookup("chat", "2") == "two"
