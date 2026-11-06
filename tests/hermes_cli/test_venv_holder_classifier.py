"""Cross-platform unit tests for the venv-holder message classifier (#90778)."""

import pytest

from anakot_cli.update_cmd import (
    _anakot_holder_subcommand,
)

class TestHolderSubcommand:
    @pytest.mark.parametrize(
        ("cmdline", "expected"),
        [
            (r"C:\x\venv\Scripts\python.exe -m anakot_cli.main serve --host 127.0.0.1", "serve"),
            (r"C:\x\venv\Scripts\python.exe -m anakot_cli.main dashboard", "dashboard"),
            (r"python.exe -m anakot_cli.main gateway run", "gateway"),
            # profile selector skipped; its VALUE must not become the subcommand
            (r"python -m anakot_cli.main --profile serve gateway run", "gateway"),
            (r"python -m anakot_cli.main -p work serve", "serve"),
            # 90778: flags containing subcommand words are not subcommands
            (r"python -m anakot_cli.main kanban --preserve-cache", "kanban"),
            # 91869 review: EVERY top-level value flag must be skipped —
            # a flag VALUE equal to a subcommand must not become the label
            (r"python -m anakot_cli.main --reasoning high serve", "serve"),
            (r"python -m anakot_cli.main -m dashboard serve", "serve"),
            (r"python -m anakot_cli.main -t browser,files gateway run", "gateway"),
            (r"python -m anakot_cli.main --model=dashboard serve", "serve"),
            # -c consumes ONE value token; later bare tokens are (harmless,
            # unhinted) subcommand candidates — pin that shape honestly
            (r"python -m anakot_cli.main -c mysession serve", "serve"),
            (r"C:\bin\anakot.exe dashboard", "dashboard"),
            (r"/usr/local/bin/anakot serve", "serve"),
            # no anakot entry at all
            (r"python -c import time; time.sleep(3)", None),
            # entry but no subcommand
            (r"python -m anakot_cli.main", None),
        ],
    )
    def test_parses_subcommand(self, cmdline, expected):
        assert _anakot_holder_subcommand(cmdline) == expected

    def test_shlex_joined_store_launcher_bootstrap_is_inventoried(self):
        """launchd ProgramArguments arrive ``shlex.join``ed (single-quoted source); the dashboard
        inventory must still read the subcommand behind the bootstrap."""
        import shlex
        from pathlib import Path

        from anakot_cli._launchers import runtime_command

        cmdline = shlex.join(runtime_command(Path("/opt/anakot-agent"), ["dashboard"], python="/opt/store/python"))
        assert _anakot_holder_subcommand(cmdline) == "dashboard"
