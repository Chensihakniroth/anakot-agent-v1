from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def test_platform_modules_only_import_stdlib_and_anakot_platform() -> None:
    root = Path(__file__).resolve().parents[2]
    code = """
import sys
before = set(sys.modules)
import anakot_platform.host.facts
import anakot_platform.host.gpu_adapters
import anakot_platform.host.runtime
import anakot_platform.host.products
import anakot_platform.host.summary
import anakot_platform.declaration
import anakot_platform.resolver
import anakot_platform.resolver.app
import anakot_platform.resolver.availability
import anakot_platform.resolver.known_dirs
new_top_levels = {name.partition('.')[0] for name in set(sys.modules) - before}
unexpected = sorted(
    name
    for name in new_top_levels
    if name not in sys.stdlib_module_names and not name.startswith('anakot_platform')
)
assert not unexpected, unexpected
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = "."

    subprocess.run(
        [sys.executable, "-c", code],
        cwd=root,
        env=env,
        check=True,
    )
