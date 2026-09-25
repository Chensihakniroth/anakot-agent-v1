"""Retention bounds for ``kanban gc`` protect all garbage-collection targets."""

import argparse
import os
from pathlib import Path

import pytest

from anakot_cli import kanban_db as kb
from anakot_cli import kanban_db_connect as kbc
from anakot_cli import kanban_ops
from anakot_cli import kanban_parser


@pytest.fixture
def board(tmp_path, monkeypatch):
    home = tmp_path / ".anakot"
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("ANAKOT_HOME", str(home))
    return home


def _done_task_with_old_event(conn):
    task_id = kb.create_task(conn, title="finished")
    with kb.write_txn(conn):
        conn.execute("UPDATE tasks SET status='done' WHERE id=?", (task_id,))
        conn.execute("UPDATE task_events SET created_at=0 WHERE task_id=?", (task_id,))
    return task_id


def _event_rows(conn, task_id):
    return conn.execute(
        "SELECT count(*) FROM task_events WHERE task_id=?", (task_id,)
    ).fetchone()[0]


def _old_log_file():
    log_dir = kb.worker_logs_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "worker-1.log"
    path.write_text("log line", encoding="utf-8")
    os.utime(path, (0, 0))
    return path


@pytest.mark.parametrize("target", ["events", "logs"])
@pytest.mark.parametrize("retention", [-86400, -0.5])
def test_gc_api_rejects_negative_retention_without_deleting(board, target, retention):
    if target == "events":
        with kbc.connect_closing() as conn:
            task_id = _done_task_with_old_event(conn)
            with pytest.raises(ValueError, match="older_than_seconds"):
                kb.gc_events(conn, older_than_seconds=retention)
            assert _event_rows(conn, task_id) > 0
    else:
        log = _old_log_file()
        with pytest.raises(ValueError, match="older_than_seconds"):
            kb.gc_worker_logs(older_than_seconds=retention)
        assert log.exists()


@pytest.mark.parametrize(
    ("days", "expected_rc", "expected_kept"),
    [(-1, 2, True), (0, 0, True), (30, 0, False)],
)
def test_gc_command_validates_before_workspaces_and_zero_disables(
    board, days, expected_rc, expected_kept
):
    with kbc.connect_closing() as conn:
        task_id = _done_task_with_old_event(conn)
        archived = kb.create_task(conn, title="archived")
        with kb.write_txn(conn):
            conn.execute(
                "UPDATE tasks SET status='archived', workspace_kind='scratch' WHERE id=?",
                (archived,),
            )
    workspace = kb.workspaces_root() / archived
    workspace.mkdir(parents=True)
    marker = workspace / "keep.txt"
    marker.write_text("keep", encoding="utf-8")
    log = _old_log_file()

    args = argparse.Namespace(event_retention_days=days, log_retention_days=days)
    assert kanban_ops._cmd_gc(args) == expected_rc
    with kbc.connect_closing() as conn:
        assert (_event_rows(conn, task_id) > 0) is expected_kept
    assert log.exists() is expected_kept
    assert marker.exists() is (days < 0)

    assert kanban_parser._nonnegative_int("0") == 0
    with pytest.raises(argparse.ArgumentTypeError):
        kanban_parser._nonnegative_int("-1")