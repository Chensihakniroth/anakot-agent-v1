from pathlib import Path


def test_windows_native_install_path_docs_match_installer() -> None:
    doc = Path("website/docs/user-guide/windows-native.md").read_text()
    install = Path("scripts/install.ps1").read_text()

    # The launchers live in the managed binary dir OUTSIDE the git checkout
    # (ANAKOT_HOME\bin, next to the managed uv) — NOT the whole venv\Scripts
    # (which would shadow the user's python, #83797) and NOT a dir inside
    # the checkout (which `anakot update`'s autostash swept off disk).
    assert "%LOCALAPPDATA%\\anakot\\bin" in doc
    assert (
        "Get-Command anakot        # should print "
        "C:\\Users\\<you>\\AppData\\Local\\anakot\\bin\\anakot.exe"
    ) in doc
    # Installer exposes $AnakotHome\bin, and must copy the launchers into it.
    assert '$anakotBin = "$AnakotHome\\bin"' in install
    assert "anakot.exe" in install and "anakot-acp.exe" in install
    # Guard against regressions to either legacy layout.
    assert '$anakotBin = "$InstallDir\\venv\\Scripts"' not in install
    assert '$anakotBin = "$InstallDir\\bin"' not in install
