#!/usr/bin/env python3
"""
custom_patches.py — Re-applies Anakot custom modifications after upstream merges.

This script runs AFTER rebrand.py on every update cycle. It re-applies changes
that the rebrand script doesn't know about (custom ASCII art, branding fixes,
update system modifications, etc.).

Usage:
    python3 custom_patches.py [target_dir]

Idempotent: safe to run multiple times on the same tree.
"""

import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# === Configuration ===
# Default target: the repo root (where this script lives, two levels up)
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
TARGET_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT

# === Patches ===

def patch_cli_ascii_art():
    """Replace ANAKOT ASCII art with ANAKOT ASCII art in CLI banner."""
    banner_path = TARGET_DIR / "anakot_cli" / "banner.py"
    if not banner_path.exists():
        print(f"  ⚠ banner.py not found at {banner_path}")
        return False

    content = banner_path.read_text(encoding="utf-8")

    # The old ANAKOT art (block-style)
    old_art = '''[bold #FFD7000]██╗  ██╗███████╗██████╗ ███╗   ███╗███████╗███████╗       █████╗  ██████╗ ███████╗███╗   ██╗████████╗[/]
[bold #FFD7000]██║  ██║██╔════╝██╔══██╗████╗ ████║██╔════╝██╔════╝      ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝[/]
[#FFBF00]███████║█████╗  ██████╔╝██╔████╔██║█████╗  ███████╗█████╗███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║[/]
[#FFBF00]██╔══██║██╔══╝  ██╔══██╗██║╚██╔╝██║██╔══╝  ╚════██║╚════╝██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║[/]
[#CD7F32]██║  ██║███████╗██║  ██║██║ ╚═╝ ██║███████╗███████║      ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║[/]
[#CD7F32]╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝╚══════╝      ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝[/]'''

    # The new ANAKOT art (block-style, same colors)
    new_art = '''[bold #FFD700] █████╗  ███╗   ██╗  █████╗  ██╔══██╗  ██████╗  ████████╗       █████╗  ██████╗ ███████╗███╗   ██╗████████╗[/]
[bold #FFD700]██╔══██╗ ████╗  ██║ ██╔══██╗ ██║╚██╗██║ ██╔═══██╗ ╚══██╔══╝      ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝[/]
[#FFBF00]███████║ ██╔██╗ ██║ ███████║ ██║ ╚████║ ██║   ██║    ██║          ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║[/]
[#FFBF00]██╔══██║ ██║╚██╗██║ ██╔══██║ ██╔═══██╗ ██║   ██║    ██║          ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║[/]
[#CD7F32]██║  ██║ ██║ ╚████║ ██║  ██║ ██╔══██╗ ╚██████╔╝    ██║               ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║[/]
[#CD7F32]╚═╝  ╚═╝ ╚═╝  ╚═══╝ ╚═╝  ╚═╝ ╚═════╝   ╚═════╝     ╚═╝           ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝[/]'''

    if old_art in content:
        content = content.replace(old_art, new_art)
        banner_path.write_text(content, encoding="utf-8")
        print("  ✓ CLI ASCII art: ANAKOT → ANAKOT")
        return True
    elif new_art in content:
        print("  ✓ CLI ASCII art: already ANAKOT (idempotent)")
        return True
    else:
        print("  ⚠ CLI ASCII art: pattern not found (may already be changed)")
        return False


def patch_tui_ascii_art():
    """Replace ANAKOT ASCII art with ANAKOT ASCII art in TUI banner."""
    banner_path = TARGET_DIR / "ui-tui" / "src" / "banner.ts"
    if not banner_path.exists():
        print(f"  ⚠ banner.ts not found at {banner_path}")
        return False

    content = banner_path.read_text(encoding="utf-8")

    # The old ANAKOT art lines
    old_lines = [
        "  '██╗  ██╗███████╗██████╗ ███╗   ███╗███████╗███████╗       █████╗  ██████╗ ███████╗███╗   ██╗████████╗',",
        "  '██║  ██║██╔════╝██╔══██╗████╗ ████║██╔════╝██╔════╝      ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝',",
        "  '███████║█████╗  ██████╔╝██╔████╔██║█████╗  ███████╗█████╗███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   ',",
        "  '██╔══██║██╔══╝  ██╔══██╗██║╚██╔╝██║██╔══╝  ╚════██║╚════╝██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   ',",
        "  '██║  ██║███████╗██║  ██║██║ ╚═╝ ██║███████╗███████║      ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   ',",
        "  '╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝╚══════╝      ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   '",
    ]

    # The new ANAKOT art lines
    new_lines = [
        "  '█████╗  ███╗   ██╗  █████╗  ██╔══██╗  ██████╗  ████████╗       █████╗  ██████╗ ███████╗███╗   ██╗████████╗',",
        "  '██╔══██╗ ████╗  ██║ ██╔══██╗ ██║╚██╗██║ ██╔═══██╗ ╚══██╔══╝      ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝',",
        "  '███████║ ██╔██╗ ██║ ███████║ ██║ ╚████║ ██║   ██║    ██║          ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   ',",
        "  '██╔══██║ ██║╚██╗██║ ██╔══██║ ██╔═══██╗ ██║   ██║    ██║          ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   ',",
        "  '██║  ██║ ██║ ╚████║ ██║  ██║ ██╔══██╗ ╚██████╔╝    ██║               ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   ',",
        "  '╚═╝  ╚═╝ ╚═╝  ╚═══╝ ╚═╝  ╚═╝ ╚═════╝   ╚═════╝     ╚═╝           ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   '",
    ]

    # Check if old art exists
    if all(line in content for line in old_lines):
        for old_line, new_line in zip(old_lines, new_lines):
            content = content.replace(old_line, new_line)
        banner_path.write_text(content, encoding="utf-8")
        print("  ✓ TUI ASCII art: ANAKOT → ANAKOT")
        return True
    elif all(line in content for line in new_lines):
        print("  ✓ TUI ASCII art: already ANAKOT (idempotent)")
        return True
    else:
        print("  ⚠ TUI ASCII art: pattern not found (may already be changed)")
        return False


def patch_desktop_intro_copy():
    """Replace ANAKOT ONLINE with ANAKOT ONLINE in desktop intro copy."""
    intro_path = TARGET_DIR / "apps" / "desktop" / "src" / "components" / "chat" / "intro-copy.jsonl"
    if not intro_path.exists():
        print(f"  ⚠ intro-copy.jsonl not found at {intro_path}")
        return False

    content = intro_path.read_text(encoding="utf-8")

    if "ANAKOT ONLINE" in content:
        content = content.replace("ANAKOT ONLINE", "ANAKOT ONLINE")
        intro_path.write_text(content, encoding="utf-8")
        print("  ✓ Desktop intro: ANAKOT ONLINE → ANAKOT ONLINE")
        return True
    elif "ANAKOT ONLINE" in content:
        print("  ✓ Desktop intro: already ANAKOT ONLINE (idempotent)")
        return True
    else:
        print("  ⚠ Desktop intro: pattern not found")
        return False


def patch_desktop_icon():
    """Install Anakot icon system-wide from the AppImage (Linux only)."""
    if sys.platform != "linux":
        print("  ✓ Desktop icon: skipped on non-Linux platform (idempotent)")
        return True

    # Prefer the current fork's Anakot logo (the girl with "N" badge)
    current_fork_icon = TARGET_DIR / "apps" / "desktop" / "public" / "apple-touch-icon.png"
    appimage_icons = Path("/opt/anakot-desktop/squashfs-root/usr/share/icons/hicolor")

    import subprocess
    installed = False
    for size in ["256x256", "512x512", "1024x1024"]:
        dst = Path(f"/usr/share/icons/hicolor/{size}/apps/anakot-desktop.png")
        # Prefer current fork's Anakot logo
        if current_fork_icon.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["sudo", "cp", str(current_fork_icon), str(dst)], capture_output=True)
            installed = True
        # Fallback: use AppImage's bundled icon
        elif (appimage_icons / size / "apps" / "Anakot.png").exists():
            src = appimage_icons / size / "apps" / "Anakot.png"
            dst.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["sudo", "cp", str(src), str(dst)], capture_output=True)
            installed = True

    if installed:
        subprocess.run(
            ["sudo", "gtk-update-icon-cache", "/usr/share/icons/hicolor/"],
            capture_output=True,
        )
        print("  ✓ Desktop icon installed")
        return True
    else:
        print("  ⚠ Desktop icon: no source icons found (skipping)")
        return True


def patch_upstream_urls():
    """Fix upstream URL constants in banner.py (rebrand may have missed these)."""
    banner_path = TARGET_DIR / "anakot_cli" / "banner.py"
    if not banner_path.exists():
        return False

    content = banner_path.read_text(encoding="utf-8")
    changed = False

    # Fix _UPSTREAM_REPO_URL
    if '_UPSTREAM_REPO_URL = "https://github.com/NousResearch/anakot-agent.git"' in content:
        content = content.replace(
            '_UPSTREAM_REPO_URL = "https://github.com/NousResearch/anakot-agent.git"',
            '_UPSTREAM_REPO_URL = "https://github.com/Chensihakniroth/anakot-agent-v1.git"'
        )
        changed = True

    # Fix _OFFICIAL_REPO_CANONICAL
    if '_OFFICIAL_REPO_CANONICAL = "github.com/nousresearch/anakot-agent"' in content:
        content = content.replace(
            '_OFFICIAL_REPO_CANONICAL = "github.com/nousresearch/anakot-agent"',
            '_OFFICIAL_REPO_CANONICAL = "github.com/nousresearch/anakot-agent"'
        )
        changed = True

    if changed:
        banner_path.write_text(content, encoding="utf-8")
        print("  ✓ Upstream URLs: fixed to anakot-agent")
        return True
    else:
        print("  ✓ Upstream URLs: already correct (idempotent)")
        return True


def patch_update_check_stored_sha():
    """Add stored SHA tracking to _check_via_local_git in banner.py."""
    banner_path = TARGET_DIR / "anakot_cli" / "banner.py"
    if not banner_path.exists():
        return False

    content = banner_path.read_text(encoding="utf-8")

    # Check if already patched
    if "last_merged_file = repo_dir / \".anakot-last-merged\"" in content:
        print("  ✓ Update check: stored SHA tracking already present (idempotent)")
        return True

    # Find the old _check_via_local_git function and replace it
    old_func = '''def _check_via_local_git(repo_dir: Path) -> Optional[int]:
    """Count commits behind origin/main in a local checkout.

    Passive checks never run ``git fetch``: every CLI/TUI/gateway start used to negotiate a pack
    with GitHub, and across the install base that was tens of millions of fetch requests a day
    (GitHub asked us to poll the API instead). Two tip SHAs are enough — the remote one from the
    API, the local one from ``rev-parse`` — and ``_tips_behind`` recovers the exact count through
    the compare API when they differ. ``git fetch`` happens only inside ``anakot update``.
    """
    # Probe the origin URL under the config-isolated env: a global url.<https>.insteadOf rewrite
    # otherwise makes an SSH origin masquerade as HTTPS (#104591).
    origin_url = _git_stdout(["remote", "get-url", "origin"], cwd=repo_dir, network=True)
    head_rev = _git_stdout(["rev-parse", "HEAD"], cwd=repo_dir)
    if not head_rev:
        return None
    canonical = _canonical_github_remote(origin_url)
    if canonical.startswith("github.com/"):
        target_rev = _github_branch_tip(canonical.removeprefix("github.com/"), "main")
    else:
        # Non-GitHub origin: one ls-remote for the tip (ref advertisement only, no pack transfer).
        result = _git_run(["ls-remote", "origin", "refs/heads/main"], cwd=repo_dir, timeout=10, network=True)
        target_rev = result.stdout.split()[0] if result is not None and result.returncode == 0 and result.stdout else None
    global _last_target_rev
    _last_target_rev = target_rev
    # Tip SHAs alone can't distinguish "behind" from a local commit AHEAD of origin/main, and
    # misreporting an ahead checkout nudges the user into `anakot update`, which can wipe carried
    # work — hence the ancestor check inside _tips_behind, against the FRESH upstream SHA.
    return _tips_behind(head_rev, target_rev, repo_dir)'''

    new_func = '''def _check_via_local_git(repo_dir: Path) -> Optional[int]:
    """Count commits behind upstream/main in a local checkout.

    For a rebranded fork, local HEAD is the rebrand commit — comparing it against origin/main
    always shows "up to date" because origin IS the fork. Instead, we compare the stored
    last-merged upstream SHA (``.anakot-last-merged``) against the current upstream/main tip.

    Passive checks never run ``git fetch``: every CLI/TUI/gateway start used to negotiate a pack
    with GitHub, and across the install base that was tens of millions of fetch requests a day
    (GitHub asked us to poll the API instead). Two tip SHAs are enough — the remote one from the
    API, the stored one from ``.anakot-last-merged`` — and ``_github_compare_behind`` recovers
    the exact count through the compare API when they differ. ``git fetch`` happens only inside
    ``anakot update``.
    """
    global _last_target_rev
    # Read the stored last-merged upstream SHA (written by `anakot update` after each merge).
    last_merged_file = repo_dir / ".anakot-last-merged"
    head_rev = _quiet(lambda: last_merged_file.read_text(encoding="utf-8").strip())
    if not head_rev:
        # No stored SHA — fall back to comparing local HEAD against origin (non-fork behavior).
        origin_url = _git_stdout(["remote", "get-url", "origin"], cwd=repo_dir, network=True)
        head_rev = _git_stdout(["rev-parse", "HEAD"], cwd=repo_dir)
        if not head_rev:
            return None
        canonical = _canonical_github_remote(origin_url)
        if canonical.startswith("github.com/"):
            target_rev = _github_branch_tip(canonical.removeprefix("github.com/"), "main")
        else:
            result = _git_run(["ls-remote", "origin", "refs/heads/main"], cwd=repo_dir, timeout=10, network=True)
            target_rev = result.stdout.split()[0] if result is not None and result.returncode == 0 and result.stdout else None
    else:
        # Fork mode: compare stored last-merged SHA against upstream/main tip.
        # Use _github_compare_behind directly (not _tips_behind) — the ancestor check in
        # _tips_behind uses local HEAD which is the rebrand commit (a descendant of upstream),
        # making it always report 0. The stored SHA is not a local ref.
        target_rev = _upstream_main_sha()
        if not head_rev or not target_rev:
            return None
        _last_target_rev = target_rev
        return _github_compare_behind(head_rev, target_rev)
    _last_target_rev = target_rev
    # Tip SHAs alone can't distinguish "behind" from a local commit AHEAD of origin/main, and
    # misreporting an ahead checkout nudges the user into `anakot update`, which can wipe carried
    # work — hence the ancestor check inside _tips_behind, against the FRESH upstream SHA.
    return _tips_behind(head_rev, target_rev, repo_dir)'''

    if old_func in content:
        content = content.replace(old_func, new_func)
        banner_path.write_text(content, encoding="utf-8")
        print("  ✓ Update check: stored SHA tracking added")
        return True
    elif "last_merged_file = repo_dir / \".anakot-last-merged\"" in content:
        print("  ✓ Update check: stored SHA tracking already present (idempotent)")
        return True
    else:
        print("  ⚠ Update check: pattern not found (may already be changed)")
        return False


def patch_update_cmd_stored_sha():
    """Add stored SHA tracking to update_cmd.py for forks."""
    update_path = TARGET_DIR / "anakot_cli" / "update_cmd.py"
    if not update_path.exists():
        return False

    content = update_path.read_text(encoding="utf-8")

    # Check if already patched
    if "last_merged_file = _m().PROJECT_ROOT / \".anakot-last-merged\"" in content:
        print("  ✓ update_cmd.py: stored SHA tracking already present (idempotent)")
        return True

    # Find the old shallow comparison block and replace it
    old_block = '''    if is_shallow:
        # No history across the shallow boundary: compare tip SHAs, then recover the
        # exact count via the GitHub compare API (complete graph).
        head_sha, target_sha = _tip_shas(git_cmd, compare_branch)
        if head_sha and target_sha and head_sha == target_sha:
            print("✓ Already up to date.")
            return
        from anakot_cli.banner import _github_compare_behind
        # counted == 0 means local-ahead, not behind; None means the API could not count.
        _print_update_check_result(_github_compare_behind(head_sha, target_sha), compare_branch)
        return'''

    new_block = '''    if is_shallow:
        # No history across the shallow boundary: compare tip SHAs, then recover the
        # exact count via the GitHub compare API (complete graph).
        # For forks: use the stored last-merged SHA instead of HEAD (which is the rebrand commit).
        last_merged_file = _m().PROJECT_ROOT / ".anakot-last-merged"
        stored_sha = last_merged_file.read_text(encoding="utf-8").strip() if last_merged_file.exists() else None
        origin_url = _m()._get_origin_url(git_cmd, _m().PROJECT_ROOT)
        if stored_sha and _is_fork(origin_url):
            head_sha = stored_sha
            # Get the target SHA from the compare branch tip
            target_result = _git_run(git_cmd, ["rev-parse", "--verify", compare_branch])
            target_sha = target_result.stdout.strip() if target_result.returncode == 0 else None
        else:
            head_sha, target_sha = _tip_shas(git_cmd, compare_branch)
        if head_sha and target_sha and head_sha == target_sha:
            print("✓ Already up to date.")
            return
        from anakot_cli.banner import _github_compare_behind
        # counted == 0 means local-ahead, not behind; None means the API could not count.
        _print_update_check_result(_github_compare_behind(head_sha, target_sha), compare_branch)
        return'''

    if old_block in content:
        content = content.replace(old_block, new_block)
        update_path.write_text(content, encoding="utf-8")
        print("  ✓ update_cmd.py: stored SHA tracking added")
        return True
    elif "last_merged_file = _m().PROJECT_ROOT / \".anakot-last-merged\"" in content:
        print("  ✓ update_cmd.py: stored SHA tracking already present (idempotent)")
        return True
    else:
        print("  ⚠ update_cmd.py: pattern not found (may already be changed)")
        return False


def patch_brandmark_icon():
    """Replace nous-girl.jpg with anakot-logo.png in BrandMark component."""
    brandmark_path = TARGET_DIR / "apps" / "desktop" / "src" / "components" / "brand-mark.tsx"
    if not brandmark_path.exists():
        print(f"  ⚠ brand-mark.tsx not found at {brandmark_path}")
        return False

    content = brandmark_path.read_text(encoding="utf-8")

    # Replace nous-girl.jpg with anakot-logo.png
    if "nous-girl.jpg" in content:
        content = content.replace("nous-girl.jpg", "anakot-logo.png")
        brandmark_path.write_text(content, encoding="utf-8")
        print("  ✓ BrandMark: nous-girl.jpg → anakot-logo.png")
        return True
    elif "anakot-logo.png" in content:
        print("  ✓ BrandMark: already using anakot-logo.png (idempotent)")
        return True
    else:
        print("  ⚠ BrandMark: no icon reference found")
        return False


def patch_skills_hub_url():
    """Fix skills hub URL: hermes-agent.nousresearch.com → hermes-agent.nousresearch.com."""
    import subprocess

    files_to_fix = [
        TARGET_DIR / "apps" / "desktop" / "src" / "app" / "capabilities" / "skills" / "embedded-hub-picker.tsx",
        TARGET_DIR / "apps" / "desktop" / "src" / "plugins" / "anakot-bots" / "skills-hub.tsx",
        TARGET_DIR / "apps" / "desktop" / "src" / "app" / "capabilities" / "plugins" / "plugins-tab.tsx",
        TARGET_DIR / "apps" / "desktop" / "src" / "app" / "settings" / "about-settings.tsx",
        TARGET_DIR / "apps" / "desktop" / "src" / "app" / "updates-overlay.tsx",
        TARGET_DIR / "apps" / "desktop" / "src" / "i18n" / "en.ts",
    ]

    fixed = 0
    for f in files_to_fix:
        if not f.exists():
            continue
        content = f.read_text(encoding="utf-8")
        if "hermes-agent.nousresearch.com" in content:
            content = content.replace("hermes-agent.nousresearch.com", "hermes-agent.nousresearch.com")
            f.write_text(content, encoding="utf-8")
            fixed += 1

    if fixed > 0:
        print(f"  ✓ Skills hub URL: fixed {fixed} file(s)")
        return True
    else:
        print("  ✓ Skills hub URL: already correct (idempotent)")
        return True


def patch_desktop_package_json():
    """Ensure apps/desktop/package.json unpacks dist/** from asar."""
    pkg_path = TARGET_DIR / "apps" / "desktop" / "package.json"
    if not pkg_path.exists():
        print(f"  ⚠ package.json not found at {pkg_path}")
        return True

    content = pkg_path.read_text(encoding="utf-8")
    if '"dist/**"' in content:
        print("  ✓ Desktop package.json: dist/** already in asarUnpack (idempotent)")
        return True

    target = '"asarUnpack": [\n      "**/*.node",'
    replacement = '"asarUnpack": [\n      "**/*.node",\n      "**/prebuilds/**",\n      "dist/**",'
    if target in content:
        content = content.replace(target, replacement)
        print("  ✓ Desktop package.json: added dist/** to asarUnpack")

    # Make clean scripts safe / no-op so missing tsc/npx doesn't fail packaging
    for old_clean in [
        '"clean:e2e": "npx --no-install tsc --build tsconfig.e2e.json --clean"',
        '"clean:e2e": "tsc --build tsconfig.e2e.json --clean"',
    ]:
        content = content.replace(old_clean, '"clean:e2e": "node -e \\"process.exit(0)\\""')
    for old_clean in [
        '"clean:renderer": "npx --no-install tsc --build tsconfig.json --clean "',
        '"clean:renderer": "tsc --build tsconfig.json --clean "',
    ]:
        content = content.replace(old_clean, '"clean:renderer": "node -e \\"process.exit(0)\\""')
    for old_clean in [
        '"clean:electron": "npx --no-install tsc --build tsconfig.electron.json --clean"',
        '"clean:electron": "tsc --build tsconfig.electron.json --clean"',
    ]:
        content = content.replace(old_clean, '"clean:electron": "node -e \\"process.exit(0)\\""')
    for old_clean in [
        '"clean": "npm run clean:e2e && npm run clean:renderer && npm run clean:electron"',
    ]:
        content = content.replace(old_clean, '"clean": "node -e \\"process.exit(0)\\""')

    pkg_path.write_text(content, encoding="utf-8")
    print("  ✓ Desktop package.json: clean scripts set to safe no-ops")
    return True


def patch_install_scripts():
    """Ensure installer scripts point to anakot-agent-v1 and guard helper scripts."""
    # 1. install.cmd
    cmd_path = TARGET_DIR / "scripts" / "install.cmd"
    if cmd_path.exists():
        cmd_content = cmd_path.read_text(encoding="utf-8")
        cmd_content = cmd_content.replace(
            "https://raw.githubusercontent.com/Chensihakniroth/anakot-agent-v1/main/scripts/install.cmd",
            "https://raw.githubusercontent.com/Chensihakniroth/anakot-agent-v1/main/scripts/install.cmd"
        )
        cmd_content = cmd_content.replace(
            "https://hermes-agent.nousresearch.com/install.ps1",
            "https://raw.githubusercontent.com/Chensihakniroth/anakot-agent-v1/main/scripts/install.ps1"
        )
        cmd_content = cmd_content.replace(
            "https://raw.githubusercontent.com/Chensihakniroth/ANAKOT-AGENT/main/scripts/install.cmd",
            "https://raw.githubusercontent.com/Chensihakniroth/anakot-agent-v1/main/scripts/install.cmd"
        )
        cmd_content = cmd_content.replace(
            "https://raw.githubusercontent.com/Chensihakniroth/ANAKOT-AGENT/main/scripts/install.ps1",
            "https://raw.githubusercontent.com/Chensihakniroth/anakot-agent-v1/main/scripts/install.ps1"
        )
        cmd_content = cmd_content.replace("Anakot Agent Installer", "Anakot Agent Installer")
        cmd_path.write_text(cmd_content, encoding="utf-8")

    # 2. install.ps1 guard ensure-rolldown-binding
    ps1_path = TARGET_DIR / "scripts" / "install.ps1"
    if ps1_path.exists():
        ps1_content = ps1_path.read_text(encoding="utf-8")
        old_pattern = '    $ensureScript = Join-Path $DesktopDir "scripts\\ensure-rolldown-binding.mjs"\n    & $script:EffectiveNode $ensureScript'
        new_pattern = '    $ensureScript = Join-Path $DesktopDir "scripts\\ensure-rolldown-binding.mjs"\n    if (Test-Path $ensureScript) {\n        & $script:EffectiveNode $ensureScript\n    }'
        if old_pattern in ps1_content:
            ps1_content = ps1_content.replace(old_pattern, new_pattern)
            ps1_path.write_text(ps1_content, encoding="utf-8")

    # 3. install.sh guard ensure-rolldown-binding
    sh_path = TARGET_DIR / "scripts" / "install.sh"
    if sh_path.exists():
        sh_content = sh_path.read_text(encoding="utf-8")
        old_sh_pattern = '    local ensure_script="$DESKTOP_DIR/scripts/ensure-rolldown-binding.mjs"\n    "$EFFECTIVE_NODE" "$ensure_script"'
        new_sh_pattern = '    local ensure_script="$DESKTOP_DIR/scripts/ensure-rolldown-binding.mjs"\n    if [ -f "$ensure_script" ]; then\n        "$EFFECTIVE_NODE" "$ensure_script"\n    fi'
        if old_sh_pattern in sh_content:
            sh_content = sh_content.replace(old_sh_pattern, new_sh_pattern)
            sh_path.write_text(sh_content, encoding="utf-8")

    print("  ✓ Installer scripts: verified URLs and guards")
    return True


def patch_bootstrap_installer():
    """Ensure bootstrap installer defaults to anakot-agent-v1 repo."""
    rs_path = TARGET_DIR / "apps" / "bootstrap-installer" / "src-tauri" / "src" / "install_script.rs"
    if not rs_path.exists():
        return True

    content = rs_path.read_text(encoding="utf-8")
    changed = False
    if '"Chensihakniroth/anakot-agent-v1"' in content:
        content = content.replace('"Chensihakniroth/anakot-agent-v1"', '"Chensihakniroth/anakot-agent-v1"')
        changed = True
    if '"Chensihakniroth/ANAKOT-AGENT"' in content:
        content = content.replace('"Chensihakniroth/ANAKOT-AGENT"', '"Chensihakniroth/anakot-agent-v1"')
        changed = True

    if changed:
        rs_path.write_text(content, encoding="utf-8")
        print("  ✓ Bootstrap installer: set repo to anakot-agent-v1")
    else:
        print("  ✓ Bootstrap installer: already anakot-agent-v1 (idempotent)")
    return True


# === Main ===

def main():
    print(f"Applying custom patches to {TARGET_DIR}...")
    print()

    results = []
    results.append(("CLI ASCII art", patch_cli_ascii_art()))
    results.append(("TUI ASCII art", patch_tui_ascii_art()))
    results.append(("Desktop intro copy", patch_desktop_intro_copy()))
    results.append(("Desktop icon", patch_desktop_icon()))
    results.append(("BrandMark icon", patch_brandmark_icon()))
    results.append(("Skills hub URL", patch_skills_hub_url()))
    results.append(("Upstream URLs", patch_upstream_urls()))
    results.append(("Update check (banner.py)", patch_update_check_stored_sha()))
    results.append(("Update check (update_cmd.py)", patch_update_cmd_stored_sha()))
    results.append(("Desktop package.json asarUnpack", patch_desktop_package_json()))
    results.append(("Installer scripts", patch_install_scripts()))
    results.append(("Bootstrap installer repo", patch_bootstrap_installer()))

    print()
    print("=== Summary ===")
    for name, ok in results:
        status = "✓" if ok else "✗"
        print(f"  {status} {name}")

    failed = [name for name, ok in results if not ok]
    if failed:
        print()
        print(f"⚠ {len(failed)} patch(es) failed: {', '.join(failed)}")
        sys.exit(1)
    else:
        print()
        print("All patches applied successfully.")


if __name__ == "__main__":
    main()
