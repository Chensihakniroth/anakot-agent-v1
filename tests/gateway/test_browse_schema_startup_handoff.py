"""Gateway boot must hand off cleanly when browse owns a short schema catch-up lock."""

from pathlib import Path
from unittest.mock import MagicMock

import gateway.run as gateway_run


def test_browse_lock_waits_until_the_handoff_succeeds(monkeypatch, tmp_path):
    import gateway.status as status

    monkeypatch.setattr(status, "_is_gateway_runtime_lock_active_strict", lambda path: True)
    monkeypatch.setattr(status, "_read_gateway_lock_record", lambda path: None)
    monkeypatch.setattr(status, "_live_pid_from_record", lambda record: None)
    monkeypatch.setattr("anakot_state_reconcile.schema_drift_reason", lambda path: "no such column")
    acquire = MagicMock(side_effect=[False, True])
    monkeypatch.setattr(status, "acquire_gateway_runtime_lock", acquire)
    monkeypatch.setattr(gateway_run.time, "sleep", lambda seconds: None)

    assert gateway_run._wait_for_browse_reconcile_lock(
        tmp_path / "gateway.lock", tmp_path / "state.db", wait_s=1.0
    ) is True
    assert acquire.call_count == 2


def test_browse_lock_wait_does_not_mask_a_live_gateway(monkeypatch, tmp_path):
    import gateway.status as status

    monkeypatch.setattr(status, "_is_gateway_runtime_lock_active_strict", lambda path: True)
    monkeypatch.setattr(status, "_read_gateway_lock_record", lambda path: {"pid": 123})
    monkeypatch.setattr(status, "_live_pid_from_record", lambda record: 123)
    monkeypatch.setattr("anakot_state_reconcile.schema_drift_reason", lambda path: "no such column")
    acquire = MagicMock(return_value=True)
    monkeypatch.setattr(status, "acquire_gateway_runtime_lock", acquire)

    assert gateway_run._wait_for_browse_reconcile_lock(
        tmp_path / "gateway.lock", tmp_path / "state.db", wait_s=1.0
    ) is False
    acquire.assert_not_called()


def test_unpublished_browse_lock_wait_is_bounded(monkeypatch, tmp_path):
    import gateway.status as status

    monkeypatch.setattr(status, "_is_gateway_runtime_lock_active_strict", lambda path: True)
    monkeypatch.setattr(status, "_read_gateway_lock_record", lambda path: None)
    monkeypatch.setattr(status, "_live_pid_from_record", lambda record: None)
    monkeypatch.setattr("anakot_state_reconcile.schema_drift_reason", lambda path: "no such column")
    monkeypatch.setattr(status, "acquire_gateway_runtime_lock", lambda: False)
    monkeypatch.setattr(gateway_run.time, "sleep", lambda seconds: None)
    monotonic = iter((0.0, 0.0, 1.0))
    monkeypatch.setattr(gateway_run.time, "monotonic", lambda: next(monotonic))

    assert gateway_run._wait_for_browse_reconcile_lock(
        tmp_path / "gateway.lock", tmp_path / "state.db", wait_s=0.5
    ) is False


def test_gateway_claim_uses_browse_handoff_before_exiting(monkeypatch):
    import atexit
    import gateway.status as status

    monkeypatch.setattr(status, "get_running_pid", lambda: None)
    monkeypatch.setattr(status, "acquire_gateway_runtime_lock", lambda: False)
    monkeypatch.setattr(status, "_get_gateway_lock_path", lambda: Path("gateway.lock"))
    monkeypatch.setattr(status, "_get_process_anakot_home", lambda: Path("."))
    monkeypatch.setattr(gateway_run, "_wait_for_browse_reconcile_lock", lambda *args, **kwargs: True)
    monkeypatch.setattr(status, "write_pid_file", lambda: None)
    monkeypatch.setattr(status, "remove_pid_file", lambda: None)
    monkeypatch.setattr(status, "release_gateway_runtime_lock", lambda: None)
    monkeypatch.setattr(atexit, "register", lambda fn: None)

    assert gateway_run._start_gateway_claim_pid_file() is True
