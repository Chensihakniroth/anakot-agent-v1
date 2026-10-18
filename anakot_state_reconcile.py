"""Explicit offline repair of additive ``state.db`` schema drift.

Read-only session consumers must not run DDL against a live profile database. This module stages a
complete SQLite snapshot, replays Anakot's canonical declarative schema, validates the staged file,
and copies it back only while the existing repair guard excludes writers.
"""

from __future__ import annotations

import contextlib
import sqlite3
from pathlib import Path
from typing import Any

from anakot_state_holders import read_only_db_uri


def schema_drift_reason(path: Path) -> str | None:
    """Return the first missing declared table/column, or ``None`` when the schema is current."""
    from anakot_state_repair import _schema_not_built
    from anakot_state_schema import schema_read_probe_statements

    with contextlib.closing(sqlite3.connect(read_only_db_uri(Path(path)), uri=True, timeout=1.0)) as conn:
        try:
            for statement in schema_read_probe_statements():
                conn.execute(statement).fetchone()
        except sqlite3.OperationalError as exc:
            if _schema_not_built(exc):
                return str(exc)
            raise
    return None


def _reconcile_snapshot(path: Path, guard: sqlite3.Connection) -> None:
    from anakot_state_repair import (
        _copy_database_snapshot,
        _db_opens_cleanly,
        _repair_conn,
        _repair_scratch_space_error,
        _unlink_db_triple,
    )
    from anakot_state_schema import SessionSchemaMixin, reconcile_state_schema

    scratch = path.with_name(path.name + ".reconcile-scratch")
    if error := _repair_scratch_space_error(path):
        raise RuntimeError(error)
    if error := _unlink_db_triple(scratch):
        raise RuntimeError(error)
    try:
        _copy_database_snapshot(path, scratch, source_connection=guard)
        with _repair_conn(scratch) as conn:
            _require_history_tables(conn)
            # The canonical DDL may create indexes that mention columns an older table lacks.
            # Reconcile columns first; the final schema probe still fails closed if an addition
            # could not be applied.
            object.__new__(SessionSchemaMixin)._reconcile_columns(conn.cursor())
            reconcile_state_schema(conn)
            conn.commit()
        if reason := schema_drift_reason(scratch):
            raise RuntimeError(f"schema reconciliation incomplete: {reason}")
        if reason := _db_opens_cleanly(scratch):
            raise RuntimeError(f"reconciled snapshot is unhealthy: {reason}")
        _copy_database_snapshot(scratch, path, destination_connection=guard)
    finally:
        if error := _unlink_db_triple(scratch):
            import logging

            logging.getLogger(__name__).warning("Could not remove reconciliation snapshot: %s", error)


def _reconcile_locked(path: Path, backup: bool, report: dict[str, Any]) -> None:
    from anakot_state_repair import (
        _backup_db_file,
        _db_opens_cleanly,
        _exclusive_repair_db_guard,
        _live_writer_holds_db,
    )

    if _live_writer_holds_db(path):
        raise RuntimeError("a live writer still holds state.db; stop it and retry")
    with contextlib.closing(sqlite3.connect(read_only_db_uri(path), uri=True, timeout=1.0)) as conn:
        _require_history_tables(conn)
    if schema_drift_reason(path) is None:
        report.update(repaired=True, strategy="already_healthy")
        return
    # Declarative reconciliation is not a substitute for corruption recovery.
    if reason := _db_opens_cleanly(path):
        raise RuntimeError(reason)
    if backup:
        backup_path, error = _backup_db_file(path)
        if backup_path is None:
            raise RuntimeError(f"pre-repair backup refused: {error}")
        report["backup_path"] = str(backup_path)
    with _exclusive_repair_db_guard(path) as (guard, error):
        if guard is None:
            raise RuntimeError(f"could not acquire exclusive state.db repair ownership: {error}")
        _reconcile_snapshot(path, guard)
        report.update(repaired=True, strategy="reconcile_declarative_schema")


def repair_declarative_schema(path: Path, *, backup: bool = True) -> dict[str, Any]:
    """Reconcile additive drift using Anakot's existing cross-process repair safeguards."""
    from anakot_state_repair import _cross_process_repair_lock

    path = Path(path)
    report: dict[str, Any] = {"repaired": False, "strategy": None, "backup_path": None, "error": None}
    try:
        with _cross_process_repair_lock(path) as holding:
            if not holding:
                raise RuntimeError("could not obtain the state.db repair lock")
            _reconcile_locked(path, backup, report)
    except (OSError, sqlite3.Error, RuntimeError, TimeoutError) as exc:
        report["error"] = str(exc)
    return report


def _require_history_tables(conn: sqlite3.Connection) -> None:
    """Never recreate missing canonical history tables as empty additive-repair output."""
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if {"sessions", "messages"} - tables:
        raise RuntimeError(
            "canonical history tables are missing; use `anakot sessions recover`, not additive reconciliation"
        )
