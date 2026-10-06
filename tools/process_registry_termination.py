"""Process-tree termination and post-kill survivor verification for ProcessRegistry."""

import logging
import os
import signal
import subprocess
import time
from contextlib import suppress
from typing import TYPE_CHECKING, List, Optional

from anakot_cli._subprocess_compat import windows_hide_flags

if TYPE_CHECKING:
    from tools.process_registry import ProcessSession

logger = logging.getLogger("tools.process_registry")


class ProcessTerminationMixin:
    """The subclass supplies ``_host_pid_is_ours``, ``_is_host_pid_alive``,
    ``_detached_host_fate`` and ``_daemon_term_grace_seconds``. See ProcessRegistry."""

    @staticmethod
    def _proc_alive(proc) -> bool:
        """True if a psutil.Process is running and not a zombie (already dead, just unreaped)."""
        try:
            import psutil
            return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
        except Exception:
            return False

    @classmethod
    def _terminate_host_pid(cls, pid: int, expected_start: Optional[int] = None) -> None:
        """Terminate a host-visible PID and its descendants.
        ``expected_start`` (kernel start time at spawn) is re-validated first: a mismatch
        or dead PID means the number was recycled onto a stranger and we refuse to touch
        it — a leaked orphan beats tree-killing someone's browser. POSIX: snapshot descendants,
        SIGTERM the parent alone so it can perform an orderly shutdown, then clean up snapshot
        descendants that survive its grace window. Survivors are SIGKILLed after a second
        ``terminal.daemon_term_grace_seconds`` window. Windows:
        ``taskkill /T /F`` (psutil's stale PPID links miss orphans there); ``os.kill``
        is the fallback."""
        from tools.process_registry import _IS_WINDOWS

        if expected_start is not None and not cls._host_pid_is_ours(pid, expected_start):
            logger.warning(
                "Refusing to terminate host pid %d: start-time mismatch — "
                "PID was recycled onto an unrelated process.", pid)
            return

        def _sigterm_quietly():
            with suppress(OSError, ProcessLookupError, PermissionError):
                os.kill(pid, signal.SIGTERM)
        if _IS_WINDOWS:
            try:
                from tools import process_registry as pr
                pr.subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    capture_output=True, timeout=5, creationflags=windows_hide_flags(),
                )
            except Exception:
                with suppress(Exception):
                    os.kill(pid, signal.SIGTERM)
            return

        # POSIX (Linux/macOS): orderly SIGTERM, snapshot descendants, SIGKILL survivors.
        try:
            import psutil
            parent = psutil.Process(pid)
            descendants = parent.children(recursive=True)
        except Exception:
            # psutil missing or process already gone
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                return
            except Exception as e:
                logger.warning("SIGTERM failed for pid %d: %s", pid, e)
                return
            # Best-effort fallback: negative PID signals the process group (if lead)
            try:
                os.kill(-pid, signal.SIGTERM)
            except Exception:
                pass
            return

        gone = (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied)

        # Signal the parent alone: let it handle SIGTERM and shut its workers down.
        # Signalling workers first can panic parents that expect ordered shutdown.
        with suppress(gone):
            parent.send_signal(signal.SIGTERM)

        grace = cls._daemon_term_grace_seconds()

        # Wait up to grace seconds for the parent to exit on its own.
        t0 = time.time()
        while time.time() - t0 < grace:
            if not cls._proc_alive(parent):
                break
            time.sleep(0.05)

        # Parent didn't exit: now signal snapshot descendants that are still alive.
        if cls._proc_alive(parent):
            for proc in descendants:
                with suppress(gone):
                    if cls._proc_alive(proc):
                        proc.send_signal(signal.SIGTERM)

            # Wait another grace window for the tree to finish exiting.
            t0 = time.time()
            while time.time() - t0 < grace:
                if not cls._proc_alive(parent) and not any(cls._proc_alive(p) for p in descendants):
                    break
                time.sleep(0.05)

        # Final sweep: SIGKILL anything that survived both grace windows.
        targets = [p for p in descendants if cls._proc_alive(p)]
        if cls._proc_alive(parent):
            targets.insert(0, parent)
        # Re-snapshot before SIGKILL: catch late-spawned workers before
        # they reparent to init and nothing can find them again.
        with suppress(gone):
            if cls._proc_alive(parent):
                known = {proc.pid for proc in targets}
                targets.extend(p for p in parent.children(recursive=True) if p.pid not in known)
        for proc in targets:
            with suppress(gone):
                if cls._proc_alive(proc):
                    proc.kill()  # SIGKILL on POSIX
                    logger.info("Escalated to SIGKILL for pid %d (ignored SIGTERM within %.1fs grace)", proc.pid, grace)

    @staticmethod
    def _live_descendants(pid: int) -> List[int]:
        """PIDs of living non-zombie descendants of host PID ``pid`` (best-effort)."""
        try:
            import psutil
            children = psutil.Process(pid).children(recursive=True)
        except Exception:
            logger.debug("Could not list descendants of pid %s", pid, exc_info=True)
            return []
        return [c.pid for c in children if ProcessTerminationMixin._proc_alive(c)]

    # SIGKILL / taskkill are asynchronous: the kernel needs a scheduling tick to
    # tear the process down and the parent must reap it before poll()/isalive()
    # stop saying "alive". Verifying survivors in that window flagged every
    # escalated kill as incomplete.
    _KILL_SETTLE_SECONDS = 1.0

    def _post_kill_survivors(self, session: "ProcessSession") -> List[int]:
        """Host PIDs still alive once the kill signals have had time to land (#115490).

        Fail-closed: anything unverifiable counts as a survivor, so a kill
        that leaves a live tree can never write a killed receipt. Sandbox
        (env) sessions have no host-visible tree and are unverifiable by
        design — they return no survivors, preserving existing behavior."""
        deadline = time.monotonic() + self._KILL_SETTLE_SECONDS
        while True:
            survivors = self._probe_survivors(session)
            if not survivors or time.monotonic() >= deadline:
                return survivors
            time.sleep(0.05)

    def _probe_survivors(self, session: "ProcessSession") -> List[int]:
        survivors: List[int] = []
        proc = getattr(session, "process", None)
        if proc is not None:
            try:
                root_alive = proc.poll() is None
            except Exception:
                root_alive = True
            if root_alive:
                survivors.append(getattr(proc, "pid", None) or session.pid)
        pty = getattr(session, "_pty", None)
        if pty is not None:
            try:
                pty_alive = bool(pty.isalive())
            except Exception:
                pty_alive = self._is_host_pid_alive(session.pid)
            if pty_alive:
                survivors.append(session.pid)
        if session.pid_scope == "host" and session.pid:
            if self._detached_host_fate(session.pid, session.host_start_time) == "running":
                if session.pid not in survivors:
                    survivors.append(session.pid)
                survivors.extend(
                    pid for pid in self._live_descendants(session.pid)
                    if pid not in survivors)
            # A dead/recycled root has no PID-scope descendants left to find:
            # reparented orphans are outside PID scope (systemd scope stop,
            # issued before this check, covers the cgroup case).
        return [pid for pid in survivors if pid]
