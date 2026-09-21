"""Process-identity contract: the two kill/relaunch predicates and the profile liveness probe
defer to the canonical matchers instead of argv substrings (root AGENTS.md process-identity rule).
"""

from __future__ import annotations

import pytest

from anakot_cli.dashboard_procs import _is_desktop_local_serve_cmdline
from anakot_cli.update_cmd_windows import _anakot_holder_subcommand, _is_backend_argv

LOOPBACK = "--host 127.0.0.1 --port 0"

# (cmdline, holder subcommand, desktop-local reap?, Windows updater "Desktop backend"?). Substring
# scanners get every "trap" row wrong: "serve" appears inside --preserve-cache / observer.py / a flag
# value. The updater's kill set additionally requires the Desktop's `-m anakot_cli.main` spawn shape —
# a user-launched `anakot serve` / `anakot dashboard` is refused on, never tree-killed.
CMDLINES = [
    ("python -m anakot_cli.main serve " + LOOPBACK, "serve", True, True),
    ("python -m anakot_cli.main dashboard", "dashboard", False, True),
    ("/venv/bin/anakot serve --isolated --host=127.0.0.1 --port=0 --ssh-owner-nonce abc", "serve", True, False),
    (r"C:\anakot\.venv\Scripts\anakot.exe serve --host 100.106.105.2 --port 9119", "serve", False, False),
    ("anakot.exe dashboard", "dashboard", False, False),
    ("anakot --profile ops serve " + LOOPBACK, "serve", True, False),
    ("anakot -m serve kanban --preserve-cache " + LOOPBACK, "kanban", False, False),
    ("python -m anakot_cli.main kanban --preserve-cache " + LOOPBACK, "kanban", False, False),
    ("anakot --reasoning high dashboard " + LOOPBACK, "dashboard", False, False),
    ("anakot gateway run --replace", "gateway", False, False),
    ("anakot chat --model serve", "chat", False, False),
    ("python observer.py serve " + LOOPBACK, None, False, False),
]


@pytest.mark.parametrize("cmdline,subcommand,reapable,desktop_backend", CMDLINES)
def test_kill_and_relaunch_predicates_agree_with_the_canonical_holder_matcher(
        cmdline, subcommand, reapable, desktop_backend):
    assert _anakot_holder_subcommand(cmdline) == subcommand
    # Desktop-local reap (a KILL path): serve + loopback + ephemeral port, decided by tokens.
    assert _is_desktop_local_serve_cmdline(cmdline) is reapable
    # Windows updater backend classifier (taskkill /T on orphans): canonical subcommand AND Desktop spawn shape.
    assert _is_backend_argv(cmdline.lower()) is desktop_backend


def test_desktop_local_serve_spares_fixed_port_and_remote_hosts():
    assert not _is_desktop_local_serve_cmdline("anakot serve --host 100.106.105.2 --port 9119 --skip-build")
    assert not _is_desktop_local_serve_cmdline("anakot serve --host 127.0.0.1 --port 9119")
    assert _is_desktop_local_serve_cmdline("anakot serve --host localhost --port 0")


def test_profile_liveness_is_the_shared_ladder(tmp_path, monkeypatch):
    """``_check_gateway_running`` is ``resolve_gateway_liveness`` scoped to the profile dir, with the
    PID rung reading (never cleaning) THAT profile's ``gateway.pid``."""
    import gateway.status as gw_status
    from anakot_cli.profiles import _check_gateway_running

    seen: dict = {}

    def fake_resolve(**kwargs):
        seen.update(kwargs)
        return gw_status.GatewayLiveness(running=True, pid=1, source="pid")

    monkeypatch.setattr(gw_status, "resolve_gateway_liveness", fake_resolve)
    calls: list = []
    monkeypatch.setattr(gw_status, "get_running_pid",
                        lambda path, cleanup_stale=True: calls.append((path, cleanup_stale)))
    assert _check_gateway_running(tmp_path) is True
    assert seen["profile_dir"] == tmp_path
    seen["pid_probe"](tmp_path / "gateway.pid")
    assert calls == [(tmp_path / "gateway.pid", False)]
