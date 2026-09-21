#!/usr/bin/env python3
"""Rebrand Anakot Agent → Anakot Agent (exclusion-aware).

Usage: python3 rebrand.py [target_dir]

Excludes update-system files that need the Anakot URL for upstream tracking.
"""

import os
import shutil
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Replacements ordered longest-first / most-specific-first
# These replace hermes → anakot in functional code and display text.
# Functional URLs (hermes-agent.nousresearch.com, api.github.com/repos/nousresearch/hermes-agent)
# are protected by EXACT_SKIP_STRINGS below.
REPLACEMENTS = [
    # Module/package identifiers (functional — must be renamed)
    (r'hermes_cli', 'anakot_cli'),
    (r'hermes_state', 'anakot_state'),
    (r'hermes_logging', 'anakot_logging'),
    (r'hermes_constants', 'anakot_constants'),
    (r'hermes_home', 'anakot_home'),
    (r'hermes_bootstrap', 'anakot_bootstrap'),
    (r'hermes_time', 'anakot_time'),
    (r'hermes_startup', 'anakot_startup'),

    # Repo / URLs — EXCLUDED from update-system files
    (r'NousResearch/hermes-agent', 'Chensihakniroth/anakot-agent-v1'),
    (r'hermes-agent', 'anakot-agent'),
    (r'hermes_agent', 'anakot_agent'),

    # Dot-directories (functional — must be renamed)
    (r'\.hermes', '.anakot'),

    # Environment variables (functional — must be renamed)
    (r'HERMES_HOME', 'ANAKOT_HOME'),
    (r'HERMES_', 'ANAKOT_'),
    (r'HERMES', 'ANAKOT'),

    # TypeScript component references (functional — must be renamed)
    (r'HermesConsole', 'AnakotConsole'),
    (r'hermes-parity', 'anakot-parity'),
    (r'hermes-capability', 'anakot-capability'),
    (r'hermes-profile', 'anakot-profile'),
    (r'hermes-cron', 'anakot-cron'),
    (r'hermes-config', 'anakot-config'),
    (r'hermes-open', 'anakot-open'),
    (r'hermes-sprite', 'anakot-sprite'),
    (r'hermes-frame', 'anakot-frame'),

    # Display text (cosmetic — UI strings)
    (r'Hermes Agent', 'Anakot Agent'),
    (r'hermes agent', 'anakot agent'),
    (r'Hermes Desktop', 'Anakot Desktop'),
    (r'Hermes CLI', 'Anakot CLI'),
    (r'Hermes TUI', 'Anakot TUI'),
    (r'Hey Hermes', 'Hey Anakot'),

    # Catch remaining (functional — must be renamed)
    (r'hermes', 'anakot'),
    (r'Hermes', 'Anakot'),
]

# Files that must NOT have the upstream URL replaced
# These track the upstream Anakot repo for update detection
EXCLUDED_FILES_FOR_UPSTREAM_URL = {
    'update_cmd_git.py',
    'banner.py',
    'update_cmd.py',
}

# Exact strings that must never be replaced
# These are functional URLs/endpoints that must stay as Hermes Agent
EXACT_SKIP_STRINGS = [
    # GitHub API endpoints (update check, release info)
    'api.github.com/repos/nousresearch/hermes-agent',
    'api.github.com/repos/NousResearch/hermes-agent',
    # Docs site (skills hub, install scripts, documentation)
    'hermes-agent.nousresearch.com',
    # Git clone URLs (upstream remote)
    'github.com/NousResearch/hermes-agent.git',
    'github.com/NousResearch/hermes-agent',
    'git@github.com:NousResearch/hermes-agent.git',
    'git@github.com:NousResearch/hermes-agent',
]

SKIP_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build'}


def is_text_file(filepath):
    basename = os.path.basename(filepath)
    ext = os.path.splitext(basename)[1]
    return ext in {'.py', '.ts', '.tsx', '.js', '.mjs', '.cjs', '.sh',
                   '.yaml', '.yml', '.toml', '.json', '.md', '.css', '.html',
                   '.bat', '.ps1', '.svg', '.xml', '.txt', '.cfg', '.ini'}


def process_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='strict') as f:
            content = f.read()
    except (UnicodeDecodeError, PermissionError, OSError):
        return False

    original = content
    basename = os.path.basename(filepath)

    for pattern, replacement in REPLACEMENTS:
        # Skip the upstream-URL replacement for files that track Anakot
        if pattern == r'Chensihakniroth/anakot-agent-v1' and basename in EXCLUDED_FILES_FOR_UPSTREAM_URL:
            continue
        if pattern in content:
            content = content.replace(pattern, replacement)

    # Restore any exact skip strings that got replaced
    for skip in EXACT_SKIP_STRINGS:
        # Build the "wrong" URL that the rebrand script would have produced
        anakot_url = skip
        # GitHub repo URLs: NousResearch/hermes-agent → Chensihakniroth/anakot-agent-v1
        anakot_url = anakot_url.replace('NousResearch/hermes-agent', 'Chensihakniroth/anakot-agent-v1')
        anakot_url = anakot_url.replace('nousresearch/hermes-agent', 'nousresearch/anakot-agent')
        # Docs site: hermes-agent.nousresearch.com → anakot-agent.nousresearch.com
        anakot_url = anakot_url.replace('hermes-agent.nousresearch.com', 'anakot-agent.nousresearch.com')
        # Git clone URLs: github.com/NousResearch/hermes-agent → github.com/Chensihakniroth/anakot-agent-v1
        anakot_url = anakot_url.replace('github.com/NousResearch/hermes-agent', 'github.com/Chensihakniroth/anakot-agent-v1')
        anakot_url = anakot_url.replace('git@github.com:NousResearch/hermes-agent', 'git@github.com:Chensihakniroth/anakot-agent-v1')
        if anakot_url in content:
            content = content.replace(anakot_url, skip)

    if content != original:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except (PermissionError, OSError):
            return False
    return False


def rename_files_and_dirs():
    """Find and rename files/directories with 'anakot' in the name."""
    candidates = []
    for dirpath, dirnames, filenames in os.walk('.', topdown=False):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            if 'anakot' in fname.lower():
                candidates.append(os.path.join(dirpath, fname))
        for dname in dirnames:
            if 'anakot' in dname.lower():
                candidates.append(os.path.join(dirpath, dname))

    # Sort deepest paths first
    candidates.sort(key=lambda p: -p.count(os.sep) - p.count('/'))

    renamed = 0
    for full_old in candidates:
        if not os.path.exists(full_old):
            continue
        dirname, basename = os.path.split(full_old)
        new_basename = basename.replace('anakot', 'anakot').replace('Anakot', 'Anakot')
        if new_basename == basename:
            continue
        full_new = os.path.join(dirname, new_basename)
        if os.path.exists(full_new) and os.path.isdir(full_old) and os.path.isdir(full_new):
            shutil.copytree(full_old, full_new, dirs_exist_ok=True)
            shutil.rmtree(full_old)
        else:
            try:
                os.rename(full_old, full_new)
            except OSError:
                continue

        # Fix import inside the renamed binary script (anakot → anakot)
        if os.path.isfile(full_new):
            try:
                with open(full_new, 'r', encoding='utf-8', errors='strict') as f:
                    content = f.read()
                if 'from anakot_cli' in content:
                    content = content.replace('from anakot_cli', 'from anakot_cli')
                    with open(full_new, 'w', encoding='utf-8') as f:
                        f.write(content)
            except (UnicodeDecodeError, PermissionError, OSError):
                pass
        print(f"  renamed: {full_old} -> {full_new}")
        renamed += 1
    return renamed


def merge_leftover_dirs():
    """Merge any leftover anakot_* directories into anakot_* counterparts."""
    merge_pairs = [
        ('anakot_cli', 'anakot_cli'),
        ('tests/anakot_cli', 'tests/anakot_cli'),
        ('tests/anakot_state', 'tests/anakot_state'),
    ]
    for old_dir, new_dir in merge_pairs:
        old_path = os.path.normpath(old_dir)
        new_path = os.path.normpath(new_dir)
        if os.path.exists(old_path) and os.path.exists(new_path):
            for root, dirs, files in os.walk(old_path):
                rel = os.path.relpath(root, old_path)
                dest_dir = os.path.join(new_path, rel) if rel != '.' else new_path
                os.makedirs(dest_dir, exist_ok=True)
                for f in files:
                    src_file = os.path.join(root, f)
                    dst_file = os.path.join(dest_dir, f)
                    if not os.path.exists(dst_file):
                        shutil.copy2(src_file, dst_file)
            shutil.rmtree(old_path, ignore_errors=True)


def update_desktop_visuals(root):
    """Update desktop GUI: fonts, logo, wordmark, intro splash."""
    desktop = os.path.join(root, 'apps', 'desktop')
    if not os.path.isdir(desktop):
        print("  (no apps/desktop — skipping visual update)")
        return

    print("  Updating desktop visuals...")

    # 1. Copy fonts to assets and public (from persistent location, fallback to working copy)
    assets_dir = os.path.join(desktop, 'assets')
    public_dir = os.path.join(desktop, 'public')
    os.makedirs(assets_dir, exist_ok=True)
    os.makedirs(public_dir, exist_ok=True)

    # Persistent assets location (survives fresh clones)
    persistent_assets = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
    font_src = os.path.join(root, 'apps', 'desktop', 'assets')

    for font in ['staravenue.ttf', 'SaintCarell.otf', 'SaintCarellClean.otf']:
        src = os.path.join(font_src, font)
        if not os.path.exists(src):
            # Fallback to persistent location
            src = os.path.join(persistent_assets, font)
        if os.path.exists(src):
            dst_assets = os.path.join(assets_dir, font)
            dst_public = os.path.join(public_dir, font)
            # Make destination writable if it exists (may be read-only from git)
            for dst in [dst_assets, dst_public]:
                if os.path.exists(dst):
                    try:
                        os.chmod(dst, 0o644)
                    except OSError:
                        pass
            # Skip if source and destination are the same file
            if os.path.abspath(src) != os.path.abspath(dst_assets):
                shutil.copy2(src, dst_assets)
            if os.path.abspath(src) != os.path.abspath(dst_public):
                shutil.copy2(src, dst_public)

    # 2. Copy logo (from persistent location, fallback to working copy)
    logo_src = os.path.join(root, 'apps', 'desktop', 'assets', 'anakot-logo.png')
    if not os.path.exists(logo_src):
        logo_src = os.path.join(persistent_assets, 'anakot-logo.png')
    if os.path.exists(logo_src):
        shutil.copy2(logo_src, os.path.join(public_dir, 'anakot-logo.png'))
        shutil.copy2(logo_src, os.path.join(public_dir, 'nous-badge.png'))

    # 3. Add StarAvenue font-face to styles.css
    styles_path = os.path.join(desktop, 'src', 'styles.css')
    if os.path.exists(styles_path):
        with open(styles_path, 'r', encoding='utf-8') as f:
            css = f.read()

        if 'StarAvenue' not in css:
            font_face = """
@font-face {
  font-family: 'StarAvenue';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url('../assets/staravenue.ttf') format('truetype');
}
"""
            # Insert after the Collapse font-face
            css = css.replace(
                "src: url('../../../node_modules/@nous-research/ui/dist/fonts/Collapse-Bold.woff2') format('woff2');\n}",
                "src: url('../../../node_modules/@nous-research/ui/dist/fonts/Collapse-Bold.woff2') format('woff2');\n}" + font_face
            )
            with open(styles_path, 'w', encoding='utf-8') as f:
                f.write(css)

        # Update .wordmark to use StarAvenue
        css = css.replace(
            "font-family: 'Collapse', var(--font-sans);",
            "font-family: 'StarAvenue', var(--font-sans);"
        )
        css = css.replace(
            "font-weight: 700;\n  line-height: 0.9;\n  text-transform: uppercase;\n  letter-spacing: 0.08em;\n}",
            "font-weight: 400;\n  line-height: 0.9;\n  text-transform: uppercase;\n  letter-spacing: 0.08em;\n}"
        )
        with open(styles_path, 'w', encoding='utf-8') as f:
            f.write(css)

    # 4. Update intro.tsx font
    intro_path = os.path.join(desktop, 'src', 'components', 'chat', 'intro.tsx')
    if os.path.exists(intro_path):
        with open(intro_path, 'r', encoding='utf-8') as f:
            content = f.read()
        content = content.replace("font-['Collapse']", "font-['StarAvenue']")
        with open(intro_path, 'w', encoding='utf-8') as f:
            f.write(content)

    # 5. Update intro-reveal brand scene
    brand_path = os.path.join(desktop, 'src', 'components', 'intro-reveal', 'scenes', 'brand.tsx')
    if os.path.exists(brand_path):
        with open(brand_path, 'r', encoding='utf-8') as f:
            content = f.read()
        content = content.replace("src={assetPath('nous-badge.png')}", "src={assetPath('anakot-logo.png')}")
        content = content.replace("fontFamily: \"'Collapse', sans-serif\"", "fontFamily: \"'StarAvenue', sans-serif\"")
        content = content.replace("fontWeight: 700", "fontWeight: 400")
        with open(brand_path, 'w', encoding='utf-8') as f:
            f.write(content)

    # 6. Update intro-reveal surface fonts
    surface_path = os.path.join(desktop, 'src', 'components', 'intro-reveal', 'intro-reveal-surface.tsx')
    if os.path.exists(surface_path):
        with open(surface_path, 'r', encoding='utf-8') as f:
            content = f.read()
        content = content.replace("fontFamily: \"'Collapse', sans-serif\"", "fontFamily: \"'StarAvenue', sans-serif\"")
        with open(surface_path, 'w', encoding='utf-8') as f:
            f.write(content)

    # 7. Update side-agents scene font
    side_path = os.path.join(desktop, 'src', 'components', 'intro-reveal', 'scenes', 'side-agents.tsx')
    if os.path.exists(side_path):
        with open(side_path, 'r', encoding='utf-8') as f:
            content = f.read()
        content = content.replace("fontFamily: \"'Collapse', sans-serif\"", "fontFamily: \"'StarAvenue', sans-serif\"")
        with open(side_path, 'w', encoding='utf-8') as f:
            f.write(content)

    # 8. Update intro-copy.jsonl (display text)
    intro_copy_path = os.path.join(desktop, 'src', 'components', 'chat', 'intro-copy.jsonl')
    if os.path.exists(intro_copy_path):
        with open(intro_copy_path, 'r', encoding='utf-8') as f:
            content = f.read()
        content = content.replace('Anakot', 'Anakot').replace('anakot', 'anakot')
        with open(intro_copy_path, 'w', encoding='utf-8') as f:
            f.write(content)

    print("  Desktop visuals updated")


def build_desktop(root):
    """Build the desktop app for the current OS using smart-dist.sh."""
    desktop = os.path.join(root, 'apps', 'desktop')
    if not os.path.isdir(desktop):
        return

    print("\n=== Phase 5: Build desktop ===")

    # Use the smart-dist script which auto-detects OS
    smart_dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smart-dist.sh')
    if not os.path.exists(smart_dist):
        print("  (smart-dist.sh not found — skipping build)")
        return

    result = subprocess.run(['bash', smart_dist], cwd=desktop)
    if result.returncode != 0:
        print(f"  ✗ Build failed (exit {result.returncode})")
    else:
        print("  ✓ Build complete")


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else '.'
    os.chdir(target)

    print("=== Phase 1: Content replacements ===")
    changed = 0
    for dirpath, dirnames, filenames in os.walk('.'):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if not is_text_file(filepath):
                continue
            if process_file(filepath):
                changed += 1

    print(f"Phase 1 complete: changed {changed} files")

    print("\n=== Phase 2: File/directory renames ===")
    renamed = rename_files_and_dirs()
    print(f"Phase 2 complete: renamed {renamed} paths")

    print("\n=== Phase 3: Merge leftover directories ===")
    merge_leftover_dirs()
    print("Phase 3 complete")

    print("\n=== Phase 4: Update desktop visuals ===")
    update_desktop_visuals(target)

    print("\n=== Phase 5: Build desktop ===")
    build_desktop(target)

    print("\n=== Rebrand complete ===")


if __name__ == '__main__':
    main()
