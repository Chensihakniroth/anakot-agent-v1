---
name: hermes-port
description: Track and port upstream NousResearch/hermes-agent commits into the Anakot fork without merge conflicts.
version: 1.1.0
author: Niroth (Chensihakniroth), Anakot Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  anakot:
    tags: [upstream, port, cherry-pick, hermes, fork-maintenance]
    related_skills: [anakot-agent-skill-authoring, systematic-debugging]
---

# Hermes Upstream Porting

## Overview

Anakot is a rebranded fork of [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent). This skill tracks upstream commits and ports selected changes into Anakot without merge conflicts — the codebase has diverged too much for cherry-picks to apply cleanly, so manual adoption is the default path.

Two update identities are maintained in the source:
- **`_UPDATE_SOURCE_REPO_URL`** (`banner.py`) = `https://github.com/NousResearch/hermes-agent.git` — where new versions come from (upstream Hermes)
- **`origin`** = `https://github.com/Chensihakniroth/anakot-agent-v1.git` — your fork's remote

The tracking file lives at **`UPSTREAM_PORTING.md`** in the repo root. It is the single source of truth for what has been ported, skipped, or customized.

## When to Use

- Hermes lands a new feature or fix you want in Anakot
- You want to check how far behind upstream your fork is
- You need to port a specific commit but don't know what it changed
- You're doing periodic fork maintenance (monthly or per-release)
- Don't use for: Anakot-only features (document those in the "Anakot-Only Features" section of `UPSTREAM_PORTING.md` instead)

## Prerequisites

- Git installed and configured
- Access to GitHub API (no auth needed for public repos)
- Python 3 (for JSON parsing in terminal calls)
- `UPSTREAM_PORTING.md` exists in repo root (create from template if missing)

## Procedure

### 1. Pull Latest Upstream Commits

Run this terminal command to see the last 100 Hermes commits:

```bash
curl -s "https://api.github.com/repos/NousResearch/hermes-agent/commits?per_page=100" | python3 -c "
import json, sys
for c in json.load(sys.stdin):
    msg = c['commit']['message'].splitlines()[0]
    print(f\"{c['sha'][:8]}  {c['commit']['committer']['date'][:10]}  {msg}\")
"
```

For a specific date range:

```bash
curl -s "https://api.github.com/repos/NousResearch/hermes-agent/commits?since=2026-09-01&per_page=100" | python3 -c "
import json, sys
for c in json.load(sys.stdin):
    print(f\"{c['sha'][:8]}  {c['commit']['committer']['date'][:10]}  {c['commit']['message'].splitlines()[0]}\")
"
```

### 2. Compare Against Tracking File

Read `UPSTREAM_PORTING.md`. Any commit SHA not in the table is **new** — add it as `PENDING`.

### 3. Inspect a Specific Commit

Get the full diff for a single commit (down to the line):

```bash
curl -s "https://api.github.com/repos/NousResearch/hermes-agent/commits/<SHA>" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('=== MESSAGE ===')
print(d['commit']['message'])
print()
print('=== FILES ===')
for f in d.get('files', []):
    print(f'  {f[\"status\"]:6} {f[\"filename\"]}  (+{f.get(\"additions\",0)} -{f.get(\"deletions\",0)})')
    if f.get('patch'):
        print(f['patch'])
    print()
"
```

### 4. Search for Specific Features

```bash
# By keyword in commit message
curl -s "https://api.github.com/search/commits?q=repo:NousResearch/hermes-agent+<KEYWORD>&per_page=20" | python3 -c "
import json, sys
for item in json.load(sys.stdin).get('items', []):
    print(f\"{item['sha'][:8]}  {item['commit']['message'].splitlines()[0]}\")
"

# By file path
curl -s "https://api.github.com/repos/NousResearch/hermes-agent/commits?path=anakot_cli/update_cmd.py&per_page=10" | python3 -c "
import json, sys
for c in json.load(sys.stdin):
    print(f\"{c['sha'][:8]}  {c['commit']['message'].splitlines()[0]}\")
"
```

### 5. Port the Change

Three strategies, in order of preference:

**A) Direct cherry-pick** (only if commit touches code you haven't modified):
```bash
git remote add upstream https://github.com/NousResearch/hermes-agent.git  # one-time
git fetch upstream
git cherry-pick <SHA>
# If conflicts: git cherry-pick --abort, go to B
```

**B) Manual port** (default for divergent code):
1. Read the upstream diff from Step 3
2. Understand the **intent** (what problem does it solve?)
3. Implement the same solution in your codebase, in your style
4. Adapt naming, imports, and structure to Anakot's conventions

**C) Skip with reason** (Hermes-specific, test-only, or conflicts with Anakot customizations)

### 6. Update Tracking File

In `UPSTREAM_PORTING.md`, update the commit row:

| SHA | Date | Description | Status | Notes |
|-----|------|-------------|--------|-------|
| abc1234 | 2026-09-22 | feat: new plugin event | PORTED | Manually ported as def5678, adapted for Anakot auth flow |
| def5678 | 2026-09-22 | fix: kanban gc bounds | SKIPPED | Hermes-specific retention logic, Anakot uses custom approach |
| ghi9012 | 2026-09-22 | refactor: skills ledger | CUSTOM | Anakot has different implementation in plugins/custom/ |

**Status values:**
- `PENDING` — not yet reviewed
- `PORTED` — cherry-picked or manually adopted
- `SKIPPED` — intentionally not ported
- `CUSTOM` — Anakot has a different implementation
- `N/A` — test-only, docs-only, or rebrand-related

### 7. Commit

```bash
git add UPSTREAM_PORTING.md
git commit -m "docs(upstream): mark abc1234 as PORTED, ghi9012 as SKIPPED"
```

## Pitfalls

1. **Don't `git clone` hermes-agent on Windows** — it times out. Use the GitHub API instead.
2. **Don't cherry-pick blindly** — check if the touched files exist in your tree and whether you've modified them. Use `git diff HEAD upstream/main -- path/to/file` after fetching.
3. **Don't merge** — the codebases have diverged too much. Merge conflicts will be unmanageable.
4. **Don't ignore the tracking file** — update it every porting session. It's your only memory.
5. **Don't port rebrand-related commits** — commits that rename "hermes" → "anakot" or change branding are already handled by your custom patches.
6. **Don't port test-only commits** — mark as `N/A` unless the test reveals a real bug.
7. **Don't forget Anakot-only features** — document them in the "Anakot-Only Features" section so you know what NOT to overwrite.

## Verification

- `UPSTREAM_PORTING.md` committed on current branch
- Every new upstream commit since last session is in the table (no gaps)
- Status is accurate: `PORTED` commits exist in your tree, `SKIPPED` commits have reasons
- No merge conflicts in working tree (`git status` clean)

## Quick Reference

| Task | Command |
|------|---------|
| Latest 100 commits | `curl -s "https://api.github.com/repos/NousResearch/hermes-agent/commits?per_page=100" \| python3 -c "..."` |
| Single commit diff | `curl -s "https://api.github.com/repos/NousResearch/hermes-agent/commits/<SHA>" \| python3 -c "..."` |
| Search by keyword | `curl -s "https://api.github.com/search/commits?q=repo:NousResearch/hermes-agent+<KEYWORD>" \| python3 -c "..."` |
| Search by file | `curl -s "https://api.github.com/repos/NousResearch/hermes-agent/commits?path=<FILE>&per_page=10" \| python3 -c "..."` |
| Since date | `curl -s "https://api.github.com/repos/NousResearch/hermes-agent/commits?since=<YYYY-MM-DD>" \| python3 -c "..."` |

## Upstream Remote Setup (one-time)

```bash
git remote add upstream https://github.com/NousResearch/hermes-agent.git
git fetch upstream
# Verify: git log upstream/main --oneline -5
```

If the remote already exists, update it:

```bash
git remote set-url upstream https://github.com/NousResearch/hermes-agent.git
```

## See Also

- `UPSTREAM_PORTING.md` — tracking file (repo root)
- `anakot_cli/banner.py` — update check source reference
- `anakot_cli/update_cmd_git.py` — upstream remote management (has stale URLs to fix)
- `docs/HERMES-DOCS-REFERENCE.md` — doc adaptation guide
