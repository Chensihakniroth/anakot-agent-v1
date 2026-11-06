#!/usr/bin/env python3
"""Copy files from a Hermes tree into the Anakot repo, applying the Anakot rebrand.

Anakot is a rebranded Hermes: the trees share most paths, but the upstream tree keeps
advancing. This tool makes the "pull the new upstream file, rebrand it" step mechanical
instead of hand-copying, which is what the fork's update workflow needs at scale.

Rebrand rules are ORDERED (longest / most specific first) and applied as whole-string
replacements. ``PROTECTED`` lists identifiers that look like branding but are infrastructure
facts (registered OAuth client ids, real API hosts) and must survive verbatim.

Usage:
    scripts/hermes_sync.py --list  tools/approval_provenance.py
    scripts/hermes_sync.py --plan  gateway/
    scripts/hermes_sync.py --apply --only-new apps/desktop/src/app/capabilities/
    scripts/hermes_sync.py --apply --only-new --allow-update agent/

    --only-new       never overwrite a file that already exists in Anakot (default: refuse updates)
    --allow-update   write over existing Anakot files when the rebranded Hermes file differs
    --dry-run        same as --plan
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_HERMES_TREE = "/tmp/hermes-tree/hermes-agent-main"

# Skip vendored / generated trees on both sides.
SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", ".venv", "venv", "__pycache__",
    ".pytest_cache", ".ruff_cache", "release", ".gradle", "target", ".vite-temp",
}

# Ordered longest-first. Each entry is a plain string replacement.
REBRAND = [
    ("hermes_cli/", "anakot_cli/"),
    ("hermes-agent-v1", "anakot-agent-v1"),
    ("hermes_agent.egg-info", "anakot_agent.egg-info"),
    ("hermes-agent", "anakot-agent"),
    ("hermes_agent", "anakot_agent"),
    ("HermesAgent", "AnakotAgent"),
    ("Hermes Agent", "Anakot Agent"),
    ("HERMES_", "ANAKOT_"),
    ("Hermes", "Anakot"),
    ("hermes_", "anakot_"),
    ("hermes-", "anakot-"),
    (".hermes", ".anakot"),
    ("hermes", "anakot"),
]

# Identifiers that look like branding but are registered infrastructure facts.
PROTECTED = [
    "hermes-cli",                  # Nous-registered OAuth client id (server-side allowlist)
    "hermes-agent.nousresearch.com",  # upstream docs host used as an HTTP-Referer
    "inference-api.nousresearch.com",
    "portal.nousresearch.com",
    "welcome-api.nousresearch.com",
    "nousresearch.com",
    "NousResearch",
]

BINARY_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".icns", ".woff", ".woff2", ".ttf", ".otf",
    ".zip", ".gz", ".tar", ".whl", ".node", ".wasm", ".pdf", ".mp3", ".mp4", ".mov",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".parquet", ".gguf", ".onnx",
}


def rebrand(text: str) -> str:
    """Apply the rebrand mapping, leaving protected identifiers untouched.

    Protection is done with placeholder sentinels so a later rule cannot rewrite a
    protected span (``hermes`` inside ``hermes-cli`` would otherwise become ``anakot-cli``).
    """
    sentinels: dict[str, str] = {}
    for i, token in enumerate(PROTECTED):
        if token in text:
            key = f"\x00P{i}\x00"
            sentinels[key] = token
            text = text.replace(token, key)
    for src, dst in REBRAND:
        text = text.replace(src, dst)
    for key, token in sentinels.items():
        text = text.replace(key, token)
    return text


def hermes_source(rel: str) -> list[str]:
    """Map an Anakot-relative path back to its Hermes-tree path (reverse rebrand)."""
    candidates = [rel, _to_hermes_dir(rel)]
    # anakot_foo.py <- hermes_foo.py
    base = os.path.basename(rel)
    if base.startswith("anakot_") and base.endswith(".py"):
        candidates.append(rel[: -len(base)] + "hermes_" + base[len("anakot_"):])
    # setup-anakot.ps1 <- setup-hermes.ps1 (and any other hyphenated brand spelling)
    if "-anakot" in base:
        candidates.append(rel[: -len(base)] + base.replace("-anakot", "-hermes"))
    return candidates


def resolve_source(tree: str, rel: str) -> str | None:
    for cand in hermes_source(rel):
        path = os.path.join(tree, cand)
        if os.path.isfile(path):
            return path
    return None


def collect(root: str, base: str) -> list[str]:
    out: list[str] = []
    for dirpath, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            out.append(os.path.relpath(os.path.join(dirpath, f), root))
    return sorted(out)


def plan(tree: str, rels: list[str], *, only_new: bool) -> tuple[list[str], list[str], list[str]]:
    """Return (new, updated, missing) repo-relative paths."""
    new: list[str] = []
    updated: list[str] = []
    missing: list[str] = []
    for rel in rels:
        src = resolve_source(tree, rel)
        if src is None:
            missing.append(rel)
            continue
        dst = os.path.join(REPO_ROOT, rel)
        if os.path.exists(dst):
            if only_new:
                continue
            try:
                if open(src, "rb").read() != open(dst, "rb").read():
                    updated.append(rel)
            except OSError:
                updated.append(rel)
        else:
            new.append(rel)
    return new, updated, missing


def apply(tree: str, rels: list[str], *, only_new: bool, allow_update: bool) -> tuple[int, int, int]:
    new, updated, missing = plan(tree, rels, only_new=only_new)
    if only_new:
        updated = []
    if not allow_update:
        updated = []
    written_new = written_upd = 0
    for rel in new:
        src = resolve_source(tree, rel)
        dst = os.path.join(REPO_ROOT, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        _write(src, dst)
        written_new += 1
    for rel in updated:
        src = resolve_source(tree, rel)
        dst = os.path.join(REPO_ROOT, rel)
        _write(src, dst)
        written_upd += 1
    return written_new, written_upd, len(missing)


def _write(src: str, dst: str) -> None:
    if os.path.splitext(dst)[1].lower() in BINARY_SUFFIXES:
        shutil.copyfile(src, dst)
        return
    try:
        text = open(src, encoding="utf-8").read()
    except UnicodeDecodeError:
        # Not UTF-8 (legacy Latin-1/Windows-1252 source, or a mislabelled binary): copy the
        # bytes verbatim rather than aborting the whole sync over one file.
        shutil.copyfile(src, dst)
        return
    open(dst, "w", encoding="utf-8").write(rebrand(text))


def expand_targets(tree: str, targets: list[str]) -> list[str]:
    """Accept Anakot-relative files or directories; directories expand against the HERMES tree.

    Expansion is driven by the source tree, because the question is "which Hermes files under
    this path are not in Anakot yet" — walking Anakot's copy would answer the wrong direction.
    """
    out: list[str] = []
    for t in targets:
        src_dir = os.path.join(tree, _to_hermes_dir(t))
        if os.path.isdir(src_dir):
            for rel in collect(tree, src_dir):
                out.append(_to_anakot_rel(rel))
        elif os.path.isfile(os.path.join(tree, _to_hermes_dir(t))):
            out.append(t)
        else:
            out.append(t)
    return sorted(set(out))


def _to_hermes_dir(rel: str) -> str:
    """Reverse the rebrand for a directory path (``anakot_cli/`` -> ``hermes_cli/``)."""
    parts = rel.split("/")
    head = parts[0]
    if head.startswith("anakot_"):
        parts[0] = "hermes_" + head[len("anakot_"):]
    return "/".join(parts)


def _to_anakot_rel(hermes_rel: str) -> str:
    """Rebrand a Hermes-tree relative path to its Anakot path (every component)."""
    return "/".join(rebrand(part) for part in hermes_rel.split("/"))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="+", help="repo-relative files or directories")
    ap.add_argument("--hermes-tree", default=DEFAULT_HERMES_TREE)
    ap.add_argument("--list", action="store_true", help="list what would change and exit")
    ap.add_argument("--plan", "--dry-run", dest="plan", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--only-new", action="store_true", help="never touch existing files")
    ap.add_argument("--allow-update", action="store_true", help="overwrite existing files when different")
    args = ap.parse_args(argv)

    if not os.path.isdir(args.hermes_tree):
        print(f"hermes tree not found: {args.hermes_tree}", file=sys.stderr)
        return 2

    rels = expand_targets(args.hermes_tree, args.targets)
    new, updated, missing = plan(args.hermes_tree, rels, only_new=args.only_new)

    if args.list or args.plan:
        for rel in new:
            print(f"NEW      {rel}")
        for rel in updated:
            print(f"UPDATE   {rel}")
        for rel in missing:
            print(f"MISSING  {rel}  (no Hermes source found)")
        print(f"\n{len(new)} new, {len(updated)} update, {len(missing)} missing, of {len(rels)} requested")
        return 0

    if not args.apply:
        print("nothing to do (pass --apply to write, or --plan to preview)", file=sys.stderr)
        return 1

    written_new, written_upd, n_missing = apply(
        args.hermes_tree, rels, only_new=args.only_new, allow_update=args.allow_update)
    print(f"wrote {written_new} new, {written_upd} updated, {n_missing} missing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
