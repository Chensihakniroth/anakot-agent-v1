"""Session-owned spillover retention and deletion-fence invariants.

The spillover path is deliberately tested through both the cache sweep and SessionDB's
real delete boundary. A transcript can carry a pointer in sentinel-prefixed multimodal
content or in a Windows-style path, and a shared archive must survive until its final
owning session is gone.
"""

import os
import time

import pytest

from anakot_state import SessionDB
from tools.tool_result_storage import cleanup_spillover_cache


@pytest.fixture
def db(tmp_path, monkeypatch):
    home = tmp_path / "anakot"
    home.mkdir()
    monkeypatch.setenv("ANAKOT_HOME", str(home))
    database = SessionDB(home / "state.db")
    try:
        yield database, home
    finally:
        database.close()


def _spill(home, name, *, age_hours=None):
    path = home / "cache" / "spillover" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(name, encoding="utf-8")
    if age_hours is not None:
        stale = time.time() - age_hours * 3600
        os.utime(path, (stale, stale))
    return path


def _pointer(home, name):
    return f"Full output saved to: {home / 'cache' / 'spillover' / name}"


def test_structured_and_windows_pointers_survive_age_sweep_then_delete(db):
    """NUL-prefixed multimodal content and backslashed sidecars count as live references."""
    database, home = db
    database.create_session("s", "cli")
    database.append_message(
        "s",
        "tool",
        [
            {"type": "text", "text": _pointer(home, "parts.txt")},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA"}},
        ],
    )
    database.append_message(
        "s",
        "tool",
        "plain result",
        api_content=_pointer(home, "win.txt").replace("/", "\\"),
    )
    parts = _spill(home, "parts.txt", age_hours=200 * 24)
    win = _spill(home, "win.txt", age_hours=200 * 24)

    assert cleanup_spillover_cache(max_age_hours=24) == 0
    assert parts.exists() and win.exists()

    assert database.delete_session("s") is True
    assert not parts.exists() and not win.exists()


def test_shared_spillover_survives_until_last_session_is_deleted(db):
    """A retired candidate remains while a surviving transcript still references it."""
    database, home = db
    spill = _spill(home, "shared.txt")
    pointer = _pointer(home, spill.name)
    for session_id in ("first", "second"):
        database.create_session(session_id, "cli")
        database.append_message(session_id, "tool", pointer)

    assert database.delete_session("first") is True
    assert spill.exists()
    assert database.delete_session("second") is True
    assert not spill.exists()


def test_bulk_delete_and_prune_capture_spillover_before_message_rows_disappear(db):
    """Bulk deletion and retention pruning use the same state-meta ownership fence."""
    database, home = db
    bulk_spill = _spill(home, "bulk.txt")
    pruned_spill = _spill(home, "pruned.txt")

    database.create_session("bulk", "cli")
    database.append_message("bulk", "tool", _pointer(home, bulk_spill.name))
    database.create_session("pruned", "cli")
    database.append_message("pruned", "tool", _pointer(home, pruned_spill.name), timestamp=1)
    database.end_session("pruned", "done")

    assert database.delete_sessions(["bulk"]) == 1
    assert not bulk_spill.exists()
    assert database.prune_sessions(older_than_days=0) == 1
    assert not pruned_spill.exists()
