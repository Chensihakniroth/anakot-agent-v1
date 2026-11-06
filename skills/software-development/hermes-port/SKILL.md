---
name: hermes-port
description: Port upstream Hermes commits into the Anakot fork.
version: 1.3.0
author: Niroth (Chensihakniroth), Anakot Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
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

> The Anakot checkout also carries a copy under `skills/software-development/hermes-port/`. Keep the two in sync — that copy is what Anakot Agent itself loads, this one is what loads in a Hermes session.

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
- **A pytest venv for the repo.** `scripts/run_tests.sh` probes `.venv`, then `venv`, then `~/.anakot/anakot-agent/venv`, and exits without one that has pytest. The checkout's existing `venv` often predates the dev extras — `uv sync --extra dev --extra messaging --python 3.11` creates/updates `.venv` with what the suites need. Include `--extra messaging`: several gateway suites import `aiohttp` and fail on a bare `--extra dev`.

## Procedure

### 0. Clear the carry-over queue first

Read `UPSTREAM_PORTING.md` and port every row already marked `PENDING` **before** scanning for new commits. Those rows were triaged by a previous session and are the highest-confidence work; commits found by a fresh scan are un-triaged and often resolve to `CUSTOM` or `SKIPPED` on inspection. Batch them: one logical port, one verification run, one commit.

### 1. Pull Latest Upstream Commits

See the last 100 Hermes commits:

```bash
curl -s "https://api.github.com/repos/NousResearch/hermes-agent/commits?per_page=100" | python3 -c "
import json, sys
for c in json.load(sys.stdin):
    msg = c['commit']['message'].splitlines()[0]
    print(f\"{c['sha'][:8]}  {c['commit']['committer']['date'][:10]}  {msg}\")
"
```

For a date range (preferred when scanning a window — see the API-budget pitfall):

```bash
curl -s "https://api.github.com/repos/NousResearch/hermes-agent/commits?since=<YYYY-MM-DD>T00:00:00Z&per_page=100&page=N"
```

For a **whole-range sweep** (answering "how far behind are we"), page the compare endpoint and
cache the commit list to a scratch file — a local crash then costs no re-fetch:

```bash
curl -s "https://api.github.com/repos/NousResearch/hermes-agent/compare/<last-triaged-sha>...main&per_page=250&page=N"
```

The compare response's `total_commits` is the range size and each page carries up to 250 commits.
Categorize them locally with the noise taxonomy in `references/upstream-gap-measurement.md`.

### 2. Compare Against Tracking File

Read `UPSTREAM_PORTING.md`. Any commit SHA not in the table is **new** — add it as `PENDING`. Filter the feed before recording rows; a raw feed is mostly noise.

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

Save each commit JSON to a scratch dir and re-print patches locally — do not re-fetch the same commit.

### 4. Search for Specific Features

```bash
# By keyword in commit message
curl -s "https://api.github.com/search/commits?q=repo:NousResearch/hermes-agent+<KEYWORD>&per_page=20"

# By file path
curl -s "https://api.github.com/repos/NousResearch/hermes-agent/commits?path=anakot_cli/update_cmd.py&per_page=10"
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
4. Adapt naming, imports, and structure to Anakot's conventions — see `references/anakot-seam-map.md` for the rename table and the seams that differ structurally

**C) Skip with reason** (Hermes-specific, test-only, or conflicts with Anakot customizations)

### 6. Verify

Run the touched areas through the repo runner, not bare pytest:

```bash
scripts/run_tests.sh tests/<area>/ tests/<other>.py -q
```

The runner gives CI parity (temp `ANAKOT_HOME`, `TZ=UTC`, `LANG=C.UTF-8`, `PYTHONHASHSEED=0`, per-file subprocess isolation). Add a regression test for every port; when a port changes a prompt or schema string, pin the new text in the test.

### 7. Update Tracking File

In `UPSTREAM_PORTING.md`, update the commit row:

| SHA | Date | Description | Status | Notes |
|-----|------|-------------|--------|-------|
| abc1234 | 2026-09-22 | feat: new plugin event | PORTED | Manually ported as def5678, adapted for Anakot auth flow |
| def5678 | 2026-09-22 | fix: kanban gc bounds | SKIPPED | Hermes-specific retention logic, Anakot uses custom approach |
| ghi9012 | 2026-09-22 | refactor: skills ledger | CUSTOM | Anakot has different implementation in plugins/custom/ |

**Status values:**
- `PENDING` — recorded for audit, not yet reviewed
- `PORTED` — cherry-picked or manually adopted
- `SKIPPED` — intentionally not ported
- `CUSTOM` — Anakot has a different implementation
- `N/A` — test-only, docs-only, or rebrand-related

### 8. Commit

```bash
git add UPSTREAM_PORTING.md <touched files>
git commit -m "feat(upstream): port <area> fixes and refresh the tracker"
```

Add a dated entry to the Porting Log section describing what was ported, how it was adapted, and the verification result.

## Bulk File-Level Sync

For "bring Anakot to 100% of Hermes" work, cherry-picking per commit does not scale.
`scripts/hermes_sync.py` copies Hermes's tree into Anakot with the rebrand applied:

```bash
# 1. Get Hermes main once (86 MB tarball -> 283 MB tree)
curl -L https://github.com/NousResearch/hermes-agent/archive/refs/heads/main.tar.gz -o /tmp/hermes.tar.gz
mkdir -p /tmp/hermes-tree && tar xzf /tmp/hermes.tar.gz -C /tmp/hermes-tree --strip-components=1

# 2. Plan, then apply in waves. --only-new NEVER overwrites an existing Anakot file.
python scripts/hermes_sync.py --plan --hermes-tree /tmp/hermes-tree --only-new agent/ tools/ gateway/ cron/ providers/ plugins/ skills/ scripts/ tests/ --dest .
python scripts/hermes_sync.py --apply --hermes-tree /tmp/hermes-tree --only-new agent/ tools/ gateway/ cron/ providers/ plugins/ skills/ scripts/ tests/ --dest .
# repeat for apps/ website/ docs/ docker/ nix/ .github/ evals/ pm/ and the repo root
```

Design points that matter:

- **Ordered longest-first mapping.** The rebrand table must replace the longest key first or
  `hermes_cli/` gets partially rewritten. `rebrand()` does this.
- **`--only-new` is the safety rail.** It copies a path only when the Anakot destination does not
  exist, so no Anakot customization can be clobbered. `--allow-update` is the deliberate override.
- **PROTECTED list.** Keeps upstream-facing identifiers intact: the Nous-registered `hermes-cli`
  client id, `nousresearch.com` API hosts, and attribution/copyright notices.
- **Expand targets against the HERMES tree, not Anakot's.** Passing Anakot's root walks Anakot's
  files and finds nothing new.
- **Non-UTF-8 sources.** `_write` falls back to `shutil.copyfile` on `UnicodeDecodeError`.

### What the sync cannot do: merge cases

The sync copies to the *rebranded* path even when that path already exists in Anakot. When the
rebrand is shallow (only the first path component, or only a filename prefix), Hermes-named files
land beside their Anakot counterparts and both survive. The old name is then unreferenced dead code.

After any bulk sync:

1. `find . -name "*hermes*"` and classify each hit as **rename** (counterpart absent),
   **merge/duplicate** (counterpart present), or **keep** (third-party plugin/skill identity,
   contributor identity, or a doc about Nous's Hermes Cloud product).
2. For renames: `git mv` the path, then rebrand file *contents* repo-wide so imports follow.
3. For duplicates: verify the rebranded counterpart is the **live** one (grep its stem across
   `apps/ web/ ui-tui/ anakot_cli/ docker/ nix/ plugins/ scripts/ skills/ tests/ tools/`), then
   `git rm -r` the old path. Confirm 0 references to the old name first.
4. Re-run the typecheck and the suites.

`ui-tui/packages/hermes-ink` is the sharpest example: it is a second copy of the same package
under a different directory name but the **same `name` field**, so it is a pnpm workspace-name
conflict — `tsc` exits non-zero with 0 TS errors. Delete the duplicate; do not rename it.

### Wiring gaps a bulk sync leaves behind

New modules arrive without the shared files they import. The two seen so far, both found by a
red test rather than by reading:

- `tools/browser_url_policy.py` imported `_authority_ambiguity` from `tools/url_safety.py`, which
  did not have it -> every browser URL-policy check raised `ImportError`. Port the helper
  (`_URL_EDGE_WHITESPACE`, `_url_hostname()`, `_authority_ambiguity()`) plus the always-blocked
  ambiguity floor in `is_always_blocked_url()`.
- `PluginContext` had no `register_delegation_provider`, so the bundled default delegation plugin
  failed to load and its warning polluted caplog assertions. The row existed in the unused
  duplicate module `anakot_cli/plugins_registrars.py`; it had to be added to the table that is
  actually consumed, `_SCOPED_PROVIDER_REGISTRARS` in `anakot_cli/plugins.py`.

Generalize: when a synced module imports a symbol Anakot lacks, port the symbol — do not delete
the import.

### Proving no regressions: a clean worktree baseline

A red test after a bulk sync is not automatically your fault. Get a baseline:

```bash
git worktree add /tmp/anakot-baseline <commit-before-your-changes>
ln -sfn /home/momo/anakot-agent-v1/.venv /tmp/anakot-baseline/.venv   # run_tests.sh probes .venv
cd /tmp/anakot-baseline && scripts/run_tests.sh <same-file-set> -q > /tmp/baseline.txt 2>&1
cd /home/momo/anakot-agent-v1    && scripts/run_tests.sh <same-file-set> -q > /tmp/current.txt 2>&1
```

Then diff the `FAILED` lines. A failure present in both is environmental (docker, computer-use,
voice, Windows compat) or a pre-existing host gap — say so instead of owning it. Only the
current-only set is yours to fix.

## Pitfalls

1. **Budget the GitHub API.** Unauthenticated access is 60 requests/hour/IP. Check `/rate_limit` before a long scan, page the `since` feed, filter locally, and only fetch per-commit diffs for shortlisted candidates. Re-fetching one commit's diff twice costs two requests.
2. **Never quote `ahead_by` as a feature count.** The compare API's `ahead_by`/`total_commits` includes plugin-catalog pins, CI churn, and remerge noise. Say "the compare API reports N commits, mostly catalog/CI churn — not a missing-feature count."
3. **Filter before recording rows.** Drop merges, `plugin-catalog`/`catalog`/`disclosure`/`contributor email` churn, and `test:`/`docs:`/`ci:`-prefixed commits first; group what is left into clusters and record one row per commit with the cluster named in its Notes. A 3-day window of ~800 commits filters to a few hundred candidates.
4. **`PENDING` means "recorded for audit", not "missing feature".** Say so explicitly in the log entry, or the row count gets misread as a backlog.
5. **Prove a red test is pre-existing before owning it.** `git stash push -u -m wip`, rerun the test, `git stash pop`. A failure that reproduces on the clean tree is an environment/host gap (missing optional extra, Windows-only fixture), not a regression from your port.
6. **`uv sync` dirties `anakot_agent.egg-info/`.** The editable-install metadata is tracked; `git checkout -- anakot_agent.egg-info/` before committing so generated churn does not ride along.
7. **Adapt the seam, not just the rename.** Anakot has no `hermes_platform` facts module, no `hermes_cli.auth`, and different prompt-builder/provider/gateway internals. Copying upstream code verbatim compiles-fail or silently changes behavior. `references/anakot-seam-map.md` lists the known differences.
8. **Match the meaning of a helper's return value, not just its name.** Upstream may return "did this call do the work" where Anakot returns "did anything change" — e.g. a stamp-refresh helper used to decide whether to force a second stat. Porting the name while keeping the old semantics reintroduces the double-work the upstream commit removed.
9. **Thread new fields through every consumer.** Adding a field to a shared dataclass (an approval prompt, a schema) means finding all constructors and all readers. Grep the symbol across `gateway/`, `plugins/`, and `tools/` before declaring the port done — and include the tests that pin the old shape, because a parser whose return arity you changed breaks its pinned assertions too.
10. **Enumerate Anakot's surface; do not mirror upstream's file list.** Upstream's `files[]` is a list of what *upstream* has, not of what the class of fix touches. When an upstream commit says "every native-button surface" or "all adapters", list Anakot's own implementations (`grep -rn "async def _send_exec_approval_prompt" gateway/ plugins/`) and port to all of them — Anakot carries platforms upstream does not. Missing one leaves a live security gap that reads as "already ported".
11. **Write invisible/format Unicode as `\uXXXX` escapes, never literal characters.** Redaction and display-integrity patterns need zero-width, bidi-override, variation-selector, tag-block, and private-use codepoints. Typing them literally into source mis-identifies the codepoint (visually identical characters from unrelated blocks), so the pattern silently matches the wrong range, and literal invisible characters in a command or file can trip the harness's obfuscation guard and block the operation. Build them with `chr(0x200B)` in tests and `\u200b`/`\U000e0000` in source, then assert the boundary codepoints both inside and outside each range.
12. **Don't port test-only commits.** Mark as `N/A` unless the test reveals a real bug.
13. **Don't port rebrand-related commits** — commits that rename "hermes" → "anakot" or change branding are already handled by your custom patches.
14. **Don't ignore the tracking file** — update it every porting session. It's your only memory.
15. **A bulk sync is not a merge.** `--only-new` prevents clobbering but creates duplicates wherever
    the rebrand is shallower than the path. Budget a cleanup pass: classify every `*hermes*` path as
    rename / duplicate / keep, then delete the dead ones only after proving the rebranded counterpart
    is the referenced one.
16. **Rebrand every path component, not just the first.** A mapping that only rewrites the leading
    directory leaves `ui-tui/packages/hermes-ink`, `tests/hermes_cli/`, `apps/desktop/src/hermes.ts`
    and friends behind as strays.
17. **Rebrand file contents after renaming paths**, or imports keep pointing at names that no
    longer exist. One repo-wide content pass over text files closes the loop.
18. **Check for duplicate package names, not just duplicate paths.** Two directories can hold the
    same `name` in `package.json`; only the workspace conflict reveals it, and `tsc` reports it as a
    non-zero exit with zero TS errors.

## Verification

- `UPSTREAM_PORTING.md` committed on current branch
- Every new upstream commit since last session is in the table (no gaps)
- Status is accurate: `PORTED` commits exist in your tree, `SKIPPED` commits have reasons
- No merge conflicts in working tree (`git status` clean)
- Every port has a focused regression test, and the touched-area suites are green

## Quick Reference

| Task | Command |
|------|---------|
| Latest 100 commits | `curl -s "https://api.github.com/repos/NousResearch/hermes-agent/commits?per_page=100"` |
| Commits since a date | `.../commits?since=<YYYY-MM-DD>T00:00:00Z&per_page=100&page=N` |
| Whole range since a triage point | `.../compare/<sha>...main&per_page=250&page=N` |
| Single commit diff | `.../commits/<SHA>` |
| Search by keyword | `.../search/commits?q=repo:NousResearch/hermes-agent+<KEYWORD>` |
| Search by file | `.../commits?path=<FILE>&per_page=10` |
| API budget left | `curl -s https://api.github.com/rate_limit` |
| Run the suites | `scripts/run_tests.sh tests/<area>/ -q` |
| Make the test venv | `uv sync --extra dev --extra messaging --python 3.11` |

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
- `references/anakot-seam-map.md` — upstream→Anakot rename table, structural seams, test conventions, type-checker notes
- `references/upstream-gap-measurement.md` — measuring how far behind, and the noise taxonomy for a whole-window sweep
- `anakot_cli/banner.py` — update check source reference
- `anakot_cli/update_cmd_git.py` — upstream remote management (has stale URLs to fix)
- `docs/HERMES-DOCS-REFERENCE.md` — doc adaptation guide
