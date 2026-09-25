# Upstream Porting Tracker

This file tracks commits from [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) and their status in Anakot.

**How to use:**
1. Run the refresh command below to pull latest Hermes commits
2. For each new commit, set status: `PENDING` → `PORTED` / `SKIPPED` / `CUSTOM`
3. Add notes explaining what you did
4. Commit this file so history persists

---

## Refresh Command

```bash
curl -s "https://api.github.com/repos/NousResearch/hermes-agent/commits?per_page=100" | python3 -c "
import json, sys
for c in json.load(sys.stdin):
    msg = c['commit']['message'].splitlines()[0]
    print(f\"{c['sha'][:8]}  {c['commit']['committer']['date'][:10]}  {msg}\")
"
```

---

## Status Legend

| Status | Meaning |
|--------|---------|
| `PENDING` | Not yet reviewed |
| `PORTED` | Cherry-picked or manually ported to Anakot |
| `SKIPPED` | Intentionally not ported (Hermes-specific, conflicts with Anakot customizations, etc.) |
| `CUSTOM` | Anakot has a different/custom implementation of the feature |
| `N/A` | Not applicable (test-only, docs-only, rebrand-related) |

---

## Tracking Table

| SHA | Date | Description | Status | Notes |
|-----|------|-------------|--------|-------|
| 1c953851 | 2026-09-22 | test: write fake CA bundles to absolute path | N/A | Test-path cleanup only; Anakot uses absolute `tmp_path` fixtures directly |
| c33be87a | 2026-09-22 | fix(urllib): log default-certificates fallback once | PORTED | Per-candidate failures say they are trying the next bundle; aggregate fallback logs once |
| 7a0c8287 | 2026-09-22 | perf(urllib): key CA-context memo on preferred bundle | PORTED | Only the preferred candidate is statted and used as the memo key |
| dd0e183f | 2026-09-22 | test: pin failed preferred bundle not memoised | N/A | Test-only consolidation; covered by Anakot's parametrized failure invariant |
| 7e421538 | 2026-09-22 | refactor(urllib): drop dead None guard on CA-context memo | N/A | Behavior-neutral cleanup folded into the final-state adaptation |
| 31931491 | 2026-09-22 | refactor(urllib): key CA-context memo on file_signature | PORTED | Cache key includes mtime, size, inode, and ctime via `utils.file_signature` |
| 5fc0af70 | 2026-09-22 | fix(urllib): never memoise CA context from fallback bundle | PORTED | A context is cached only when built from the preferred candidate |
| 62475fe3 | 2026-09-22 | test: keep invariant tests for CA-bundle memo | N/A | Test-only row; Anakot adds rotation, retry, fallback, and logging invariants |
| f56b5d76 | 2026-09-22 | fix(urllib): never memoise failed CA-bundle load | PORTED | Failed preferred loads are retried on the next request |
| 966f746b | 2026-09-22 | perf(urllib): parse CA bundle once not per request | PORTED | Anakot-owned urllib requests share a preferred-bundle `SSLContext` until rotation |
| 28bd8cc0 | 2026-09-22 | fix(memory): never dedupe indented recall lines | PORTED | Indented continuation/nested lines bypass duplicate detection entirely |
| 8f618d84 | 2026-09-22 | refactor(memory): match recall bullet regex once per line | PORTED | Final-state helper evaluates one compiled bullet regex per eligible line |
| 71cb9913 | 2026-09-22 | test(bot-mode): drop unused cache fixture | PENDING | |
| 47a6f2aa | 2026-09-22 | test(memory): fold two-heading assert into repeated-bullet test | N/A | Test-only consolidation; covered by the section invariant test |
| 4607e501 | 2026-09-22 | refactor(gateway): drop test-only delivery-ledger _prune() wrapper | N/A | Anakot tests the real caller-owned transaction seam directly |
| b255c8fb | 2026-09-22 | fix(gateway): prune error in recording transaction not swallowed | PORTED | Prune failures roll back the obligation instead of silently committing an unbounded ledger |
| af0305c9 | 2026-09-22 | fix(memory): column-0 non-bullet line opens new dedupe section | PORTED | Prose, rules, markdown headings, and bold headings reset duplicate scope |
| e1760ee4 | 2026-09-22 | test: keep invariant tests for jonpol01 perf trio | PENDING | |
| a6af4041 | 2026-09-22 | docs(bot-mode): note capability epoch follows skills walker org gating | PENDING | |
| 4c41d980 | 2026-09-22 | perf(gateway): delivery ledger prunes inside recording transaction | PORTED | Record and bounded retention sweep share one lock/connection/transaction |
| e1ea7e74 | 2026-09-22 | fix(memory): repeated-bullet dedupe scoped per section | PORTED | Identical bullets under different sections are both preserved |
| 6df45711 | 2026-09-22 | perf(bot-mode): capability epoch counts invocable skills not archived | PENDING | |
| 83a1a9a2 | 2026-09-22 | fix(memory): only self-contained bullet deduped, bold heading not bullet | PORTED | Bullets with indented continuation lines remain untouched; bold headings are not bullets |
| cbe23de6 | 2026-09-22 | perf(memory): recalled line stated once per memory-context block | PORTED | Removes repeated self-contained bullets while preserving first-occurrence order and structure |
| b9ec3993 | 2026-09-22 | fix(discord): pre-seed starter dedup before awaiting mark_async | PENDING | |
| 6351d60a | 2026-09-22 | docs(gateway): point rich_sent_store restatements at _LOCK | PENDING | |
| 9bc8fed2 | 2026-09-22 | fix(gateway): await mark_async in _branch_open_thread | PENDING | |
| 4e87d3b0 | 2026-09-22 | refactor(gateway): give tracker persist real _to_thread seam | PENDING | |
| a5bdde60 | 2026-09-22 | docs(gateway): reflow mark_async docstring to 80 columns | PENDING | |
| 57111043 | 2026-09-22 | docs(gateway): stop counting mark_async callers in docstring | PENDING | |
| 70feb49b | 2026-09-22 | test(gateway): derive stall threshold from one constant | PENDING | |
| 9056bfb5 | 2026-09-22 | docs(gateway): drop references to deleted AST sweep | PENDING | |
| c60ce97b | 2026-09-22 | test(gateway): stop paying full barrier timeout on green paths | PENDING | |
| 0c417ece | 2026-09-22 | fix(gateway): ThreadParticipationTracker no longer holds lock across os.replace | PENDING | |
| c6ed9d57 | 2026-09-22 | fix(gateway): serialize rich_sent_store._update across worker threads | PENDING | |
| 38b8af39 | 2026-09-22 | test: keep invariant tests for off-loop gateway writes | PENDING | |
| f8be6db1 | 2026-09-22 | fix(gateway): ThreadParticipationTracker.clear() takes the lock | PENDING | |
| 7dd6bee3 | 2026-09-22 | fix(gateway): rich_sent_store writes run off event loop | PENDING | |
| ee8a3ded | 2026-09-22 | fix(gateway): move thread-participation persist off event loop | PENDING | |
| cb567242 | 2026-09-22 | fix(gateway): move sticker-description cache write off event loop | PENDING | |
| a472b0c0 | 2026-09-22 | chore: map daedalus-opus contributor email | PENDING | |
| f16a54bf | 2026-09-22 | fix(relay): treat "relay" placeholder as unresolved ack lane | PORTED | Unknown/empty wire platforms fall through chat lane and descriptor before choosing reactions |
| ab24fb05 | 2026-09-22 | fix(relay): use reaction Telegram allows for turn ack | PORTED | Telegram uses 👀/👍/👎; free-form platforms retain ✅/❌ |
| 836b5f82 | 2026-09-22 | fix(config): user-installed platform plugins feed env-var metadata | SKIPPED | Unsafe in Anakot's multiplexed process: import-time mutation leaks profile-owned names and lets another profile's `reload_env()` delete them; requires a profile-aware env metadata/blocklist redesign |
| 5c0e73ef | 2026-09-22 | feat(desktop): render plugin-declared settings in Plugins tab | PENDING | |
| 30de0e01 | 2026-09-22 | fmt(js): `npm run fix` on merge | PENDING | |
| 70f5dc5f | 2026-09-22 | feat(connectors): backend API for desktop Connectors page | PENDING | |
| 966d091d | 2026-09-22 | fix(aux-hooks): tolerate test seams stubbing relay metadata | PENDING | |
| 0e580956 | 2026-09-22 | feat(plugins): fire pre/post_auxiliary_call events | PENDING | |
| 9863e315 | 2026-09-22 | fix(plugins): per-plugin load deadline for hung register() | PENDING | |
| d6758299 | 2026-09-22 | test(kanban): fold workspace-survival check into gc bounds parametrize | N/A | Test-only refactor; covered by Anakot retention invariant test |
| 1c189141 | 2026-09-22 | refactor(kanban): narrow _nonnegative_int except to ValueError | PORTED | Final-state adaptation in `anakot_cli/kanban_parser.py` |
| e8ae808b | 2026-09-22 | refactor(kanban): share _retention_seconds helper across gc sweeps | PORTED | Final-state adaptation in `anakot_cli/kanban_db.py` |
| 1be926db | 2026-09-22 | refactor(kanban): drop redundant int() in gc_events cutoff | PORTED | Folded into shared retention helper adaptation |
| 9134d322 | 2026-09-22 | test(kanban): fix slash gc docstring | N/A | Test-only wording cleanup |
| 4937999d | 2026-09-22 | docs(kanban): state gc retention semantics | PORTED | Documented negative rejection and zero-disable CLI semantics |
| ca879980 | 2026-09-22 | refactor(kanban): share negative-retention ValueError message | PORTED | Folded into shared retention helper adaptation |
| e760226c | 2026-09-22 | test: collapse duplicated kanban gc retention tests | N/A | Test-only refactor; Anakot uses one parametrized invariant test |
| bf8b2d80 | 2026-09-22 | fix(kanban): reject negative retention at argparse boundary | PORTED | `_nonnegative_int` rejects destructive negative values |
| 4baff6fb | 2026-09-22 | kanban gc: validate retention flags before workspace sweep | PORTED | Command rejects invalid retention before any deletion |
| b01b1c8b | 2026-09-22 | fix(kanban): bound gc retention days so -N/0 cannot mass-delete | PORTED | Negative values fail closed; CLI zero disables event/log sweeps |
| 78dfd6e6 | 2026-09-22 | docs(skills): explain undecodable ledger warning | N/A | Test-docstring-only clarification |
| d3684a7d | 2026-09-22 | test(skills): assert missing-ledger case emits no warning | N/A | Test-only; covered by Anakot ledger invariant test |
| 14b29a42 | 2026-09-22 | refactor(skills): abort blob GC from single malformed-row guard | PORTED | Final-state adaptation in `tools/skill_ledger.py` |
| 5194561c | 2026-09-22 | refactor(skills): share _read_ledger() helper | PORTED | Shared fail-closed UTF-8 ledger reader |
| dd309d04 | 2026-09-22 | fix(skills): warn when list_entries() hits corrupt ledger | PORTED | Corrupt ledgers return empty with a warning |
| 69002c92 | 2026-09-22 | docs(skills): document unreadable ledger aborting blob GC | PORTED | `gc_blobs` docstring states unreadable/undecodable abort semantics |
| 14240116 | 2026-09-22 | test(skills): make unreadable-ledger fixture transport-agnostic | N/A | Test-only fixture refactor |
| 83cf0ef8 | 2026-09-22 | fix(skills): treat undecodable ledger as empty in list_entries() | PORTED | `list_entries` fails closed on invalid UTF-8 |
| 0c5beaad | 2026-09-22 | test(skills): pin compact_ledger() no-op on undecodable ledger | N/A | Test-only; covered by Anakot ledger invariant test |
| 2a9c27f1 | 2026-09-22 | fix(skills): warn when compaction skipped (unreadable ledger) | PORTED | Shared reader logs compaction skip reason |
| 1d6c1c2f | 2026-09-22 | fix(skills): abort blob GC on non-dict ledger row | PORTED | Non-object JSON rows abort the sweep |
| 49aa7215 | 2026-09-22 | fix(skills): warn when blob GC skipped over malformed line | PORTED | Malformed rows emit a fail-closed warning |
| 1cb30951 | 2026-09-22 | test: drop incidental encoding= edits from unrelated ledger test | N/A | Test-only cleanup |
| 25f1f6fc | 2026-09-22 | fix(skills): guard compact_ledger() against undecodable bytes | PORTED | Invalid UTF-8 leaves the ledger untouched |
| b9183820 | 2026-09-22 | fix(skills): warn when blob GC skipped (unreadable ledger) | PORTED | Shared reader warns before aborting blob GC |
| 9e1a92c8 | 2026-09-22 | fix(skills): preserve rollback blobs when ledger reads fail | PORTED | Missing, unreadable, malformed, and undecodable ledgers keep all blobs |
| b34cd9b2 | 2026-09-22 | test(stt): drop dead shutil.which patch in CAF neighbor test | N/A | Test-only cleanup; Anakot's adapted invariant test never introduced the dead patch |
| 43833ed9 | 2026-09-22 | fix(stt): tolerate CAF work-dir cleanup errors | PORTED | CAF conversion uses an owned `TemporaryDirectory(ignore_cleanup_errors=True)` |
| 2b2fd4b9 | 2026-09-22 | test: fold CAF isolation test into TestCafConversion | N/A | Test-only consolidation; Anakot keeps the invariant cases in `TestCafConversion` |
| c17dafee | 2026-09-22 | fix(stt): isolate CAF conversions from source recordings | PORTED | Caller-owned work dir prevents sibling overwrite and cleans output on success or provider failure |
| e4f76b82 | 2026-09-22 | refactor(agent): inline single-use _finish closure | PENDING | |
| 600bee92 | 2026-09-22 | test(agent): derive lean-sampling marker bound | PENDING | |
| 8e12cd92 | 2026-09-22 | refactor(agent): integer head/tail split in _bound_oversized_record | PENDING | |
| e17d4917 | 2026-09-22 | refactor(agent): drop unreachable trailing-gap branch | PENDING | |
| 56b63ecf | 2026-09-22 | refactor(agent): merge lean-sampling slices once | PENDING | |
| c2a2a626 | 2026-09-22 | test(agent): cover slices merged when extension pass closes gap | PENDING | |
| f3642a27 | 2026-09-22 | docs(agent): explain extension pass re-render | PENDING | |
| be63d5bc | 2026-09-22 | fix(agent): hand out lean-sampling headroom round-robin | PENDING | |
| 3339255a | 2026-09-22 | test: assert newest record token in lean sampling test | PENDING | |
| c94fe7a2 | 2026-09-22 | docs(agent): say sampled_chars counts display chars | PENDING | |
| eb05bde6 | 2026-09-22 | refactor(agent): pre-declare summary_input_* telemetry keys | PENDING | |
| 949d1707 | 2026-09-22 | fix(agent): spend leftover lean-sampling budget on neighbors | PENDING | |
| f94e296a | 2026-09-22 | refactor(agent): remove unreachable overflow-trim loop | PENDING | |
| 5aeef288 | 2026-09-22 | refactor(agent): drop unreachable re-trim in _bound_oversized_record | PENDING | |
| 33a1d46d | 2026-09-22 | feat(agent): record summary-input coverage telemetry | PENDING | |
| 4410ced1 | 2026-09-22 | test: keep two behavioural lean-sampling tests | PENDING | |
| a3a03d48 | 2026-09-22 | refactor(agent): sampler takes serialized records only | PENDING | |
| e28157be | 2026-09-22 | fix(agent): keep _serialize_for_summary byte-identical to main | PENDING | |
| 04fe735c | 2026-09-22 | fix: preserve structural record framing in lean summary sampling | PENDING | |

---

## Anakot-Only Features (Hermes doesn't have these)

| Feature | Location | Description |
|---------|----------|-------------|
| Hikari Pixel persona | `SOUL.md` / system prompt | Custom AI persona with neon-blue pixel aesthetic |
| StarAvenue branding font | `apps/desktop/src/styles.css` | Custom display face for wordmark |
| anakot-logo.png brand mark | `apps/desktop/public/` | Rebranded logo (replaces nous-badge.png) |
| Custom intro-reveal scenes | `apps/desktop/src/components/intro-reveal/scenes/` | Adapted cinematic intro with Anakot branding |
| Nile CMS integration | `skills/` | WordPress+WooCommerce headless CMS deployment |
| Attire Lounge POS integration | `skills/` | Multi-outlet POS system integration |
| Desktop update flow (fork-based) | `anakot_cli/update_cmd_git.py` | Simplified: pulls from origin, no rebrand scripts |
| Upstream porting tracker | `UPSTREAM_PORTING.md` | This file |

---

## Porting Log

### 2026-09-23 — Refresh: pull latest 100 Hermes commits
- Added 30 new commits (1c953851 → 04fe735c) from 2026-09-22
- Categories: urllib CA-bundle perf, memory dedupe fixes, gateway async safety, bot-mode perf, relay/discord fixes, desktop plugin settings UI
- All new commits marked PENDING

### 2026-09-22 — Initial setup
- Created this tracking file
- Pulled latest 100 Hermes commits
- All commits marked PENDING

---

## Quick Commands

```bash
# Get full diff for a specific commit
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

# Search commits by keyword
curl -s "https://api.github.com/search/commits?q=repo:NousResearch/hermes-agent+<KEYWORD>&per_page=20" | python3 -c "
import json, sys
for item in json.load(sys.stdin).get('items', []):
    print(f\"{item['sha'][:8]}  {item['commit']['message'].splitlines()[0]}\")
"

# See commits since a date
curl -s "https://api.github.com/repos/NousResearch/hermes-agent/commits?since=2026-09-01&per_page=100" | python3 -c "
import json, sys
for c in json.load(sys.stdin):
    print(f\"{c['sha'][:8]}  {c['commit']['committer']['date'][:10]}  {c['commit']['message'].splitlines()[0]}\")
"

# Check how far ahead/behind
curl -s "https://api.github.com/repos/NousResearch/hermes-agent/compare/v2026.8.31...main?per_page=1" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'Ahead by: {d.get(\"ahead_by\")} commits')
print(f'Behind by: {d.get(\"behind_by\")} commits')
"
```
