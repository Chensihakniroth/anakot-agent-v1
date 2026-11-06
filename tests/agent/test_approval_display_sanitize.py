"""Approval prompts must show everything that will run (upstream ``3f5612cd``).

A dangerous command can carry content that renders as nothing — zero-width and bidi-override
characters, the U+E0000 tag block, raw ANSI/OSC escapes or a bare carriage return, or a run of
spaces that pushes the real tail off screen. The human then approves something other than what
runs. ``redact_approval_display`` is the single display-only copy used by every approval surface;
the executed command, the smart assessment and the allowlist keys never see it.
"""

from agent.redact import redact_approval_display, sanitize_command_for_display

ZWSP = chr(0x200B)
RLO = chr(0x202E)
TAG = chr(0xE0000)
ANSI = chr(0x1B) + "[31m"


def test_zero_width_characters_become_visible_escapes():
    out = sanitize_command_for_display(f"echo {ZWSP}whoami")
    assert ZWSP not in out
    assert "\\u200b" in out
    assert "echo" in out and "whoami" in out


def test_bidi_override_characters_become_visible_escapes():
    out = sanitize_command_for_display(f"echo {RLO}whoami")
    assert RLO not in out
    assert "\\u202e" in out


def test_tag_block_characters_become_visible_escapes():
    out = sanitize_command_for_display(f"echo {TAG}")
    assert TAG not in out
    assert "\\U000e0000" in out


def test_raw_control_bytes_become_visible_escapes():
    out = sanitize_command_for_display(f"echo {ANSI}whoami")
    assert ANSI not in out
    assert "\\x1b" in out


def test_whitespace_padding_collapses_to_a_marker():
    out = sanitize_command_for_display("echo hi" + " " * 40 + "whoami")
    assert " " * 40 not in out
    assert "⟨+40 whitespace chars⟩" in out


def test_blank_line_runs_collapse_to_a_marker():
    out = sanitize_command_for_display("a\n\n\n\n\nb")
    assert "\n\n\n\n\n" not in out
    assert "⟨+4 blank lines⟩" in out


def test_clean_text_comes_back_unchanged():
    assert sanitize_command_for_display("ls -la /tmp") == "ls -la /tmp"


def test_empty_input_stays_empty():
    assert sanitize_command_for_display("") == ""
    assert sanitize_command_for_display(None) == ""


def test_redaction_still_applies_alongside_sanitization():
    # A secret-shaped token is masked even with force=False, and the hidden char is still surfaced.
    secret = "sk-" + "A1b2C3d4E5f6G7h8"
    out = redact_approval_display(f"curl -H 'Authorization: Bearer {secret}'{ZWSP} https://x.example")
    assert secret not in out
    assert ZWSP not in out
    assert "https://x.example" in out
