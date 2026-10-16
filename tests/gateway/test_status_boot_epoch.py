"""Scoped gateway locks reject recycled PIDs across a host/container restart."""

from gateway import status


def _live_gateway(monkeypatch):
    monkeypatch.setattr(status, "_pid_exists", lambda _pid: True)
    monkeypatch.setattr(status, "_get_process_start_time", lambda _pid: 123)
    monkeypatch.setattr(status, "_looks_like_gateway_process", lambda _pid: True)
    monkeypatch.setattr(status, "_process_is_stopped", lambda _pid: False)


def test_boot_epoch_mismatch_rejects_an_otherwise_matching_pid(monkeypatch):
    _live_gateway(monkeypatch)
    monkeypatch.setattr(status, "_current_boot_epoch", lambda: "boot-new")
    assert status._scoped_lock_record_is_stale(
        {"pid": 321, "start_time": 123, "boot_epoch": "boot-old"}, 321)


def test_unreadable_current_epoch_keeps_a_recorded_lock_conservative(monkeypatch):
    _live_gateway(monkeypatch)
    monkeypatch.setattr(status, "_current_boot_epoch", lambda: "")
    assert not status._scoped_lock_record_is_stale(
        {"pid": 321, "start_time": 123, "boot_epoch": "boot-old"}, 321)
