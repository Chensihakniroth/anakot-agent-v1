"""Browse-time session schema drift is additive only, profile-owned aware, and fail-closed."""

import sqlite3
from contextlib import closing

import pytest
from fastapi import HTTPException

import anakot_state_reconcile
from anakot_cli.web_server_sessions import _open_session_db_at_path
from anakot_state import SessionDB
from anakot_state_reconcile import CorruptStoreError, reconcile_drift_for_browse


def _lagging_store(tmp_path):
    path = tmp_path / "state.db"
    with SessionDB(db_path=path) as db:
        db.create_session("kept", source="cli")
        db.append_message("kept", role="user", content="history survives")
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("DROP INDEX IF EXISTS idx_sessions_effective_activity")
        conn.execute("ALTER TABLE sessions DROP COLUMN last_activity_at")
        conn.commit()
    return path


def test_unowned_lagging_store_browses_after_one_reconcile(tmp_path, monkeypatch):
    path = _lagging_store(tmp_path)
    monkeypatch.setenv("ANAKOT_HOME", str(tmp_path))

    db = _open_session_db_at_path(path, read_only=True)
    try:
        assert [row["id"] for row in db.list_sessions_rich(limit=10, compact_rows=True)] == ["kept"]
        assert [row["content"] for row in db.get_messages("kept")] == ["history survives"]
    finally:
        db.close()

    with closing(sqlite3.connect(path)) as conn:
        assert "last_activity_at" in {row[1] for row in conn.execute("PRAGMA table_info(sessions)")}

    before = path.read_bytes()
    db = _open_session_db_at_path(path, read_only=True)
    db.close()
    assert path.read_bytes() == before


def test_owned_lagging_store_is_not_written_and_names_restart(monkeypatch, tmp_path):
    path = _lagging_store(tmp_path)
    monkeypatch.setenv("ANAKOT_HOME", str(tmp_path))
    monkeypatch.setattr(
        "gateway.status._is_gateway_runtime_lock_active_strict",
        lambda lock_path: True,
    )
    monkeypatch.setattr("gateway.status._live_pid_from_record", lambda record: 12345)
    before = path.read_bytes()

    with pytest.raises(HTTPException) as caught:
        _open_session_db_at_path(path, read_only=True)

    assert caught.value.status_code == 503
    assert "running gateway owns it" in str(caught.value.detail)
    assert "gateway restart" in str(caught.value.detail)
    assert path.read_bytes() == before


def test_lock_claim_losing_race_refuses_the_browse_write(monkeypatch, tmp_path):
    path = _lagging_store(tmp_path)
    monkeypatch.setenv("ANAKOT_HOME", str(tmp_path))
    monkeypatch.setattr(anakot_state_reconcile, "_profile_gateway_owned", lambda _: False)
    monkeypatch.setattr("gateway.status._try_acquire_file_lock", lambda handle: False)
    before = path.read_bytes()

    with pytest.raises(HTTPException) as caught:
        _open_session_db_at_path(path, read_only=True)

    assert caught.value.status_code == 503
    assert "another process" in str(caught.value.detail)
    assert path.read_bytes() == before


def test_named_profile_served_by_multiplexer_is_owned(monkeypatch, tmp_path):
    home = tmp_path / "profiles" / "alpha"
    home.mkdir(parents=True)
    path = _lagging_store(home)
    monkeypatch.setenv("ANAKOT_HOME", str(tmp_path))
    monkeypatch.setattr(
        "anakot_cli.gateway.named_profile_served_by_running_multiplexer",
        lambda profile: profile == "alpha",
    )
    before = path.read_bytes()

    with pytest.raises(HTTPException) as caught:
        _open_session_db_at_path(path, read_only=True)

    assert caught.value.status_code == 503
    assert "running gateway owns it" in str(caught.value.detail)
    assert path.read_bytes() == before


def test_concurrent_browses_wait_for_one_reconcile(tmp_path, monkeypatch):
    import threading

    path = _lagging_store(tmp_path)
    monkeypatch.setenv("ANAKOT_HOME", str(tmp_path))
    barrier = threading.Barrier(6)
    results = []
    result_lock = threading.Lock()

    def browse():
        barrier.wait()
        try:
            db = _open_session_db_at_path(path, read_only=True)
            db.close()
            result = "200"
        except HTTPException as exc:
            result = f"{exc.status_code} {exc.detail}"
        with result_lock:
            results.append(result)

    threads = [threading.Thread(target=browse) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert all(not thread.is_alive() for thread in threads)
    assert results == ["200"] * 6


def test_missing_history_tables_are_not_recreated(tmp_path):
    path = tmp_path / "state.db"
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("CREATE TABLE sessions (id TEXT)")
        conn.execute("INSERT INTO sessions VALUES ('retain-me')")
        conn.commit()
    before = path.read_bytes()

    with pytest.raises(RuntimeError, match="canonical history tables are missing"):
        reconcile_drift_for_browse(path)

    assert path.read_bytes() == before


def test_corrupt_lagging_store_is_not_written(tmp_path, monkeypatch):
    path = _lagging_store(tmp_path)
    before = path.read_bytes()
    monkeypatch.setattr(anakot_state_reconcile, "_integrity_problem", lambda _: "malformed page")

    def fail_if_called(_path):
        raise AssertionError("browse must not run additive DDL on a corrupt store")

    monkeypatch.setattr(anakot_state_reconcile, "_apply_additive_schema", fail_if_called)
    with pytest.raises(CorruptStoreError, match="malformed"):
        reconcile_drift_for_browse(path)

    assert path.read_bytes() == before
