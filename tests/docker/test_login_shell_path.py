"""Login shells in the image keep Anakot' own dirs on PATH.

Debian's ``/etc/profile`` resets PATH for every login shell, so without
``/etc/profile.d/anakot.sh`` a ``bash -l`` (``docker exec <c> bash -l``, ssh, the
terminal tool's background ``bash -lic``) lost ``/opt/anakot/bin`` and bare
``anakot`` exited 127 (#56634).
"""
from __future__ import annotations

import subprocess


def test_login_shell_resolves_anakot_to_the_image_shim(built_image: str) -> None:
    r = subprocess.run(
        ["docker", "run", "--rm", "-u", "anakot", "--entrypoint", "bash", built_image,
         "-lc", 'echo "anakot=$(command -v anakot)"; echo "path=$PATH"'],
        capture_output=True, text=True, timeout=60, check=False,
    )
    assert r.returncode == 0, r.stderr
    lines = dict(line.split("=", 1) for line in r.stdout.splitlines() if "=" in line)
    assert lines["anakot"] == "/opt/anakot/bin/anakot"
    entries = lines["path"].split(":")
    assert entries.index("/opt/anakot/bin") < entries.index("/opt/anakot/.venv/bin")
    assert entries.count("/opt/anakot/bin") == 1
