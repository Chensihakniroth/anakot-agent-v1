"""Tests for bounded async-delegation recovery evidence."""

from pathlib import Path


def test_transcript_tail_is_bounded_and_decodes_replacements(tmp_path: Path):
    from tools.async_delegation_recovery_hints import transcript_tail, transcript_tails

    path = tmp_path / "task.log"
    path.write_bytes("kickoff\n".encode() + ("x" * 3000).encode() + b"\nfinished\n")
    tail = transcript_tail(str(path), lines=2, chars=20)
    assert tail.startswith("…")
    assert len(tail) <= 21
    default_tail = transcript_tail(str(path))
    assert transcript_tails({"0": str(path)})["0"] == default_tail


def test_transcript_tails_skips_missing_paths(tmp_path: Path):
    from tools.async_delegation_recovery_hints import transcript_tails

    assert transcript_tails({"0": str(tmp_path / "missing.log")}) == {}


def test_recovery_notification_renders_transcript_tail_and_git_hint():
    from tools.process_registry_notifications import format_process_notification

    event = {
        "type": "async_delegation",
        "delegation_id": "deleg-recovered",
        "status": "unknown",
        "goal": "continue the work",
        "error": "owner exited",
        "last_known_status": "running",
        "task_transcripts": {"0": "C:/tmp/task-0.log"},
        "transcript_tails": {"0": "kickoff\nlast observed step"},
        "git_state_hint": "main @ abc123 (2 uncommitted file(s)) in C:/repo",
    }
    rendered = format_process_notification(event)
    assert "last observed step" in rendered
    assert "uncommitted file(s)" in rendered
    assert "task-0.log" in rendered
