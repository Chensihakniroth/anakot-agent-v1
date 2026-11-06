"""A flagged command that a prior decision covers says why it ran (upstream ``468f14ac``).

Provenance never decides anything: the guard only attaches it after the session/permanent check
passed, so a clean command keeps the bare ``{"approved": True}`` shape and the terminal tool
renders the note instead of looking like a bypass.
"""

from tools import approval
from tools.approval_provenance import preapproval_note

SESSION = "agent:main:test:session:1"


def _flagged_command():
    """A command the dangerous-pattern detector flags (and the hardline floors do not block)."""
    return "rm -rf build"


def test_a_clean_command_keeps_the_bare_approved_shape(monkeypatch):
    monkeypatch.setattr(approval, "_permanent_set", lambda: set())
    result = approval.check_dangerous_command("ls -la", "shell")
    assert result == {"approved": True, "message": None}
    assert "pre_approved" not in result


def test_an_allowlisted_flagged_command_names_the_entry(monkeypatch):
    monkeypatch.setattr(approval, "_permanent_set", lambda: {"rm -rf *"})
    result = approval.check_dangerous_command(_flagged_command(), "shell")
    assert result["approved"] is True
    entries = result["pre_approved"]
    assert len(entries) == 1
    assert entries[0]["scope"] == "allowlist"
    assert entries[0]["rule"] == "rm -rf *"
    assert entries[0]["description"]


def test_a_session_approved_flagged_command_names_the_scope(monkeypatch):
    monkeypatch.setattr(approval, "_permanent_set", lambda: set())
    monkeypatch.setattr(approval, "_session_approved", {SESSION: {"recursive delete"}}, raising=False)
    monkeypatch.setattr(approval, "get_current_session_key", lambda *a, **k: SESSION, raising=False)
    monkeypatch.setattr(approval, "_presence", lambda callback=None: (None, True, False, False))
    # Route through the combined guard so the session check is consulted.
    result = approval.check_all_command_guards(_flagged_command(), "shell")
    assert result["approved"] is True
    assert result["pre_approved"], "an approved flagged command must carry provenance"
    assert all(entry["scope"] in {"session", "permanent"} for entry in result["pre_approved"])


def test_a_permanently_approved_flagged_command_names_the_scope(monkeypatch):
    monkeypatch.setattr(approval, "_permanent_set", lambda: {"recursive delete"})
    monkeypatch.setattr(approval, "_presence", lambda callback=None: (None, True, False, False))
    result = approval.check_all_command_guards(_flagged_command(), "shell")
    assert result["approved"] is True
    assert result["pre_approved"]
    assert all(entry["scope"] == "permanent" for entry in result["pre_approved"])


def test_preapproval_note_words_the_reason():
    note = preapproval_note([{"description": "recursive delete", "scope": "permanent"}])
    assert "recursive delete" in note
    assert "always" in note
    assert note.startswith("Command was flagged (")


def test_a_denied_command_carries_no_provenance(monkeypatch):
    monkeypatch.setattr(approval, "_permanent_set", lambda: set())
    result = approval.check_dangerous_command("ls -la", "shell")
    assert "pre_approved" not in result
