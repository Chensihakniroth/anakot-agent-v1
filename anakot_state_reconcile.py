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


class DeclarativeDriftError(RuntimeError):
    """The store lags the declared schema and browse-time reconciliation could not catch it up."""

    def __init__(self, detail: str, *, owned: bool = False):
        super().__init__(detail)
        self.owned = owned


class CorruptStoreError(sqlite3.DatabaseError):
    """A lagging store also failed integrity checks; browse must not write DDL into it."""

    def __init__(self, detail: str):
        super().__init__(f"database disk image is malformed (integrity_check: {detail})")


def is_declarative_drift_error(exc: BaseException) -> bool:
    """Return whether an operational error is a declared table/column lag, not corruption."""
    from anakot_state_repair import _schema_not_built

    return isinstance(exc, sqlite3.OperationalError) and _schema_not_built(exc)


def _owner_remedy(home: Path) -> tuple[str, str]:
    from gateway.status import _profile_label_for_home

    label = _profile_label_for_home(home)
    if label and label != "default":
        return label, f"anakot -p {label} gateway restart"
    return label or str(home), "anakot gateway restart"


def _profile_gateway_owned(path: Path) -> bool:
    """Probe the gateway lock for the profile owning *path*, failing closed on ACL errors."""
    from gateway.status import (
        _get_gateway_lock_path,
        _is_gateway_runtime_lock_active_strict,
        _live_pid_from_record,
        _read_gateway_lock_record,
        owns_gateway_runtime_lock,
    )

    lock_path = Path(path).with_name("gateway.lock")
    label, _ = _owner_remedy(lock_path.parent)
    if label != "default":
        from anakot_cli.gateway import named_profile_served_by_running_multiplexer

        if named_profile_served_by_running_multiplexer(label):
            return True
    if owns_gateway_runtime_lock() and lock_path.resolve() == _get_gateway_lock_path().resolve():
        return True
    try:
        if not _is_gateway_runtime_lock_active_strict(lock_path):
            return False
        # A sibling browse holds the OS lock but does not publish a gateway
        # record. A live, unmarked record is the positive runtime-owner proof;
        # empty/torn records stay in the bounded handoff path below.
        record = _read_gateway_lock_record(lock_path)
        return _live_pid_from_record(record) is not None and not (record or {}).get("purpose")
    except RuntimeError as exc:
        raise DeclarativeDriftError(
            f"could not inspect the profile gateway lock at {lock_path}; refusing to write the session store: {exc}",
            owned=True,
        ) from exc


_BROWSE_SIBLING_POLL_S = 0.1


def _wait_for_sibling_reconcile(path: Path, reason: str, label: str, remedy: str) -> bool:
    """Wait for another browse to publish a current schema, or classify a real owner."""
    import time

    deadline = time.monotonic() + 2.0
    while True:
        if schema_drift_reason(path) is None:
            return True
        if _profile_gateway_owned(path):
            raise DeclarativeDriftError(
                f"Session store for profile '{label}' is behind this Anakot version ({reason}), and a running "
                f"gateway owns it, so browsing will not write to it. Restart that gateway (`{remedy}`) to catch it up.",
                owned=True,
            )
        if time.monotonic() >= deadline:
            raise DeclarativeDriftError(
                f"Session store for profile '{label}' is being brought up to date by another process ({reason}). "
                "Retry in a moment; the session list was not cleared."
            )
        time.sleep(_BROWSE_SIBLING_POLL_S)


def _profile_lock_paths(path: Path) -> tuple[Path, ...]:
    """Return every lock a browse writer must hold, in a stable order."""
    from anakot_constants import get_default_anakot_root

    profile_lock = Path(path).with_name("gateway.lock").resolve()
    default_lock = (Path(get_default_anakot_root()) / "gateway.lock").resolve()
    if profile_lock == default_lock:
        return (profile_lock,)
    # Named profiles can be served by the default multiplexer. Holding both
    # locks prevents either a standalone gateway or the multiplexer from
    # starting between ownership discovery and the additive write.
    return default_lock, profile_lock


@contextlib.contextmanager
def _hold_profile_gateway_locks(path: Path):
    """Hold the OS gateway locks across the integrity check and additive DDL."""
    from gateway.status import _release_file_lock, _try_acquire_file_lock

    handles = []
    try:
        for lock_path in _profile_lock_paths(path):
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            handle = open(lock_path, "a+", encoding="utf-8")
            try:
                acquired = _try_acquire_file_lock(handle)
            except BaseException:
                handle.close()
                raise
            if not acquired:
                handle.close()
                for held_handle in reversed(handles):
                    _release_file_lock(held_handle)
                    with contextlib.suppress(OSError):
                        held_handle.close()
                handles.clear()
                yield False
                return
            handles.append(handle)
        yield True
    finally:
        for handle in reversed(handles):
            _release_file_lock(handle)
            with contextlib.suppress(OSError):
                handle.close()


def _integrity_problem(path: Path) -> str | None:
    """Return the first B-tree or FTS read-probe problem without opening the DB writable."""
    from anakot_state_repair import _FTS_TABLES, _schema_not_built

    try:
        with contextlib.closing(
            sqlite3.connect(read_only_db_uri(Path(path)), uri=True, timeout=2.0)
        ) as conn:
            rows = conn.execute("PRAGMA integrity_check").fetchall()
            problems = [str(row[0]) for row in rows if row and str(row[0]).lower() != "ok"]
            if problems:
                return "; ".join(problems[:3])
            for fts_table in _FTS_TABLES:
                try:
                    conn.execute(
                        f'SELECT 1 FROM {fts_table} WHERE {fts_table} MATCH \'""\' LIMIT 1'
                    ).fetchone()
                except sqlite3.DatabaseError as exc:
                    message = str(exc).lower()
                    if "no such module" in message or "no such tokenizer" in message:
                        continue
                    if _schema_not_built(exc):
                        # An absent optional FTS table is normal on builds that do not enable
                        # that tokenizer. Once the virtual table exists, however, "no such
                        # table/column" usually names a missing shadow/content object and is
                        # corruption, not a schema addition browse may safely repair.
                        base_exists = conn.execute(
                            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                            (fts_table,),
                        ).fetchone()
                        if not base_exists:
                            continue
                        return f"fts read probe failed on existing {fts_table}: {exc}"
                    return f"fts read probe failed on {fts_table}: {exc}"
    except sqlite3.DatabaseError as exc:
        return str(exc)
    return None


def _apply_additive_schema(path: Path) -> None:
    """Apply only canonical additive DDL in one short transaction."""
    from anakot_cli.sqlite_safe_read import connect_tracked
    from anakot_state_common import SCHEMA_SQL
    from anakot_state_repair import _reapply_durability_barriers
    from anakot_state_schema import SessionSchemaMixin

    with contextlib.closing(
        connect_tracked(Path(path), tracking_path=Path(path), timeout=2.0, isolation_level=None)
    ) as conn:
        _reapply_durability_barriers(conn)
        conn.execute("BEGIN IMMEDIATE")
        try:
            _require_history_tables(conn)
            cursor = conn.cursor()
            shim = object.__new__(SessionSchemaMixin)
            # Columns first: canonical indexes may reference an older table's missing column.
            shim._reconcile_columns(cursor)
            SessionSchemaMixin._execute_ddl_script_transactional(cursor, SCHEMA_SQL)
            shim._reconcile_columns(cursor)
            conn.execute("COMMIT")
        except BaseException:
            with contextlib.suppress(sqlite3.Error):
                conn.execute("ROLLBACK")
            raise


def reconcile_drift_for_browse(path: Path) -> bool:
    """Catch an unowned additive schema drift up once for a read-only browse.

    Missing history tables and corrupt files are never recreated or modified. A running gateway
    remains the sole writer for its profile; browse names its restart remedy instead of opening a
    second writer beside it.
    """
    path = Path(path)
    reason = schema_drift_reason(path)
    if reason is None:
        return False
    with contextlib.closing(
        sqlite3.connect(read_only_db_uri(path), uri=True, timeout=1.0)
    ) as conn:
        _require_history_tables(conn)
    label, remedy = _owner_remedy(path.parent)
    if _profile_gateway_owned(path):
        raise DeclarativeDriftError(
            f"Session store for profile '{label}' is behind this Anakot version ({reason}), and a running "
            f"gateway owns it, so browsing will not write to it. Restart that gateway (`{remedy}`) to catch it up.",
            owned=True,
        )
    try:
        with _hold_profile_gateway_locks(path) as held:
            if not held:
                return _wait_for_sibling_reconcile(path, reason, label, remedy)
            if problem := _integrity_problem(path):
                raise CorruptStoreError(problem)
            _apply_additive_schema(path)
            if after := schema_drift_reason(path):
                raise DeclarativeDriftError(
                    f"Session store for profile '{label}' is behind this Anakot version and could not be caught up "
                    f"({after}). Run `anakot sessions repair` for that profile."
                )
    except (DeclarativeDriftError, CorruptStoreError):
        raise
    except (OSError, sqlite3.DatabaseError, RuntimeError, TimeoutError) as exc:
        raise DeclarativeDriftError(
            f"Session store for profile '{label}' is behind this Anakot version and could not be caught up "
            f"({exc}). Run `{remedy}` and retry browsing.",
        ) from exc
    import logging

    logging.getLogger(__name__).warning(
        "state.db at %s lagged the declared schema (%s); added missing tables/columns for browsing",
        path,
        reason,
    )
    return True
