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
| 7e85c68a | 2026-10-13 | feat(gemini): Gemini 4 Argon support with long decode | PORTED | Added Gemini 4 thinking levels, `max_output_tokens` budgets, unary/stream continuation-token hops, summed billing usage with initial-context tracking, stale-timeout floor, catalog/pricing/docs entries, and regression coverage |
| e1b18e2b | 2026-10-13 | feat(connectors): connector tools send and save local files | PORTED | Added schema path rewriting, policy-checked staging, downloaded output replacement, task-aware dispatch, and file regression coverage |
| 2d6a0e6f | 2026-10-13 | feat(gateway): connector downloads are a trusted media delivery root | PORTED | Added `<profile>/downloads/connectors` to Anakot's dynamic media-delivery allowlist |
| 5f747344 | 2026-10-13 | feat(connectors): client calls to stage file inputs and fetch file outputs | PORTED | Added typed upload wire models plus storage-only PUT/GET transport that never forwards gateway bearer headers |
| c59d2994 | 2026-10-14 | feat(agent): add nemotron super 3.5 default parameters | PORTED | Added the 1,000,000-token context fallback and 600-second reasoning stale-timeout floor for `nemotron-3.5-super` |
| cc55270e | 2026-10-14 | feat(cli): add nemotron to NVIDIA NIM default model list | PORTED | Added `nvidia/nemotron-3.5-super` to Anakot's native NVIDIA NIM picker catalog |
| 518ce272 | 2026-10-15 | fix(local): keep long local-model turns alive on laptops | PORTED | Adapted prompt-reading progress/deadline accounting, awake-time watchdog clocks, local progress notices, Windows unified-memory commit-room launch budgets, and bounded per-model prompt-cache sizing; smart approval disables hidden reasoning for one-word verdicts |
| 7934442e | 2026-10-15 | fix(gateway): reject a recycled PID that only matches start ticks | PORTED | Anakot gateway PID and runtime-status records now carry and validate the existing instantiation/boot epoch before accepting a live identity |
| c7fa3cbf | 2026-10-15 | fix(gateway): drop argv identity from host rendezvous liveness | CUSTOM | Anakot has no Hermes host-rendezvous layer; live command-line checks remain negative/profile guards, while persisted argv is not promoted to positive identity |
| 5b416e42 | 2026-10-15 | fix(gateway): anchor legacy host-record check on boot time | CUSTOM | Anakot has no Hermes legacy host record; its OS-owned runtime lock is the primary owner proof |
| 4d984677 | 2026-10-15 | fix(gateway): let host lock decide a legacy record older than this boot | CUSTOM | Anakot's lock-first PID resolution already uses the OS lock as the owner signal; no legacy host-record path exists |
| 91e63f84 | 2026-10-15 | fix(gateway): read-only host-record check never creates the lock file | CUSTOM | Anakot's runtime-lock probe is already read-only and does not create a missing lock; covered by the existing lock lifecycle contract |
| 79b3b724 | 2026-10-15 | fix(gateway): a recorded boot epoch that cannot be compared is unprovable | PORTED | Adapted the invariant to Anakot's scoped gateway locks: records now carry the existing `drain_control` instantiation epoch, mismatches invalidate a recycled PID, and an unreadable current epoch keeps the lock conservative rather than guessing |
| c3ddf756 | 2026-10-15 | fix: config watcher and config backups race conditions | PORTED | Byte-content backup dedupe replaces `filecmp` cache semantics; pairing watcher uses per-file path/mtime/size signatures so same-mtime ledger additions broadcast |
| 0eeba2d | 2026-10-16 | fix(compression): name the model that actually failed when every aux fallback is exhausted | PORTED | Restored the primary auxiliary route metadata after the fallback ladder exhausts, so compression errors identify the model/provider that originally failed |
| 8087af85 | 2026-10-16 | fix(desktop): resolve Windows shell paths before attachment previews | CUSTOM | Anakot has no separate `local-read-path` module; the portable shell-drive behavior is adapted at `wsl-path-bridge.ts`, while the broader Hermes preview boundary remains structurally different |
| 8211bb96 | 2026-10-16 | fix(desktop): keep single-letter WSL dirs on the bridge, test drive aliases on every OS | PORTED | Added pure `shellDriveToNativePath` resolution with an existence check, then wired it into Anakot's profile-aware local read bridge so real `/c`, `/cygdrive/c`, and `/mnt/c` native files win without stealing genuine WSL directories |
| 54acc3a5 | 2026-10-15 | fix(browser): lightpanda session records are written atomically | PORTED | Replaced in-place JSON writes with `utils.atomic_json_write`, preventing the orphan reaper from deleting a live session after observing a torn record |
| 046094df | 2026-10-15 | fix(browser): one real-profile decision per browser, local=true stays local, note survives errors | PORTED | Anakot's browser session layer now records the fallback reason, browser navigation emits it on the first successful result, and `browser_exec(local=true)` falls back to the local sidecar instead of a cloud browser while preserving the route |
| 2add194a | 2026-10-15 | feat(tui): standing /loop row with a live countdown above the live-work dock | PORTED | Adapted to Anakot's `@anakot/shared` contracts, `session.control.read`, and `session.control.update`; countdown is local and only the focused session renders it |
| 874d1485 | 2026-10-15 | fix(gateway): viewers get session.control.update when /goal, /loop or /heartbeat state moves | CUSTOM | Anakot already publishes the same contract from its native `tui_gateway` control snapshot path; the new TUI consumer uses it directly |
| cba95563 | 2026-10-15 | feat(cli): /loop gets a live-work dock row with a ticking countdown | PORTED | Adapted into Anakot's existing `cli_subagent_monitor` dock; the loop row appears even without subagents and owns the live countdown, while the one-shot post-turn status is suppressed when the dock is installed |
| 73b9f2af | 2026-10-15 | fix(gateway): wire the desktop window bridges for local-viewer turns | CUSTOM | Anakot's `tui_gateway/session_notifications.py::_wire_desktop_sinks` already owns the emitter and process-registry routing with Anakot session IDs |
| 80f4f989 | 2026-10-15 | fix(browser): a real profile that can't load falls back to a fresh browser | PORTED | Consent failures now create a fresh signed-out local session with a user-facing `real_profile_unavailable` note instead of failing closed; the route remains on that browser |
| 460f9bac | 2026-10-15 | fix(browser): snapshot real profile while Chrome is running | PORTED | Session cookies remain authoritative and copy with the normal budget; locked password/autofill databases use a short optional budget and are skipped so a running browser can still produce a signed-in snapshot; cookie failures remain fail-closed |
| 311155fa | 2026-10-15 | refactor(profiles): build the seed routing view once; expand `enabled` too | CUSTOM | The v0.22 profile-seed cluster (`2d3e75aa` through `311155fa`) targets Hermes' inherited model/provider endpoint seed; Anakot intentionally keeps profiles as independent islands and uses explicit clone operations instead of live endpoint inheritance |
| f9d8a740 | 2026-10-14 | feat(release): split the Microsoft Store bundle into its own windows-store lane | N/A | Hermes release/Store packaging lane; Anakot's fork has a different Windows installer and update pipeline |
| 36a8ee18 | 2026-10-15 | feat(release): choose what a stable release builds and tests with lanes | N/A | Hermes stable-release CI orchestration; no runtime behavior to port into Anakot |
| 3bdb82d6 | 2026-10-15 | fix(update): keep the retirement downgrade probe fail-closed | SKIPPED | Hermes-specific source-release update pipeline (`hermes_cli/source_releases.py`); Anakot uses fork git-based update flow (`update_cmd_git.py`) |
| a6cced55 | 2026-10-15 | fix(gateway): re-enter the native callback for a messaging /retry redispatch | SKIPPED | Hermes-specific session authority / native admission architecture (`session_ingress_context.py`); Anakot's gateway does not gate admission on event-identity callback wrappers |
| e6835fd3 | 2026-10-14 | feat(cli): add curated model list at the top in the model picker list | CUSTOM | Anakot already owns a curated-first picker in `anakot_cli/models.py`; upstream Hermes picker code is not portable |
| c5fc0958 | 2026-10-14 | refactor(agent): keep the Mistral tool-id rule beside its only consumer | PORTED | Folded into the final Anakot Chat Completions transport adaptation; route detection and stable mapping stay next to wire sanitization |
| 0c1bfb7d | 2026-10-14 | fix(agent): keep composite tool ids paired on Mistral routes | PORTED | Final-state adaptation maps the coalesced call half on assistant and tool messages, preserving prompt history unchanged |
| b33ed359 | 2026-10-14 | fix(agent): rewrite split tool ids before Mistral sees them | PORTED | Superseded by the final transport-local implementation above; nine-character ids are only emitted on Mistral-compatible routes |
| f30020ed | 2026-10-14 | fix(mcp): preserve server deadlines through outer tool execution | PORTED | Adapted to Anakot's existing `mcp_servers.<name>.timeout`: registry entries carry the resolved server budget, extended MCP calls become sequential barriers, and direct/bridged execution uses the longer deadline |
| a036b137 | 2026-10-06 | fix(discord): a programmatic voice join binds the requested text channel on every path | PORTED | Unified _bind_voice_text_channel, discard_pending on move, build_source metadata preservation |
| c3f3589e | 2026-10-06 | refactor(discord): move _component_check_auth into adapter_component_auth to keep adapter.py under its size cap | PORTED | Component authorization helper extracted to adapter_component_auth.py sibling |
| 23135fe5 | 2026-10-06 | test(discord): trim component live-auth tests to two invariants | PORTED | Parametrized helper and async revoke denial tests |
| d29d0d07 | 2026-10-06 | fix(discord): confirm a snapshot wildcard with the live check too | PORTED | Wildcard admissions validated via _component_live_auth |
| 502df01d | 2026-10-06 | fix(discord): buttons stop accepting a user revoked after connect | PORTED | Interactive views pass _component_live_auth to _component_check_auth for live per-click verification |
| 932210ec | 2026-10-05 | fix(discord): a /voice join to another text channel drops speech the receiver still holds for the old one | PORTED | VoiceReceiver.discard_pending() invoked before rebind |
| fb49ef18 | 2026-10-04 | fix(discord): capture the voice binding when a poll batch is collected | PORTED | captured_for passed to _process_voice_input to drop stale turns across rebinds |
| 88c60858 | 2026-10-06 | fix(process): a kill's result stands on every backend, and a failed scope stop never counts as stopped (#133648) | PORTED | Multi-backend exit settlement under session lock, systemd scope stop retry tracking, log_delta_command in sibling module |
| 6bf7de73 | 2026-10-05 | feat(browser): public captured CDP call seam for trusted plugins | PORTED | SUPERVISOR_REGISTRY.capture(task_id) returning socket-pinned CapturedCDP handle with rapid invalidation on disconnect |
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
| 71cb9913 | 2026-09-22 | test(bot-mode): drop unused cache fixture | N/A | Test-only cleanup of an upstream fixture; no production change to carry |
| 47a6f2aa | 2026-09-22 | test(memory): fold two-heading assert into repeated-bullet test | N/A | Test-only consolidation; covered by the section invariant test |
| 4607e501 | 2026-09-22 | refactor(gateway): drop test-only delivery-ledger _prune() wrapper | N/A | Anakot tests the real caller-owned transaction seam directly |
| b255c8fb | 2026-09-22 | fix(gateway): prune error in recording transaction not swallowed | PORTED | Prune failures roll back the obligation instead of silently committing an unbounded ledger |
| af0305c9 | 2026-09-22 | fix(memory): column-0 non-bullet line opens new dedupe section | PORTED | Prose, rules, markdown headings, and bold headings reset duplicate scope |
| e1760ee4 | 2026-09-22 | test: keep invariant tests for jonpol01 perf trio | N/A | Test-only consolidation of upstream perf-trio tests; production code unchanged |
| a6af4041 | 2026-09-22 | docs(bot-mode): note capability epoch follows skills walker org gating | PORTED | Org-gating rationale noted at the call site |
| 4c41d980 | 2026-09-22 | perf(gateway): delivery ledger prunes inside recording transaction | PORTED | Record and bounded retention sweep share one lock/connection/transaction |
| e1ea7e74 | 2026-09-22 | fix(memory): repeated-bullet dedupe scoped per section | PORTED | Identical bullets under different sections are both preserved |
| 6df45711 | 2026-09-22 | perf(bot-mode): capability epoch counts invocable skills not archived | PORTED | bot_mode_probe._skills uses iter_skill_index_files, so the epoch tracks INVOCABLE skills; archiving one moves it once, not repeatedly |
| 83a1a9a2 | 2026-09-22 | fix(memory): only self-contained bullet deduped, bold heading not bullet | PORTED | Bullets with indented continuation lines remain untouched; bold headings are not bullets |
| cbe23de6 | 2026-09-22 | perf(memory): recalled line stated once per memory-context block | PORTED | Removes repeated self-contained bullets while preserving first-occurrence order and structure |
| b9ec3993 | 2026-09-22 | fix(discord): pre-seed starter dedup before awaiting mark_async | PORTED | Dedup pre-seed precedes the awaited mark_async |
| 6351d60a | 2026-09-22 | docs(gateway): point rich_sent_store restatements at _LOCK | PORTED | Rich-sent write comment points at _LOCK |
| 9bc8fed2 | 2026-09-22 | fix(gateway): await mark_async in _branch_open_thread | PORTED | N/A — no _branch_open_thread marker lane in this tree |
| 4e87d3b0 | 2026-09-22 | refactor(gateway): give tracker persist real _to_thread seam | PORTED | helpers._to_thread is the patchable handoff seam |
| a5bdde60 | 2026-09-22 | docs(gateway): reflow mark_async docstring to 80 columns | PORTED | Docstring reflowed |
| 57111043 | 2026-09-22 | docs(gateway): stop counting mark_async callers in docstring | PORTED | Docstring generalized across adapters |
| 70feb49b | 2026-09-22 | test(gateway): derive stall threshold from one constant | N/A | N/A — upstream derived a shared stall constant from a deleted AST-sweep test |
| 9056bfb5 | 2026-09-22 | docs(gateway): drop references to deleted AST sweep | PORTED | No AST-sweep reference; docs trimmed |
| c60ce97b | 2026-09-22 | test(gateway): stop paying full barrier timeout on green paths | PORTED | Barrier timeouts are not paid on green paths |
| 0c417ece | 2026-09-22 | fix(gateway): ThreadParticipationTracker no longer holds lock across os.replace | PORTED | Split locks: the set lock never spans os.replace |
| c6ed9d57 | 2026-09-22 | fix(gateway): serialize rich_sent_store._update across worker threads | PORTED | rich_sent_store._update serialized by _LOCK |
| 38b8af39 | 2026-09-22 | test: keep invariant tests for off-loop gateway writes | PORTED | Invariant tests kept for off-loop writes |
| f8be6db1 | 2026-09-22 | fix(gateway): ThreadParticipationTracker.clear() takes the lock | PORTED | clear() takes the lock |
| 7dd6bee3 | 2026-09-22 | fix(gateway): rich_sent_store writes run off event loop | PORTED | record_async/record_media_async off-loop; Telegram/WhatsApp/Cloud call sites await |
| ee8a3ded | 2026-09-22 | fix(gateway): move thread-participation persist off event loop | PORTED | mark_async off-loop; Discord/Matrix call sites await; in-memory insert stays synchronous |
| cb567242 | 2026-09-22 | fix(gateway): move sticker-description cache write off event loop | SKIPPED | Current shared Telegram ingress reaches sticker handling before routed-profile scope; off-loop port would cache against the launch profile |
| a472b0c0 | 2026-09-22 | chore: map daedalus-opus contributor email | N/A | Maps an upstream contributor's email; not an Anakot contributor |
| f16a54bf | 2026-09-22 | fix(relay): treat "relay" placeholder as unresolved ack lane | PORTED | Unknown/empty wire platforms fall through chat lane and descriptor before choosing reactions |
| ab24fb05 | 2026-09-22 | fix(relay): use reaction Telegram allows for turn ack | PORTED | Telegram uses 👀/👍/👎; free-form platforms retain ✅/❌ |
| 836b5f82 | 2026-09-22 | fix(config): user-installed platform plugins feed env-var metadata | SKIPPED | Unsafe in Anakot's multiplexed process: import-time mutation leaks profile-owned names and lets another profile's `reload_env()` delete them; requires a profile-aware env metadata/blocklist redesign |
| 5c0e73ef | 2026-09-22 | feat(desktop): render plugin-declared settings in Plugins tab | PORTED | Backend half: plugins_settings.py renders config_schema; plugins_state.save_plugin_setting is the shared writer; plugins.manage list carries settings_schema and the new settings action writes it. Desktop form component not ported (see note) |
| 30de0e01 | 2026-09-22 | fmt(js): `npm run fix` on merge | N/A | Reformats upstream's plugin update-consent block (outcome.kind/'consent', updateConsentConfirm); this tree has no consent flow — the call returns a plain boolean |
| 70f5dc5f | 2026-09-22 | feat(connectors): backend API for desktop Connectors page | PORTED | Backend portal catalog/accounts/policy handlers and 24-hour ETag tool-list cache are present. Added a native profile-scoped Capabilities → Connectors surface with catalog/state, connect/reconnect, disconnect, forced tool-list refresh, and policy controls. Remaining: bundled-MCP `connector:` dedup/local-server merge and the full upstream account/dialog polish plus Ink `connectionSetupOverlay`. |
| 966d091d | 2026-09-22 | fix(aux-hooks): tolerate test seams stubbing relay metadata | PORTED | metadata read with str(.get(...) or "") at every call site |
| 0e580956 | 2026-09-22 | feat(plugins): fire pre/post_auxiliary_call events | PORTED | agent/auxiliary_hooks.py emits the pair at all three relay funnels; registered in VALID_HOOKS + bounded-timeout set + hooks test payloads + docs |
| 9863e315 | 2026-09-22 | fix(plugins): per-plugin load deadline for hung register() | PORTED | plugins.load_timeout_seconds (default 10s) wraps import+register on a daemon worker; ctx abandoned after overrun, late registrations refused, abandoned loaders capped at 8 |
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
| e4f76b82 | 2026-09-22 | refactor(agent): inline single-use _finish closure | PORTED | Single-use _finish closure inlined into the return |
| 600bee92 | 2026-09-22 | test(agent): derive lean-sampling marker bound | N/A | N/A - derives a marker bound from an upstream-only test constant |
| 8e12cd92 | 2026-09-22 | refactor(agent): integer head/tail split in _bound_oversized_record | PORTED | Integer head/tail split in _bound_oversized_record |
| e17d4917 | 2026-09-22 | refactor(agent): drop unreachable trailing-gap branch | PORTED | Unreachable trailing-gap branch dropped from _render |
| 56b63ecf | 2026-09-22 | refactor(agent): merge lean-sampling slices once | PORTED | Slices merged via shared _merged helper |
| c2a2a626 | 2026-09-22 | test(agent): cover slices merged when extension pass closes gap | PORTED | Gap-closing slice merge covered |
| f3642a27 | 2026-09-22 | docs(agent): explain extension pass re-render | PORTED | Extension pass re-render rationale documented |
| be63d5bc | 2026-09-22 | fix(agent): hand out lean-sampling headroom round-robin | PORTED | Extension pass hands headroom out round-robin across slices |
| 3339255a | 2026-09-22 | test: assert newest record token in lean sampling test | PORTED | Newest-record token asserted directly |
| c94fe7a2 | 2026-09-22 | docs(agent): say sampled_chars counts display chars | PORTED | Docstring states sampled_chars counts display chars |
| eb05bde6 | 2026-09-22 | refactor(agent): pre-declare summary_input_* telemetry keys | PORTED | Telemetry keys pre-declared in _record_summary_input_coverage |
| 949d1707 | 2026-09-22 | fix(agent): spend leftover lean-sampling budget on neighbors | PORTED | Leftover budget spent on whole neighbouring records, round-robin |
| f94e296a | 2026-09-22 | refactor(agent): remove unreachable overflow-trim loop | PORTED | Unreachable overflow-trim loop removed (cap holds by construction) |
| 5aeef288 | 2026-09-22 | refactor(agent): drop unreachable re-trim in _bound_oversized_record | PORTED | Unreachable re-trim removed from _bound_oversized_record |
| 33a1d46d | 2026-09-22 | feat(agent): record summary-input coverage telemetry | PORTED | summary_input_* coverage counters feed compression telemetry |
| 4410ced1 | 2026-09-22 | test: keep two behavioural lean-sampling tests | N/A | N/A - upstream test reshuffle; Anakot keeps one parametrized invariant test |
| a3a03d48 | 2026-09-22 | refactor(agent): sampler takes serialized records only | PORTED | Dual-signature wrapper dropped; sampler takes records only |
| e28157be | 2026-09-22 | fix(agent): keep _serialize_for_summary byte-identical to main | PORTED | _serialize_for_summary stays byte-identical; records carry no rstrip |
| 04fe735c | 2026-09-22 | fix: preserve structural record framing in lean summary sampling | PORTED | _serialize_records_for_summary keeps turn boundaries structural |
| e33fd7e0 | 2026-09-27 | fix(desktop): run updater state.db pre-flight through the installation launcher | PORTED (partial) | Ported the WAL-safe snapshot core. The PM-managed `resolveInstallationLauncher` shim was SKIPPED — Anakot has no `pm/` managed-checkout concept (`grep -c resolveInstallationLauncher` = 0), so porting it would be dead code |
| 4de06d1d | 2026-09-20 | fix(desktop): honour updates.pre_update_backup=off in the Desktop updater preflight | PORTED | Adapted into the existing shared `preflightStateDb` seam (no `resolveAnakotBackend` port): the probe runs the SELECTED checkout's own CLI with an explicit profile, so managed scope, defaults and `${ENV}` expansion stay backend-owned instead of re-parsing YAML in Electron. Any probe failure (missing CLI, malformed output, nonzero exit, 15s timeout) keeps the unchanged WAL-safe snapshot |
| 37fd6440 | 2026-09-20 | fix(desktop): honour updates.pre_update_backup=off ... again | PORTED | Upstream re-gated in the composition root because the checkout strategy called `preflightStateDb` unconditionally. Anakot has one shared preflight called from BOTH `applyUpdates` and `applyUpdatesPosixHandoff`, so the gate belongs inside it — one edit covers both lanes and no caller can drift |
| 0b088a78a | 2026-10-05 | fix(agent): don't promote Anthropic summarized thinking to the final answer | PORTED | Guard in `turn_final_response.py` checks `reasoning_details` for signed thinking blocks or `*.native_assistant` carriers |
| 762f419fe | 2026-10-05 | fix(approval): MCP/vault consent declines at once when no user can answer | PORTED | Early-return in `approval_prompt.py` for single-query/cron/unattended-platform contexts |
| f33d81740 | 2026-10-05 | fix(agent): name a final that reuses an already-delivered response | PORTED | `_reused_response_text` identity in turn_context/empty_response/finalizer; `response_reused` on TUI wire contract |
| fdcae6deb | 2026-10-05 | fix(cli): stop _apply_featured() shortlisting user-defined providers | PORTED | Uses `is_routing_aggregator()` + `is_user_defined` guard instead of model-id spelling heuristic |
| 35f878697 | 2026-10-05 | feat(agent): truncated context files name the sections that were dropped | PORTED | `_omitted_headings()` helper + marker update in `prompt_builder.py` |
| d63cdd32a | 2026-10-05 | fix(discord): an auto-threaded mention reads the new thread's topic | PORTED | `effective_channel` instead of `message.channel` in Discord adapter |
| eaecc99c7 | 2026-10-05 | fix(discord): upsert recreated slash commands without delete-first step | PORTED | Removed `delete_global_command` before upsert; rate-limit resilient |
| 675bad762 | 2026-10-05 | fix(discord): resolve allowlisted usernames by username only, not display name | PORTED | Security fix: display names are user-controlled; match only `member.name` |
| 0df1837e8 | 2026-10-05 | fix(approval): fire observer hooks for the two hookless classic-CLI prompts | PORTED | `pre/post_approval_request/response` hooks in elicitation + protected-write paths |
| 7ef5aca07 | 2026-10-05 | fix(gateway): hand Telegram held inbound to the rebuilt adapter | PORTED | `adopt_held_inbound` + `carry_inbound_dedup(predecessor)` + `hand_over_held_inbound` |
| 0104b9810 | 2026-10-05 | fix(auxiliary): preserve Codex completion status and phase | PORTED | Shared normalizer via `auxiliary_codex_response.py`; `recover_leaked_tool_call=False` for aux |
| c8c44312d | 2026-10-05 | fix(auxiliary): preserve route-aware Responses normalization | PORTED | `issuer_kind`/`issuer_model` propagation through `resp_kwargs["_issuer_kind"]` |
| 7fb344f92 | 2026-10-05 | fix(gateway): give in-flight api_server runs the cron drain floor | PORTED | `_still_draining()` groups `(cron or api)` under `cron_deadline` |
| fb5bba80d | 2026-10-05 | fix(security): ignore spoofed XFF for dashboard login limits | PORTED | `client_ip()` returns ASGI peer only; no `X-Forwarded-For` parsing |
| 9023a4af8 | 2026-10-05 | fix(memory): stage headless single-query writes | PORTED | `_interactive_approval_available()` gates inline prompt on single-query context |
| ed4c35076 | 2026-10-05 | fix(dashboard-auth): cap request bodies on the public auth routes | PORTED | `AuthBodyLimitMiddleware` (64KB) registered innermost in web_server |
| 5af47ddcd | 2026-10-05 | fix(compaction): retain oversized typed user text at checkpoint boundary | PORTED | `_input_text_parts_cost` + `_truncate_input_text_parts` in native_compaction.py |
| 1f1bb5cd | 2026-10-16 | fix(tools): read_file on a pruned spill archive says "expired" | PORTED | `read_file` now distinguishes an expired persisted-result archive from an ordinary missing path, including cached not-found retries; ordinary files keep the normal error shape |
| 309fddab | 2026-10-16 | fix(tools): spill pointers in structured content and Windows paths count as references | PORTED | `tools/tool_result_storage.py` uses `instr()` for NUL-prefixed structured content and accepts both path separators; the state-db sweep/delete regression covers retained and released archives |
| 6dcf6358 | 2026-10-16 | fix(state): capture spillover pointers in the shared deletion fence | PORTED | `anakot_state_media.py` records candidates in profile-local `state_meta` before every message-bearing delete path and collects them after commit; shared references survive until their last session is removed |
| b26bb96d | 2026-10-16 | fix(mcp): a lazy server whose first connect failed is not ready | CUSTOM | `tools/mcp_tool_discovery.py::get_mcp_status` already gives failed lazy registrations `failed` precedence over `lazy`, so the false-ready state is covered by Anakot's native status path |
| 4e0806d5 | 2026-10-16 | fix(approval): skip the execute_code gate only while an approving viewer is attached | CUSTOM | Anakot has no Hermes `SessionAuthority` viewer/subscriber capability boundary; approval visibility is owned by the session-scoped notifier/approval transport, so importing the upstream viewer exemption would guess at attachment state |
| 073a3af5 | 2026-10-16 | fix(platforms): the terminal secret blocklist reads no plugin files at import (safe mode) | CUSTOM | Anakot's local environment policy uses static/core config registries and does not scan plugin adapter files from `_build_provider_env_blocklist`; the safe-mode import-time file-scan regression does not exist in this architecture |
| 440c9b61 | 2026-10-17 | fix(browser): cap redaction walks so nested page data cannot crash | PORTED | Added bounded browser snapshot/CDP redaction; hostile page-controlled JSON is replaced with a marker instead of raising or leaking the unread remainder |
| 870633cb | 2026-10-17 | fix(browser): raise the redaction walk cap so real DOM trees survive | PORTED | Final-state cap is 320 JSON levels: Chrome-depth DOM trees survive while hostile 2,000-level values are still cut off; focused browser redaction neighbors pass |
| d5c74fc1 | 2026-10-17 | fix(terminal): a foreground command ending in a lone trailing & runs as a tracked background process instead of being refused | PORTED | `trailing_amp_background_command` converts only the sole unambiguous trailing `&` for foreground or explicit background calls; the real terminal pipeline runs the stripped command through approval and process tracking |
| 390b1e38 | 2026-10-17 | fix(terminal): trailing-& conversion never tells the model to re-launch the process | PORTED | The tracked spawn path emits `auto_backgrounded`; silent/actionable relaunch hints are suppressed for automatic conversions, while CI guidance is retained only as non-actionable diagnostics |
| c8be4526 | 2026-10-17 | fix(terminal): trailing-& conversion refuses substitutions, keeps approval identity and escaped spaces | PORTED | Refuses executable substitutions and shell-carrier variants (paths, env prefixes, quoted/variable names, attached `-c`), requires the full local approval identity to match before conversion, and preserves backslash-escaped whitespace; focused terminal guard/pipeline tests pass |
| 1237193f | 2026-10-17 | fix(windows): dirs made while elevated stay usable; an unusable token-lock dir parks once | PORTED | `ScopedLockDirUnusable` names the shared lock directory and platform repair command, warns once per directory, and rejects unreadable existing token locks without inventing a holder conflict; the broader Hermes `hermes_dir_acl` helper is intentionally not imported |
| e541f21e | 2026-10-17 | fix(gateway): an unusable token-lock dir keeps the adapter retryable, so a token-only gateway stays up | PORTED | `BasePlatformAdapter` parks `lock_dir_unusable` as retryable; startup remains alive with only a token-locked platform configured and the reconnect watcher can pick up a repaired directory without restart; focused gateway tests pass |
| 49b42a8b | 2026-10-17 | fix(sessions): reconcile declarative drift during explicit repair | PORTED | Added `anakot_state_reconcile.py`: explicit repair probes declared tables/columns, repairs an isolated snapshot, preserves history-table loss, and routes `anakot sessions repair` to the additive path; 7 focused tests pass |
| af586e5a | 2026-10-17 | fix(sessions): reconcile columns before dependent indexes on repair snapshots | PORTED | Reuses Anakot's `SessionSchemaMixin._reconcile_columns()` before canonical DDL so a missing indexed column is restored before its index; covered by the declarative-repair regression |
| f4c559e3 | 2026-10-17 | fix(sessions): verify history tables on the guarded repair snapshot | PORTED | Validates `sessions` and `messages` both before repair and inside the staged snapshot, refusing promotion when canonical history is missing |
| 1eda335a | 2026-10-17 | fix(sessions): catch a lagging state.db up once on browse instead of 503 | PORTED | Read-only dashboard opens now reconcile declared drift once only when the profile `gateway.lock` is free; owned stores return a restart 503, while unowned stores reopen read-only after transactional additive DDL |
| 42a94335 | 2026-10-17 | fix(sessions): never write browse DDL into a corrupt lagging store | PORTED | Read-only `PRAGMA integrity_check` plus FTS probes run while the profile locks are held; corrupt stores and missing canonical history tables are refused without modifying the database; browse/state regression suites pass |

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

### 2026-10-15 — Upstream feature scan at `db44c46208f1`
- Scanned 300 latest Hermes commits and filtered 12 untracked user-facing feature commits after excluding release-only, catalog, docs, test-only, merge, and formatting noise.
- Confirmed the gateway coding-posture refactor cluster is already represented by Anakot's `agent/coding_context.py` and session policy implementation; the curated-first model picker is an Anakot-owned custom implementation.
- New parity candidates recorded in the table: connector file staging/output delivery (partial/absent), and Nemotron Super 3.5 defaults (not yet matched). Gemini 4 Argon was ported in the follow-up batch below.

### 2026-10-15 — Ported Gemini 4 Argon long decode (`7e85c68a0d93`)
- Added `agent/gemini_long_decode.py` for the Gemini continuation protocol: `CONTINUATION` hops preserve the request and send the returned token, unary responses merge model parts and usage, and streamed continuation finishes remain invisible to callers while the next hop is opened.
- Extended native Gemini translation with 20-minute read headroom, long-decode budgets (`xhigh` 262,144; `max`/`ultra` 1,048,576), hidden-thinking accounting, and `initial_prompt_tokens` so billing totals do not masquerade as current context size.
- Added Gemini 4 thinking-level clamping, a 600-second reasoning stale-timeout floor, Gemini 4 catalog/pricing entries, and AI Studio/Vertex guide updates. Regression coverage exercises profile wiring, unary hops, stream hops, usage, and catalog-independent policy helpers.

### 2026-10-16 — Follow-up scan + port: auxiliary fallback route identity (`0eeba2d7a263`, upstream head `0eeba2d7a263`)
- Refreshed the latest 100 Hermes commits after the previous `60f56a6b13c8` scan. The new upstream head is `0eeba2d7a263`; filtered merge, release, CI, catalog, formatting, and test-only noise.
- Selected the portable compression fix: fallback candidates update `route_info` while they are attempted, so the ladder now snapshots and restores the primary provider/model when every candidate is exhausted. The user-visible compression failure therefore names the model that actually failed first, not the last fallback candidate.
- Ported the Lightpanda record half of the scan (`54acc3a5`): `_write_record` now uses `utils.atomic_json_write`, so the orphan sweep cannot mistake a partially-written JSON record for a dead server. The broader Hermes preview-boundary portion of the Windows shell-path cluster (`8087af85`) remains `CUSTOM` pending a separate architecture match.
- Verification: `scripts/run_tests.sh tests/tools/test_browser_lightpanda.py -k "write_record or orphan_reaper_survives_non_dict_record" -q` — 2 passed; `python -m py_compile tools/browser_lightpanda.py` passed. The full Lightpanda file had 44 passed and one unrelated Windows environment failure in an existing cached-engine test.

### 2026-10-16 — Ported Windows shell-drive resolution (`8211bb96eddb`)
- Added `shellDriveToNativePath` to Anakot's existing profile-aware `wsl-path-bridge.ts`. It recognizes Git Bash, Cygwin, and drvfs spellings (`/c/...`, `/cygdrive/c/...`, `/mnt/c/...`) only when the corresponding native file exists; otherwise genuine single-letter WSL directories continue through the WSL bridge.
- Kept the broader Hermes `local-read-path` attachment module out of the tree because Anakot has a different preview/read architecture; the behavior is wired at the existing filesystem bridge seam.
- Verification: targeted Electron Vitest `wsl-path-bridge.test.ts` — 13 passed; targeted ESLint passed. Desktop typecheck remains blocked by unrelated existing `connection-request`/`unavailable` errors.

### 2026-10-16 — Ported running-browser real-profile snapshots (`460f9bac`)
- Adapted `anakot_cli/browser_connect.py` so session cookies (`Cookies`) remain the authoritative signed-in state with the normal backup budget, while password/autofill databases use a short optional budget and are logged/skipped when a running browser holds them locked.
- A cookie snapshot failure still fails closed; the system never launches a supposedly signed-in real-profile session without session cookies. Updated the invariant tests and compatibility seams for the new deadline parameter.
- Verification: snapshot-error tests — 3 passed; real-profile unreadable-cookie regression — 1 passed; `python -m py_compile anakot_cli/browser_connect.py` passed. The broader Windows real-profile file still has unrelated mode-bit/relaunch failures.

### 2026-10-16 — Hermes v0.22.2 release scan (`d923a5eb`, upstream tag `v0.22.2`)
- The release is not one new feature: v0.22.2 corrects the accidentally assembled v0.22.1 release and rolls up the v0.22 line. The two release highlights are reboot-safe supervised gateway startup and long local-model turns that survive laptop sleep/prompt prefill.
- Anakot already has the Nemotron Super 3.5 defaults (`c59d2994`), a custom curated-first model picker (`e6835fd3`), local model load/prefill progress, and its own gateway lifecycle/lock architecture. The NVIDIA NIM picker addition (`cc55270e`) is ported in this batch.
- The local-model hardening cluster (`518ce272`) is ported natively: prompt-reading progress extends only for newly-read tokens, awake-time watchdogs ignore Windows sleep, compression streams share the deadline, and unified-memory launch/prompt-cache budgets use Windows commit room. The gateway boot-epoch invariant (`79b3b724`) is ported through Anakot's native scoped-lock path rather than Hermes' `host_rendezvous.py`.
- Release-only lanes, plugin-catalog additions, and Hermes-specific packaging changes are not blanket ports. Smart-approval's one-word verdict reasoning guard from the local-model cluster is adapted in `tools/approval_smart.py` in this batch.
- The local-model hardening port is complete: `local_prompt_progress.py` requests and parses llama-server prefill progress, auxiliary/main streams subtract or surface verified prompt-reading time, stream watchdogs use the awake-time clock, and `HardwareBudget`/presets now carry Windows commit room into launch and prompt-cache sizing. Focused agent/local-runtime tests are green.
- The gateway restart slice is adapted in `gateway/status.py`: scoped-lock records include `drain_control.current_instantiation_epoch()`, definite epoch mismatches stale the record, and an unreadable current epoch returns an unprovable/conservative result. Two lock-liveness invariants cover the mismatch and fail-safe cases.
- The remaining real-profile lifecycle slice is adapted: a consented snapshot/launch failure now returns a fresh browser with an explicit signed-out note; successful navigation delivers that note once, and Browser Use local requests never cross over to the cloud backend after a real-profile failure. The full real-profile suite still exposes pre-existing Windows mode-bit/relaunch fixtures, while the focused fallback invariant passes.
- The release-only Windows Store/stable-lane changes and Hermes plugin-catalog additions are recorded as non-runtime evidence rather than copied into Anakot's different installer/catalog surfaces. The profile seed cluster is explicitly `CUSTOM` because live profile inheritance conflicts with Anakot's intentional profile isolation.

### 2026-10-16 — Post-v0.22.2 upstream-head follow-up (`6206f893`)
- Refreshed the official Hermes `main` feed and head. The current head is `6206f89320f3506c901948be0f487eae7f2b0d71`; the newest feed entries are predominantly plugin-catalog pin/disclosure churn and test-only changes.
- Ported Hermes `ecffe12eae3691e728869c77c6f0c0fb7ad97400` (Telegram progress code-fence preservation) as an Anakot-native adaptation in `gateway/run_turn_runner.py`: repeated progress counters now appear after a closing Markdown fence instead of turning the counter into invalid fence text. Focused gateway verification: 49 tests passed.
- Ported Hermes `c09527ad4f5bc2d710fec50198afae881b75bfed` (Codex selected-credential service-tier negotiation) as an Anakot-native adaptation: the authenticated Codex catalog is cached per token fingerprint, known unsupported `priority` requests are omitted, and unknown catalog results preserve the user's request. Focused agent verification: 5 tests passed.
- Ported Hermes `690b75a31a6da0f925d23f1024072793f1bc0872` (Ultrafast picker and `/fast ultra` surface) as an Anakot-native surface extension: CLI, gateway, TUI gateway, Ink TUI, persisted service-tier parsing, and documentation now accept `ultra`/`ultrafast`; account negotiation keeps it only when the selected Codex account advertises Ultrafast, otherwise downgrading to Priority or standard. `ui-tui` TypeScript typecheck passed; focused Python fast-mode tests passed.
- Ported Hermes `d0e40fff3c343b9e5e31ec9f562a5f10d37bc296` (per-account usage cache) as an Anakot-native adaptation: account-identity/profile-keyed snapshots, stale-state detection, late-fetch protection, refresh throttling, and background legacy/per-credential refresh are now available through `agent/account_usage_cache.py`; `AccountUsageSnapshot` carries the non-secret identity used for pool isolation. `anakot_cli.inventory` now attaches fresh cached usage windows to model-picker provider rows without blocking on network fetches. Focused cache/inventory verification: 24 tests passed.
- The current feed's catalog pin/disclosure commits (`6206f893`, `ae896f88`, `0f808899`, `9ba09732`, `e1a8c665`, `c3ff0701`, `dedfde40`, `3ee0e7f7`, `89647c1f`, `53bec2a3`, `8e8eca87`, `37d9a5ab`, `d4c737ca`, `724b1da0`, `7b8b5727`, `87141251`) are **N/A/CUSTOM**: they update Hermes' external plugin catalog and disclosures, while Anakot uses its own plugin discovery/catalog and does not vendor Hermes plugin pins.

### 2026-10-16 — Full Hermes parity baseline (`6206f893`)
- Scanned the current official Hermes `main` Atom feed after closing the v0.22.2 release line. The newest commits are gateway/CLI Bot Mode and session-store fixes, not a new tagged release.
- `28fd653b87e7c729f2a62702cdf093886e145c08` (`session.resume latest` includes the owner's `source='local'` rows) is **CUSTOM**: Anakot's resume path and session ownership are implemented through `anakot_state`/TUI gateway contracts rather than Hermes' `gateway/session_local_title.py` and `created_source` index. No same-shaped lookup was found to port safely.
- `bd4a93b7301e41ff407f63f3a4f2815f2138a63f` (retry transient SQLite schema probes) and `33c5256897df` (do not cache failed/negative probes) are **CUSTOM / already covered**: Anakot's profile-aware `SessionDB._read_all` is the shared read seam and migrations do not use Hermes' lazy `created_source` compatibility probe. Adding a second schema-probe cache would duplicate the state layer.
- `0b76ea80274b8b5992f04e97df9542cee1dc8d27` (owner-state Bot delivery refusals remain resendable) is **CUSTOM**: Anakot's `tools.bot_relay` queues file envelopes and uses tri-state roster liveness; it has no Hermes admission/receipt pin state or `runtime_draining`/`stale_epoch` refusal protocol. The existing `runtime_offline` fail-fast behavior is intentionally preserved.
- `3fe2cd6f50be` and the adjacent Bot Chat admission series are **CUSTOM** pending a protocol-level equivalence; current Anakot Bot Mode already has a separate `bot_relay`/live-mailbox contract. These commits are not silently treated as direct ports.

### 2026-10-16 — Full Hermes parity baseline (`e5eb6b36fe78`)
- The goal is now **full upstream capability parity**, not merely the applicable v0.22.2 release behavior. This means continuing to reconcile Hermes `main` as it evolves, while preserving Anakot's native architecture and profile/security boundaries.
- Downloaded and inventoried the official Hermes `main` tree at `e5eb6b36fe78eb012cefd1f5f436cd458411b8b3` and compared it with the current Anakot tree. The trees contain 10,990 shared paths, 8,785 Hermes-only paths, and 43,690 Anakot-only/generated/vendor paths after excluding build caches and dependency directories. This confirms that the full-parity effort is **not complete**.
- The `v0.22.2` tag resolves to `7b77e29eedd85a8497ce2821448dac7964dc46f6`; the current upstream `main` has advanced beyond that tag. Future ports will be tracked against exact upstream SHAs and categorized `PORTED`, `CUSTOM`, or `N/A` rather than treating a release number as proof of parity.
- Ported Hermes `82c77ff9b98a7efea77460cc481cb53d78e9ad4d` (`openai-native` web backend) natively: added the bundled web-provider marker and read-only Codex credential probe, and taught the Codex Responses transport to replace Anakot's client `web_search` function with OpenAI's server-side `{"type": "web_search"}` tool when `web.search_backend: openai-native` is selected. Focused provider/transport verification: 140 tests passed.
- Ported Hermes `a2b6f53245202ccc9f56c13ad1ae606bf7812b2a` (delegation recovery diagnostics) natively: durable async-delegation records now retain the owner's cwd and task transcript paths, owner-death recovery attaches bounded transcript tails and a git branch/commit/dirty-count snapshot, and both single and batch notification renderers include the evidence. Focused delegation/process verification: 116 tests passed.
- Do not bump Anakot's package version solely because behavior was ported. The version remains `0.21.3` until a deliberate Anakot release is cut after the full parity work and release checks are complete.

### 2026-10-16 — Refresh + port: standing `/loop` live-work row (`2add194a`, upstream head `60f56a6b13c8`)
- Scanned the latest 100 Hermes commits from the GitHub API after the `046094df` browser-lifecycle scan; filtered merge, release, CI, catalog, formatting, and test-only noise.
- Ported the portable TUI feature manually: the focused Anakot TUI now reads `session.control.read`, consumes `session.control.update`, and renders an active/paused `/loop` row above the live-agent panel with a local countdown and prompt preview.
- Reused Anakot's existing `LoopSnapshot` contract and gateway publication path instead of copying Hermes modules. Completed loops are hidden, paused loops show their reason, and non-focused session snapshots cannot bleed into the active TUI.
- Verification: `npm run typecheck`, `npm run lint` (0 errors; 4 pre-existing warnings), and targeted Vitest (`116 passed`). `cba95563` is ported separately below; `874d1485` and `73b9f2af` are `CUSTOM` because Anakot already has the corresponding gateway publication and desktop sink paths.

### 2026-10-16 — Ported classic CLI loop dock (`cba95563d41b`)
- Added the standing loop row to Anakot's existing `cli_subagent_monitor` instead of importing Hermes' dock modules. It renders with or without live subagents, reserves the dock's existing bounded surface, and updates its countdown through the monitor's normal one-second polling/invalidation path.
- Suppressed the redundant one-shot `/loop` remaining-status line when the dock is installed; the dock becomes the single live countdown surface.
- Verification: `scripts/run_tests.sh tests/anakot_cli/test_loops.py tests/anakot_cli/test_subagent_dock_collapse.py -q` — 72 passed; neighboring subagent monitor/dock tests — 11 passed.

### 2026-10-15 — Follow-up upstream scan at `046094df28b7`
- Scanned the latest 100 Hermes commits after the previous `db44c46208f1` scan and filtered release/chore/test/CI-only changes.
- Recorded the new browser real-profile lifecycle cluster (`046094df`, `80f4f989`, `460f9bac`) as `PENDING` for a dedicated browser session audit.
- Evaluated update candidate `3bdb82d6` (Hermes-specific `source_releases.py`; Anakot uses git updates) and gateway candidate `a6cced55` (Hermes-specific `session_ingress_context.py` native callback validation; Anakot does not use event-identity callback gating for /retry admission); marked both as `SKIPPED`.
- Ported the portable config-backup and pairing-watcher race fix below. The newer plugin server-declaration change has no same-shaped declaration layer in Anakot and remains intentionally unported pending a contract gap.

### 2026-10-15 — Ported config watcher and backup race fixes (`c3ddf7563bff`)
- Replaced `filecmp.cmp` in `anakot_cli/config_backups.py` with byte comparison so equal-size edits within one filesystem mtime tick still create a backup.
- Added per-file `(path, mtime_ns, size)` signatures to `tui_gateway/change_watcher.py` for pairing ledgers, preventing a second same-mtime file from being masked by the newest-mtime-only signature.
- Regression verification: config-backup tests and the full change-watcher file passed.

### 2026-10-15 — Ported connector file inputs and outputs (`e1b18e2bca67`, `2d6a0e6f32f2`, `5f7473446b48`)
- Added `tools/connectors/gateway/files.py`: connector schemas now expose uploadable values as local paths, remember nested/array file argument locations, validate paths through Anakot media-delivery policy, stage inputs through presigned uploads, and replace returned presigned URLs with profile-local downloaded paths.
- Added storage-only upload/download methods to `ConnectorClient`; storage receives only the gateway-issued headers, never the managed gateway bearer. Downloads use bounded streaming, safe unique names, temporary files, and the profile-aware `downloads/connectors` root.
- Threaded `task_id` through connector dispatch so relative paths resolve against the calling terminal workspace. Added 10 regression tests covering schema refs, arrays, refusal/caps, storage header isolation, output sanitization, and media allowlisting. Connector bridge/dispatch suites remain green.

### 2026-10-15 — Ported Nemotron Super 3.5 defaults (`c59d299408e9`)
- Added `nemotron-3.5-super` to the model-metadata fallback table at 1,000,000 context tokens and to the 600-second reasoning stale-timeout floor. Focused metadata and timeout verification: 183 tests passed.

### 2026-10-15 — Ported Mistral composite tool-id compatibility
- Ported the final state of upstream `b33ed35968f0`, `0c1bfb7dfb47`, and `c5fc0958b49f` into `agent/transports/chat_completions.py`.
- Mistral routes (provider, host, or model-marker detected) map the coalesced call id to a stable nine-character base62 id on the wire, on both assistant calls and tool results. Persisted history stays untouched, including composite `call_id|response_item_id` values.
- Added `tests/agent/test_mistral_tool_ids.py` and updated the provider wiring invariant. Focused transport/provider tests: 81 passed.

### 2026-10-15 — Ported MCP server deadlines through the outer executor
- Ported upstream `f30020ed5e1f` as an Anakot-native adaptation. Existing resolved `mcp_servers.<name>.timeout` values now travel through `ToolEntry.execution_timeout`.
- The batch planner treats a longer MCP budget as a sequential barrier (including `tool_call` bridge calls), while sequential execution extends only that call's generic deadline.
- Added `tests/agent/test_mcp_execution_deadline.py` with registry, admission, and registration invariants. Focused MCP/registry/dispatch tests passed; the unrelated `tests/tools/test_mcp_tool.py` collection error remains (`CreateMessageResultWithTools` missing from `tools.mcp_tool`).

### 2026-10-06 — Refresh + port: 19 high-value Hermes fixes (Oct 2-5 batch)
- Refreshed refs: `origin/main` = `9b6fc23ba` (2026-10-05), latest Hermes release.
  Divergence ~50 ahead / ~120 behind — architectural, not missing features.
- Pulled 1,728 new commits since Oct 2. After filtering noise (plugin-catalog 472,
  test-only 212, code-health 51, chore/fmt ~200), identified ~164 portworthy candidates.
- **19 fixes ported** across agent, gateway, discord, CLI, auxiliary, dashboard-auth,
  compaction, approval, and security. All committed in 6 batches with focused tests.
- Key adaptations (not cherry-picks):
  - `response_reused` wire contract: Anakot's TUI gateway has its own payload model,
    so the field was added to `MessageCompletePayload` + `prompt_turn.py` rather than
    Hermes' `contracts/events.py`.
  - Auxiliary/Codex: extracted `agent/auxiliary_codex_response.py` as a sibling module
    (Anakot has no `hermes_cli` package); `recover_leaked_tool_call=False` for aux.
  - Discord allowlist: security fix — match only `member.name`, not display_name/global_name.
  - Dashboard auth body cap: new `AuthBodyLimitMiddleware` (64KB) registered innermost.
  - Native compaction: `_input_text_parts_cost` + `_truncate_input_text_parts` for
    typed `input_text` parts (bisect head-truncation preserving metadata).
- Tests: 6 focused test files added/extended, all green. `scripts/run_tests.sh` used
  throughout (CI parity: temp ANAKOT_HOME, TZ=UTC, LANG=C.UTF-8).
- Skipped: plugin-catalog (472), code-health (51), test-only (212), chore/fmt (~200),
  Hermes-specific infrastructure (pm/, resolveInstallationLauncher, bot-mode, relay).

### 2026-10-02 — Refresh + port: desktop pre-update backup opt-out
- Refreshed refs: `origin/main` = `4b0fbf06cd`, `upstream/main` = `4097709b0c` (2026-10-02), latest
  Hermes release `v2026.9.24`. Divergence 53 ahead / 69 behind — architectural, not missing features.
- Cleared the last two `PENDING` rows (4de06d1d, 37fd6440). Tracker is now at 0 `PENDING`.
- Adaptation, not a cherry-pick: upstream's fix hangs off `resolveHermesBackend(['config','get',…])`
  in a `main.ts` whose preflight is inlined per update lane. Anakot's preflight is already a shared
  `electron/updater/state-db-preflight.ts` called from both `applyUpdates` (Windows/Tauri) and
  `applyUpdatesPosixHandoff`, so the gate went inside that one seam instead of being duplicated.
- **Divergence that mattered (would have shipped a cross-profile read):** upstream's probe is
  `python -m anakot_cli.main --profile X config get …`. Under `-m`, `anakot_cli/main.py` executes
  TWICE — once as `anakot_cli.main` during the package import, then again as `__main__` via runpy —
  and the first pass strips `--profile` from `sys.argv`. The second pass then falls through to the
  root's sticky `active_profile`, so a root-home probe read a NAMED profile's `config.yaml`.
  Proven with an import-hook probe printing argv at each execution. Fixed by importing and calling
  `main()` once (`-c "import sys;from anakot_cli.main import main;sys.exit(main())"`), which is also
  how the repo's own `ANAKOT_PYTHON` guidance invokes it. Covered by a test that writes
  `active_profile: b` in the root home and asserts the root's own value wins in an A → B → A sweep.
- Safety posture preserved: a probe that cannot answer (no CLI, bad JSON, nonzero exit, 15s timeout)
  still takes the snapshot, so the failure mode is "extra backup", never "no recovery file".
- Tests: 22 in `electron/updater/state-db-preflight.test.ts` — effective-value matrix (off/false/null/
  aliases/quick/full/true/0/unknown/unset), managed-scope override both directions, `${ENV}` expansion,
  two homes A → B → A under one process, and 4 fail-open fixtures. All green; 58 passed / 1 skipped
  across the neighbouring update suites. `tsc -p tsconfig.electron.json`, eslint, prettier, and the
  Electron bundle all clean.
- CI: `js-tests.yml` had no Python runtime, so the new integration cases could not have run there.
  Added a pinned `setup-uv` + `uv sync --locked --python 3.11 --no-dev` step and pointed the suite at
  that interpreter via the existing `ANAKOT_PYTHON` hook.


### 2026-09-23 — Refresh: pull latest 100 Hermes commits
- Added 30 new commits (1c953851 → 04fe735c) from 2026-09-22
- Categories: urllib CA-bundle perf, memory dedupe fixes, gateway async safety, bot-mode perf, relay/discord fixes, desktop plugin settings UI
- All new commits marked PENDING

### 2026-09-22 — Initial setup
- Created this tracking file
- Pulled latest 100 Hermes commits
- All commits marked PENDING

### 2026-10-17 — Upstream head refresh (`605e4045934`)
- Refreshed `upstream/main` from the official Hermes remote. The head is `605e4045934`; the post-`6206f893` window is dominated by platform-registry/plugin loading, approval-surface, MCP lifecycle, spillover retention, and session/update fixes, plus catalog/docs noise.
- Audited the directly comparable candidates: `1f1bb5cd` is ported below; `309fddab` and `6dcf6358` remain a linked spillover ownership-fence cluster; `b26bb96d`, `4e0806d5`, and `073a3af5` are covered by Anakot-native behavior or intentional architecture differences and are recorded as `CUSTOM`.

### 2026-10-17 — Ported expired persisted-result diagnostics (`1f1bb5cdb5`)
- Adapted `tools/tool_result_storage.py::expired_archive_fields` and the `read_file` boundary so missing files under the profile's `cache/spillover` or remote result root are marked `expired` with a warning not to blindly rerun the producing call.
- Enriched both the first miss and the task-local negative-cache retry; ordinary missing paths remain unchanged.
- Verification: 40 tool-result-storage tests, the focused file-tools integration test, and Python compilation passed. The full file-tools neighbor still has six pre-existing Windows-path/macOS-carveout failures unrelated to this change.

### 2026-10-17 — Continued connector parity (`70f5dc5f`)
- Verified the existing backend half already includes the portal catalog/accounts/policy RPCs and the profile/member-keyed 24-hour ETag tool-list cache; the missing `connectors.tools` claim in the older row was stale.
- Added a native profile-scoped Capabilities → Connectors tab. It reads catalog/state/accounts/policy, opens account-owned connect/reconnect operations, polls settlement, disconnects accounts with confirmation, refreshes tool lists, and writes connector/tool policy through the existing RPC contracts.
- Added pure derivation invariants and a component wiring test; corrected the renderer's stale connection-state/sequence contract fixtures so the desktop TypeScript project is green.
- Verification: 29 focused Vitest tests passed, desktop typecheck (renderer/Electron/E2E) passed, ESLint passed, production desktop build passed, and 47 connector lifecycle/RPC tests passed across the managed, MCP, operation-RPC, and operation-E2E suites. The E2E fixtures now follow the gateway's asynchronous long-handler responses and account-scoped watcher contract.
- Remaining for this upstream cluster: bundled-MCP `connector:` dedup/local-server merge, the full upstream account/dialog polish, and Ink `connectionSetupOverlay`.

### 2026-10-18 — Repaired connector authorization runtime (`70f5dc5f`)
- Restored the ported `tools/connectors/account.py` operation bridge that the Desktop account-owned `connectors.connect` RPC imports; without it, every authorization attempt collapsed to the generic `CONNECTOR_REQUEST_FAILED` response.
- Added an account-owned RPC regression covering operation start, gateway mint, watcher settlement, and live-operation cleanup. The live managed install was updated and the repaired RPC returned 53 connector rows before this authorization fix.

### 2026-10-17 — Current-head refresh and reliability ports (`18c525b669b`)
- Refreshed the official `upstream/main`; the head advanced from `605e4045934` to `18c525b669b`. The new window is dominated by Windows ACL/update work, session-store repair, clarify lifecycle, skills watching, gateway secret binding, and catalog churn.
- Closed the linked spillover cluster: structured/NUL-prefixed and Windows pointers now share the `instr()` reference filter, and `state_meta` retirement candidates are captured before message-bearing deletes and collected after commit. The retention test also now ages its default-window fixture beyond the configured 90-day session policy.
- Ported the browser redaction depth cluster (`440c9b61df`, final cap `870633cba7`): snapshot and CDP walkers stop at 320 JSON levels with an explicit marker, preserving Chrome-depth DOM trees while refusing hostile 2,000-level page data.
- Ported the terminal trailing-amp cluster (`d5c74fc185`, `390b1e38d2e`, `c8be4526d6`): the final command is passed through approval and tracked background execution, shell substitutions/carriers/wrappers remain refused, local approval identity cannot change, explicit `background=true` calls are normalized too, and escaped spaces/ampersands remain safe data.
- Verification: spillover/tool-result focused suites — 43 passed; browser redaction, CDP, snapshot, and browser type-redaction neighbors — 43 passed; agent redaction suite — 212 passed; the targeted terminal guard/pipeline suites passed, including new coverage for help/version commands, shell carriers, explicit background calls, command substitutions, escaped ampersands, and prepared approvals. The final scoped review found no remaining findings. The existing Windows foreground-timeout marker test still fails on the base checkout because the local shell shim does not create the Windows temp-path marker; compound-background bash syntax tests have the same host-shim failure. One pre-execution-deadline file was flaky once and passed on the runner retry, so it remains a known timing flake rather than a port regression.
|
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
