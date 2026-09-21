# anakot update — review follow-up (compact)

**Repo:** `D:\School\PROJECT\anakot-agent-v1`  
**Commit updated:** `5f0df15`  
**Branch:** `main`

## What I changed

1. **Split the two update identities** (`anakot_cli/banner.py`)
   - Upstream feed = `nousresearch/hermes-agent` (verified live, 200 OK).
   - Distribution identity still this fork `Chensihakniroth/anakot-agent-v1`.
   - `_check_via_local_git` now fetches upstream, not `origin` (kills the 404 in `anakot update --check`).

2. **Cross-platform rebrand pipeline + fail-closed missing-scripts** (`scripts/rebrand/rebrand.py`, `scripts/rebrand/custom_patches.py`)
   - Rebrand now defaults to `sys.executable`, `shutil.copytree`, no hardcoded `python3`/`rsync`.
   - If `rebrand-scripts/` home overlay is missing, the pipeline skips rather than crashing — and clearly prints the missing path.

3. **Health gate before commit/push** (`anakot_cli/update_cmd_git.py`)
   - After rebrand + custom patches, but **before** commit/push, verify modules import + critical files valid.
   - On failure: keep the temp tree, print its path, do **not** commit, do **not** push.

4. **Opt-in via config** (`anakot_cli/config_defaults.py`, `anakot_cli/main.py`)
   - Behind `updates.rebrand_sync: false` by default. Reachable only when enabled.
   - Keeps the orphan-history / force-push behavior, but now opt-in.

5. **Long-term fixes completed in earlier step (still valid)**
   - `.gitignore` rebrand (rebrand tool skips dotfiles without extension → added the anakot-* twins).
   - `_pull_updates` empty-SHA guard (two failed `rev-parse` no longer read as "already updated").
   - Host-specific tests marked/reworked SSD-smart (macOS/Linux-only paths guarded, tests keep coverage on every OS where possible).

## Why this flow exists

`anakot update` should be able to:
1. fetch latest from `nousresearch/hermes-agent`
2. run `rebrand.py` to convert hermes → anakot
3. apply `custom_patches.py` for features to keep/deduct
4. **health check** that everything boots cleanly
5. then commit / push (opt-in)

This commit gets items 1–4 solid and safe. Item 5 (the actual update-facing `rebrand_sync` flag + the "push the result back to this fork" path) is intentionally left for the next step so this commit stays one concern.

## To finish on another platform

Run this first on the target machine (read-only checks, no push):

```
cd D:/School/PROJECT/anakot-agent-v1
python -m py_compile anakot_cli/banner.py \
    anakot_cli/update_cmd.py \
    anakot_cli/update_cmd_git.py \
    anakot_cli/update_contract.py \
    scripts/rebrand/rebrand.py \
    scripts/rebrand/custom_patches.py
```

Then, if the target platform supports git push to a fork (GitHub token / PAT in env or credential helper):

```
git fetch origin main
git rebase origin/main
git push origin main
```

If git push is not available or you want the update to land somewhere else first, replace the push with a local tag or a handoff note — the health gate already ensures the tree is good before any push happens.

## What to verify on the other platform

1. `python -m py_compile ...` above.
2. `tests/anakot_cli/test_update_check.py` (passive check no longer hardcodes a dead slug on this fork).
3. `tests/anakot_cli/test_update_autostash.py` and the OS-marked tests that apply to the target OS.
4. If you enable `updates.rebrand_sync`, run the actual pipeline dry-run and confirm:
   - the temp clone resolves to `nousresearch/hermes-agent`
   - `rebrand.py` runs without hardcoding python3/rsync
   - `custom_patches.py` applies after rebrand
   - the health gate catches a deliberately broken tree and refuses to commit/push
5. Confirm `.gitignore` matches the repo's actual runtime/build files.

## Notes / caveats

- `OFFICIAL_MAIN_SHA_API_LATEST` is still inert (`None`). If you want a real release-feed URL for this fork, set it; the code won't invent one.
- Some user-facing strings still reference the old upstream name in docs; that's a follow-up doc drift item, not part of this commit.
- `main.py` subcommand-level labels were intentionally left as-is to avoid touching unrelated assert paths in one commit; reconcile naming in a separate pass if desired.
