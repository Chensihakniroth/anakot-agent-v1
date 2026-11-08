"""The desktop build's lock scan survives a process whose cwd cannot be read.

psutil's ``process_iter(attrs=...)`` calls ``as_dict`` inside the generator, outside
the scan's per-process guard. ``Process.cwd()`` on Windows reads the target's PEB
via ReadProcessMemory and can raise raw ``OSError`` (WinError 87) for protected
processes — ``as_dict`` only swallows AccessDenied/NoSuchProcess — so one
unreadable process aborted the whole scan and crashed the desktop rebuild step of
``anakot update`` (bootstrap-installer.log, 2026-11-08).
"""

from __future__ import annotations

import pytest

from anakot_cli import main_desktop


class _FakeProc:
    """Enough of psutil.Process for the scan; cwd() raises like the real one."""

    def __init__(self, pid, *, name, exe, ppid=1, cwd="", cwd_error=None):
        self.pid = pid
        self._name = name
        self._exe = exe
        self._ppid = ppid
        self._cwd = cwd
        self._cwd_error = cwd_error
        self.terminated = False

    def as_dict(self, attrs, ad_value=None):
        values = {"pid": self.pid, "name": self._name, "exe": self._exe, "ppid": self._ppid}
        if "cwd" in attrs:
            values["cwd"] = self.cwd()  # raw OSError propagates, as in real as_dict
        return {attr: values.get(attr, ad_value) for attr in attrs}

    def cwd(self):
        if self._cwd_error is not None:
            raise self._cwd_error
        return self._cwd

    def terminate(self):
        self.terminated = True


def _patch_scan(monkeypatch, psutil, procs):
    def fake_process_iter(attrs=None, ad_value=None):
        for proc in procs:
            if attrs is not None:
                # Mirrors the real generator: as_dict runs here, outside the
                # caller's per-process try, so a raise aborts the iteration.
                proc.info = proc.as_dict(attrs, ad_value)
            yield proc

    monkeypatch.setattr(psutil, "process_iter", fake_process_iter)
    monkeypatch.setattr(psutil, "wait_procs", lambda victims, timeout=0: (victims, []))


def _release_tree(tmp_path):
    desktop_dir = tmp_path / "desktop"
    locker_exe = desktop_dir / "release" / "win-unpacked" / "Anakot.exe"
    locker_exe.parent.mkdir(parents=True)
    return desktop_dir, locker_exe


@pytest.mark.windows_only
def test_unreadable_cwd_does_not_abort_the_scan(tmp_path, monkeypatch):
    psutil = pytest.importorskip("psutil")
    desktop_dir, locker_exe = _release_tree(tmp_path)
    bad = _FakeProc(
        100,
        name="protected.exe",
        exe=r"C:\Windows\System32\protected.exe",
        cwd_error=OSError(87, "The parameter is incorrect"),
    )
    locker = _FakeProc(200, name="Anakot.exe", exe=str(locker_exe))
    _patch_scan(monkeypatch, psutil, [bad, locker])

    stopped = main_desktop._stop_desktop_processes_locking_build(desktop_dir)

    assert stopped == [200]
    assert locker.terminated
    assert not bad.terminated


@pytest.mark.windows_only
def test_conhost_with_unreadable_cwd_is_skipped_not_fatal(tmp_path, monkeypatch):
    psutil = pytest.importorskip("psutil")
    desktop_dir, locker_exe = _release_tree(tmp_path)
    bad = _FakeProc(
        100,
        name="conhost.exe",
        exe=r"C:\Windows\System32\conhost.exe",
        cwd_error=OSError(87, "The parameter is incorrect"),
    )
    locker = _FakeProc(200, name="Anakot.exe", exe=str(locker_exe))
    _patch_scan(monkeypatch, psutil, [bad, locker])

    stopped = main_desktop._stop_desktop_processes_locking_build(desktop_dir)

    assert stopped == [200]
    assert locker.terminated
    assert not bad.terminated