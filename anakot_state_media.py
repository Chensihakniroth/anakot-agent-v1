"""Durable spillover ownership for session transcript archives.

A persisted tool result is referenced by transcript content, so age-based cache cleanup must not
remove it while a surviving session can still read it. Delete paths record the names before their
message rows disappear, then collect the candidates after commit.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable

from tools.tool_result_storage import SPILLOVER_SQL_FILTER, spillover_names_in_text

logger = logging.getLogger("anakot_state")
SPILLOVER_PREFIX = "anakot.spillover.retired.v1."
_SPILLOVER_SUBDIR = Path("cache") / "spillover"


def retire_spillover(conn, session_ids: Iterable[str]) -> None:
    """Record spillover names referenced by *session_ids* before their messages are deleted."""
    ids = list(dict.fromkeys(session_ids))
    if not ids:
        return
    from anakot_state_common import _id_chunks, _placeholders

    for chunk in _id_chunks(ids):
        rows = conn.execute(
            f"SELECT content, api_content FROM messages "
            f"WHERE session_id IN ({_placeholders(chunk)}) AND {SPILLOVER_SQL_FILTER}",
            chunk,
        ).fetchall()
        names = set()
        for content, api_content in rows:
            names.update(spillover_names_in_text(content, api_content))
        conn.executemany(
            "INSERT OR IGNORE INTO state_meta(key, value) VALUES(?, ?)",
            [(SPILLOVER_PREFIX + name, json.dumps(name)) for name in names],
        )


def collect_retired_spillover(db) -> None:
    """Unlink retired archives no surviving message references and keep unresolved candidates.

    A surviving branch or compression sibling may share a pointer. If the reference scan cannot
    be completed, this function fails closed and leaves both the archive and its fence row intact.
    """
    try:
        with db._read_ctx() as conn:
            rows = conn.execute(
                "SELECT key, value FROM state_meta WHERE key LIKE ? ESCAPE '\\'",
                (SPILLOVER_PREFIX + "%",),
            ).fetchall()
            if not rows:
                return
            message_rows = conn.execute(
                f"SELECT content, api_content FROM messages WHERE {SPILLOVER_SQL_FILTER}"
            ).fetchall()
    except Exception:
        logger.debug("Could not inspect retired spillover candidates", exc_info=True)
        return

    referenced = set()
    for content, api_content in message_rows:
        referenced.update(spillover_names_in_text(content, api_content))

    spill_dir = Path(db.db_path).parent / _SPILLOVER_SUBDIR
    collected_keys = []
    for key, raw_name in rows:
        try:
            name = json.loads(raw_name)
            if not isinstance(name, str) or not name or name in referenced:
                continue
            path = spill_dir / name
            if path.name != name:
                continue
            path.unlink(missing_ok=True)
            collected_keys.append((key,))
        except (OSError, TypeError, ValueError):
            logger.debug("Spillover unlink failed for retired candidate %r", raw_name, exc_info=True)

    if collected_keys:
        try:
            db._execute_write(
                lambda conn: conn.executemany(
                    "DELETE FROM state_meta WHERE key = ?", collected_keys
                )
            )
        except Exception:
            logger.debug("Could not clear collected spillover candidates", exc_info=True)
