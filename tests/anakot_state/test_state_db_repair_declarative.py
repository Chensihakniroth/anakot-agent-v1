"""Explicit session repair must detect and safely reconcile additive schema drift."""

import sqlite3
from contextlib import closing
from types import SimpleNamespace

import pytest

import anakot_state_schema
from anakot_cli import sessions_cmd
from anakot_state import SessionDB
from anakot_state_common import SCHEMA_VERSION
from anakot_state_reconcile import repair_declarative_schema, schema_drift_reason


def _legacy_store(tmp_path, monkeypatch):
    path = tmp_path / "state.db"
    with SessionDB(db_path=path) as db:
        db.create_session("retained", source="cli")
        db.append_message("retained", role="user", content="history survives")
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("ALTER TABLE sessions DROP COLUMN tool_names")
        conn.execute("DROP TABLE gateway_hygiene_state")
        conn.commit()
    monkeypatch.setattr("anakot_state.DEFAULT_DB_PATH", path)
    return path


def test_check_only_reports_declarative_drift_without_mutation(tmp_path, monkeypatch):
    path = _legacy_store(tmp_path, monkeypatch)
    before = path.read_bytes()

    assert schema_drift_reason(path)
    assert sessions_cmd._cmd_repair(SimpleNamespace(check_only=True, no_backup=False)) == 1
    assert path.read_bytes() == before


@pytest.mark.parametrize("missing", ["sessions", "messages"])
def test_missing_history_table_is_not_recreated_as_empty(tmp_path, missing):
    path = tmp_path / "state.db"
    kept = "messages" if missing == "sessions" else "sessions"
    with closing(sqlite3.connect(path)) as conn:
        conn.execute(f"CREATE TABLE {kept} (id TEXT)")
        conn.execute(f"INSERT INTO {kept} VALUES ('retain-me')")
        conn.commit()
    before = path.read_bytes()

    report = repair_declarative_schema(path)

    assert report["repaired"] is False
    assert "canonical history tables are missing" in report["error"]
    assert path.read_bytes() == before


def test_repair_restores_a_missing_indexed_column_before_indexes(tmp_path, monkeypatch):
    path = _legacy_store(tmp_path, monkeypatch)
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("DROP INDEX idx_async_delegations_delivery")
        conn.execute("ALTER TABLE async_delegations DROP COLUMN completed_at")
        conn.commit()

    assert sessions_cmd._cmd_repair(SimpleNamespace(check_only=False, no_backup=True)) is None
    assert schema_drift_reason(path) is None
    with SessionDB(db_path=path, read_only=True) as db:
        assert [row["content"] for row in db.get_messages("retained")] == ["history survives"]
        assert db._conn.execute(
            "SELECT name FROM sqlite_master WHERE name='idx_async_delegations_delivery'"
        ).fetchone()


@pytest.mark.parametrize("backup", [True, False])
def test_explicit_repair_restores_readonly_history(tmp_path, monkeypatch, backup):
    path = _legacy_store(tmp_path, monkeypatch)

    assert sessions_cmd._cmd_repair(
        SimpleNamespace(check_only=False, no_backup=not backup)
    ) is None
    backups = list(tmp_path.glob("state.db.malformed-backup-*"))
    assert bool(backups) is backup
    assert schema_drift_reason(path) is None
    with SessionDB(db_path=path, read_only=True) as db:
        assert [row["content"] for row in db.get_messages("retained")] == ["history survives"]
        assert db.session_count() == 1
        assert db._conn.execute("SELECT version FROM schema_version").fetchone()[0] == SCHEMA_VERSION


def test_reconcile_failure_preserves_original_and_cleans_snapshot(tmp_path, monkeypatch):
    path = _legacy_store(tmp_path, monkeypatch)
    before = path.read_bytes()

    def refuse_reconcile(conn):
        conn.execute("CREATE TABLE only_in_scratch (id INTEGER)")
        raise sqlite3.OperationalError("injected DDL refusal")

    monkeypatch.setattr(anakot_state_schema, "reconcile_state_schema", refuse_reconcile)
    report = repair_declarative_schema(path, backup=False)

    assert report["repaired"] is False
    assert "injected DDL refusal" in report["error"]
    assert path.read_bytes() == before
    assert not path.with_name(path.name + ".reconcile-scratch").exists()
