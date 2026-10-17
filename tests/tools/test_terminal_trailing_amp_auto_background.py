"""Trailing-ampersand foreground commands stay tracked and approval-safe."""

import json
import threading
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from tools.terminal_tool_guards import _foreground_background_guidance, trailing_amp_background_command


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("printf x &", "printf x"),
        ("printf x&", "printf x"),
        ("printf x&   ", "printf x"),
        ("echo x && printf y &", "echo x && printf y"),
        (r"printf '<%s>' trailing\ &", r"printf '<%s>' trailing\ "),
    ],
)
def test_unambiguous_trailing_amp_is_stripped_only(command, expected):
    assert trailing_amp_background_command(command) == expected


@pytest.mark.parametrize(
    "command",
    [
        "printf x & printf y",
        "printf x; printf y &",
        "nohup printf x &",
        'pid="$(sleep 1 & echo $!)" &',
        'pid="`sleep 1 & echo $!`" &',
        "cat <(printf x) &",
        "cat >(printf x) &",
        "hermes gateway run &",
        r"printf x\&",
        "bash -c 'sleep 1 &' &",
        'sh -c "sleep 1 &" &',
        "bash -c 'sleep 1 &'",
        "/bin/bash -c 'sleep 1 &' &",
        "/usr/bin/env -i bash -c 'sleep 1 &' &",
        "env FOO=1 bash -c 'sleep 1 &' &",
        "env FOO='a b' bash -c 'sleep 1 &' &",
        "busybox sh -c 'sleep 1 &' &",
        "bash.exe -c 'sleep 1 &' &",
        '"/bin/bash" -c \'sleep 1 &\' &',
        '"$SHELL" -c \'sleep 1 &\' &',
        "bash -c'sleep 1 &' &",
        '"${SHELL}" -c \'sleep 1 &\' &',
    ],
)
def test_ambiguous_or_identity_changing_commands_keep_the_refusal(command):
    assert trailing_amp_background_command(command) is None



def test_command_substitution_backgrounding_is_refused_before_quote_masking():
    command = 'echo "$(sleep 9 & echo $!)"'

    assert _foreground_background_guidance(command)


def test_escaped_ampersand_is_data_not_backgrounding():
    command = r"printf x\&echo done"

    assert _foreground_background_guidance(command) is None


def test_no_space_inline_amp_is_refused_for_both_background_modes():
    command = "sleep 1&echo done"

    assert trailing_amp_background_command(command) is None
    assert _foreground_background_guidance(command)


@pytest.mark.parametrize(
    ("command", "expected"),
    [("printf --help &", "printf --help"), ("printf --version&", "printf --version")],
)
def test_help_version_trailing_amp_is_still_tracked(command, expected):
    assert trailing_amp_background_command(command) == expected


def test_tirith_identity_change_keeps_the_refusal(monkeypatch):
    from tools import approval

    monkeypatch.setattr(
        approval,
        "_tirith_scan",
        lambda command: {
            "action": "warn" if command.endswith("&") else "allow",
            "findings": [{"rule_id": "synthetic"}] if command.endswith("&") else [],
        },
    )

    assert trailing_amp_background_command("printf x &") is None


def test_terminal_pipeline_runs_the_stripped_command_as_tracked_background(monkeypatch, tmp_path):
    import tools.terminal_tool as terminal_module

    plan = SimpleNamespace(
        config={},
        env_type="local",
        effective_task_id="trailing-amp-test",
        cwd=str(tmp_path),
        host_cwd=None,
        effective_timeout=180,
        promoted_from_foreground_timeout=None,
        auto_background_command="printf x",
    )
    seen = {}
    guard_commands = []

    monkeypatch.setattr(terminal_module, "_plan_execution", lambda *_a, **_k: plan)
    monkeypatch.setattr(terminal_module, "_acquire_env", lambda *_a, **_k: object())

    def pre_guard(command, **_kwargs):
        guard_commands.append(("pre", command))

    def approval_guard(command, *_args, **_kwargs):
        guard_commands.append(("approval", command))
        return terminal_module._ApprovalVerdict()

    monkeypatch.setattr(terminal_module, "_pre_exec_block", pre_guard)
    monkeypatch.setattr(terminal_module, "_run_approval_guards", approval_guard)

    def spawn(**kwargs):
        seen.update(kwargs)
        return json.dumps({
            "output": "Background process started",
            "session_id": "proc_test",
            "pid": 1,
            "exit_code": 0,
            "error": None,
        })

    monkeypatch.setattr(terminal_module, "spawn_background_process", spawn)

    result = json.loads(terminal_module.terminal_tool("printf x &"))

    assert seen["command"] == "printf x"
    assert seen["auto_backgrounded"] is True
    assert guard_commands == [("pre", "printf x"), ("approval", "printf x")]
    assert result["session_id"] == "proc_test"


def test_explicit_background_also_canonicalizes_the_trailing_amp(monkeypatch, tmp_path):
    import tools.terminal_tool as terminal_module

    config = {
        "env_type": "local", "timeout": 180, "cwd": str(tmp_path), "host_cwd": None,
        "modal_mode": "auto", "docker_image": "", "singularity_image": "",
        "modal_image": "", "daytona_image": "",
    }
    plan_result = {}
    monkeypatch.setattr(terminal_module, "_get_env_config", lambda: config)
    monkeypatch.setattr(terminal_module, "_acquire_env", lambda *_args: object())
    monkeypatch.setattr(terminal_module, "_start_cleanup_thread", lambda: None)
    monkeypatch.setattr(terminal_module, "_pre_exec_block", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        terminal_module, "_run_approval_guards", lambda *_args, **_kwargs: terminal_module._ApprovalVerdict()
    )
    monkeypatch.setattr(
        terminal_module,
        "spawn_background_process",
        lambda **kwargs: plan_result.update(kwargs) or json.dumps({
            "output": "Background process started", "session_id": "proc_test", "pid": 1,
            "exit_code": 0, "error": None,
        }),
    )

    result = json.loads(terminal_module.terminal_tool("printf x &", background=True))

    assert result["session_id"] == "proc_test"
    assert plan_result["command"] == "printf x"
    assert plan_result["auto_backgrounded"] is True


def test_prepared_terminal_approval_uses_the_canonical_command(monkeypatch):
    import tools.terminal_tool as terminal_module
    from agent.terminal_approval_batch import _TerminalSlot, _slot, consume_prepared_guard
    from tools.approval_context import _approval_tool_call_id

    class Batch:
        cancelled = threading.Event()
        task_id = "task-1"
        agent = SimpleNamespace(_interrupt_requested=False, session_id="", _current_turn_id="")

    captured = []
    monkeypatch.setattr(terminal_module, "_get_env_config", lambda: {"env_type": "local"})
    monkeypatch.setattr(terminal_module, "_docker_has_host_access", lambda _config: False)
    monkeypatch.setattr(
        terminal_module,
        "_check_all_guards",
        lambda command, *_args: captured.append(command) or {"approved": True},
    )

    parsed = SimpleNamespace(ref=lambda _task_id: SimpleNamespace(call_id="call-1"))
    slot = _TerminalSlot(Batch(), parsed, 0)
    slot.release.set()
    slot.prepare(SimpleNamespace(call_id="call-1", args={"command": "printf x &"}))

    assert captured == ["printf x"]
    assert slot.guard_key[0] == "printf x"

    slot_token = _slot.set(slot)
    call_token = _approval_tool_call_id.set("call-1")
    try:
        assert consume_prepared_guard("printf x", "local", False) == {"approved": True}
        assert consume_prepared_guard("printf x", "local", False) is None
    finally:
        _approval_tool_call_id.reset(call_token)
        _slot.reset(slot_token)


def test_background_result_uses_conversion_note_without_relaunch_hint(monkeypatch, tmp_path):
    import tools.terminal_tool_background as background_module

    monkeypatch.setattr(
        background_module,
        "_spawn",
        lambda *_a, **_k: SimpleNamespace(id="proc_test", pid=1, watcher_platform="", parent_session_id=""),
    )
    result = json.loads(background_module.spawn_background_process(
        command="printf x",
        env=SimpleNamespace(),
        env_type="local",
        effective_task_id="trailing-amp-test",
        task_id=None,
        session_key="",
        workdir=None,
        cwd=str(tmp_path),
        effective_pty=False,
        notify_on_complete=False,
        watch_patterns=None,
        approval_note=None,
        pty_disabled_reason=None,
        auto_backgrounded=True,
    ))

    assert "auto_backgrounded" in result
    assert "hint" not in result


def test_auto_background_ci_diagnostic_is_not_an_actionable_hint(monkeypatch, tmp_path):
    import tools.terminal_tool_background as background_module

    monkeypatch.setattr(
        background_module,
        "_spawn",
        lambda *_a, **_k: SimpleNamespace(id="proc_test", pid=1, watcher_platform="", parent_session_id=""),
    )
    result = json.loads(background_module.spawn_background_process(
        command="gh pr checks 123 | jq '.[]'",
        env=SimpleNamespace(),
        env_type="local",
        effective_task_id="trailing-amp-test",
        task_id=None,
        session_key="",
        workdir=None,
        cwd=str(tmp_path),
        effective_pty=False,
        notify_on_complete=False,
        watch_patterns=None,
        approval_note=None,
        pty_disabled_reason=None,
        auto_backgrounded=True,
    ))

    assert "auto_backgrounded" in result
    assert "diagnostic" in result
    assert "hint" not in result
