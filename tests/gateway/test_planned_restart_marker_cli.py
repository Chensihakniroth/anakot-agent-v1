"""The planned-restart marker has one writer and one reader, and never blocks a restart.

``gateway/restart_notice.py`` is the single writer for both restart kinds (the gateway's in-band
shutdown and the CLI's stop+start); ``gateway/run.py`` is the reader that owes the "Gateway online"
home-channel notice. The CLI verbs stamp it only once the old host is gone, because a marker written
while the old host still drains can be replayed and unlinked by it (#142515, #142576).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import gateway.run as gateway_run
from gateway.restart_notice import (
    PLANNED_RESTART_MARKER_FILENAME,
    planned_restart_marker_path,
    write_planned_restart_marker,
)


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("ANAKOT_HOME", str(tmp_path))
    monkeypatch.setattr(gateway_run, "_anakot_home", tmp_path)
    return tmp_path


def test_writer_and_reader_agree_on_the_marker_path(home):
    write_planned_restart_marker()
    reader_path = gateway_run._planned_restart_notification_path()
    assert reader_path == planned_restart_marker_path(home)
    assert reader_path == home / PLANNED_RESTART_MARKER_FILENAME
    assert reader_path.exists()
    assert gateway_run._planned_restart_notification_pending() is True


def test_marker_carries_the_restart_kind(home):
    write_planned_restart_marker(via_service=True, detached=True)
    payload = json.loads((home / PLANNED_RESTART_MARKER_FILENAME).read_text(encoding="utf-8"))
    assert payload["via_service"] is True and payload["detached"] is True
    assert isinstance(payload["requested_at"], float)


def test_an_unwritable_home_costs_the_notice_not_the_restart(home, monkeypatch):
    from utils import atomic_json_write

    def boom(*args, **kwargs):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr("gateway.restart_notice.atomic_json_write", boom)
    write_planned_restart_marker()  # must not raise


def test_restart_all_stamps_the_marker_once_the_old_host_is_gone(home, monkeypatch):
    import anakot_cli.gateway as gw

    calls = []

    def stop_service(system):
        calls.append("stop_service")
        return 0

    def kill(all_profiles):
        calls.append("kill")
        return 1

    def wait_exit(timeout, force_after):
        calls.append("wait_exit")

    def wait_port_free():
        calls.append("wait_port_free")

    def start(**kwargs):
        calls.append("start")
        # The marker must already be on disk when the new host starts.
        assert (home / PLANNED_RESTART_MARKER_FILENAME).exists()

    monkeypatch.setattr(gw, "_stop_installed_service", stop_service)
    monkeypatch.setattr(gw, "kill_gateway_processes", kill)
    monkeypatch.setattr(gw, "_wait_for_gateway_exit", wait_exit)
    monkeypatch.setattr(gw, "_wait_for_api_server_port_free", wait_port_free)
    monkeypatch.setattr(gw, "_installed_service_kind_for", lambda is_windows: None)
    monkeypatch.setattr(gw, "run_gateway", start)

    gw._restart_all(False)

    assert calls == ["stop_service", "kill", "wait_exit", "wait_port_free", "start"]
