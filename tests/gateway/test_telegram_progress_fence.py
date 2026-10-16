"""Regression coverage for Telegram progress repeat formatting."""


def test_progress_repeat_count_stays_outside_closing_code_fence():
    from gateway.run_turn_runner import _append_progress_repeat_count

    message = "💻 terminal\n```\nssh -F /tmp/config host\n```"
    repeated = _append_progress_repeat_count(message, 4)
    assert repeated.endswith("```\n(×4)")
    assert "``` (×4)" not in repeated


def test_plain_progress_repeat_count_keeps_inline_format():
    from gateway.run_turn_runner import _append_progress_repeat_count

    assert _append_progress_repeat_count("working", 3) == "working (×3)"
