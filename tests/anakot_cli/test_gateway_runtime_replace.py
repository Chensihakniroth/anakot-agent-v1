"""Tests for replacing incompatible gateway owners."""

import time

import pytest

import anakot_cli.gateway_runtime_replace as replace


@pytest.mark.platforms("windows")
def test_incompatible_owner_stops_its_scheduled_task_in_control_profile(monkeypatch, tmp_path):
    from anakot_constants import get_anakot_home
    from anakot_cli import gateway_windows

    control = tmp_path / "default"
    home = control / "profiles" / "secondary"
    control.mkdir()
    home.mkdir(parents=True)
    monkeypatch.setenv("ANAKOT_HOME", str(home))
    stops = []

    monkeypatch.setattr(replace, "_identify", lambda *_args, **_kwargs: (control, {}))
    monkeypatch.setattr(replace, "_verified_owner", lambda *_args: (12345, 10.0))
    monkeypatch.setattr(replace, "_write_planned_stop", lambda *_args: None)
    monkeypatch.setattr(replace, "_wait_gone", lambda *_args: True)
    monkeypatch.setattr(gateway_windows, "stop", lambda: stops.append(get_anakot_home()))

    assert replace.replace_incompatible_owner(home, deadline=time.monotonic() + 60) is None
    assert stops == [control]
    assert get_anakot_home() == home
