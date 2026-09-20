# Anakot CLI Reference

Live sources when anything looks stale: `anakot --help`, `anakot <command> --help`,
https://anakot-agent.nousresearch.com/docs/reference/cli-commands

### Global Flags

```
anakot [flags] [command]        (no subcommand = interactive chat)

  --version, -V             Show version
  -z, --oneshot PROMPT      One-shot: print ONLY the final response (for scripts/pipes)
  -m MODEL  --provider P    Model/provider override for this invocation
  -t, --toolsets LIST       Comma-separated toolsets for this invocation
  --resume, -r SESSION      Resume session by ID or title
  --continue, -c [NAME]     Resume by name, or most recent session
  --worktree, -w            Isolated git worktree mode (parallel agents)
  --skills, -s SKILL        Preload skills (comma-separate or repeat)
  --profile, -p NAME        Use a named profile
  --yolo                    Skip dangerous command approval
  --tui / --cli             Force the Ink TUI / classic REPL
  --ignore-rules            Skip AGENTS.md/SOUL.md/memory/skill injection
  --safe-mode               Disable ALL customizations (troubleshooting)
  --pass-session-id         Include session ID in system prompt
```

### Chat

```
anakot chat [flags]
  -q, --query TEXT          Single query, non-interactive
  --image PATH              Attach a local image to a single query
  -Q, --quiet               Suppress banner, spinner, tool previews
  --checkpoints             Enable filesystem checkpoints (/rollback)
  --max-turns N             Cap tool-calling iterations
  --source TAG              Session source tag (default: cli)
```
(plus the global flags above)

### Configuration

```
anakot setup [section]      Wizard (model|tts|terminal|gateway|tools|agent)
anakot model                Interactive model/provider picker
anakot fallback [add|remove|list]  Fallback provider chain
anakot config [show|edit|get|set|unset|path|env-path|check|migrate]
anakot login / logout       OAuth sign-in / clear stored auth
anakot doctor [--fix]       Check dependencies and config
anakot status [--all]       Component status
```

### Tools & Skills

```
anakot tools [list|enable NAME|disable NAME]   Per-platform toolsets (curses UI with no args)

anakot skills list|browse|search QUERY|inspect ID
anakot skills install ID    Hub identifier OR a direct https://…/SKILL.md URL
anakot skills config        Enable/disable skills per platform
anakot skills check|update|uninstall|publish PATH
anakot skills tap add REPO  Add a GitHub repo as a skill source
anakot bundles              Skill bundles (one /<name> alias loads several skills)
```

### MCP Servers

```
anakot mcp add NAME (--url or --command) | remove | list | test NAME
anakot mcp catalog | install NAME     Curated catalog install
anakot mcp configure NAME             Toggle tool selection
anakot mcp serve                      Run Anakot as an MCP server
```
Details (transport, tool discovery, catalog): `references/native-mcp.md`.

### Gateway (Messaging Platforms)

```
anakot gateway run|install|start|stop|restart|status|setup
```

20+ platforms: Telegram, Discord, Slack, WhatsApp (Baileys + Business Cloud API), iMessage (Photon — `anakot photon setup`), Signal, Email, SMS, Matrix, Mattermost, Teams, LINE, SimpleX, ntfy, Google Chat, Home Assistant, DingTalk, Feishu, WeCom, Weixin, API Server, Webhooks. Open WebUI connects via the API Server adapter. Most adapters ship under `plugins/platforms/`.
Docs: https://anakot-agent.nousresearch.com/docs/user-guide/messaging/

### Sessions

```
anakot sessions list|browse|rename ID TITLE|delete ID|export OUT|prune|stats
```

### Cron / Webhooks

```
anakot cron list|create SCHED|edit ID|pause|resume|run ID|remove|status
    Schedules: '30m', 'every 2h', '0 9 * * *', ISO timestamp
anakot webhook subscribe NAME|list|remove NAME|test NAME
```
Webhook payloads/routes: `references/webhooks.md`.

### Profiles

```
anakot profile list|create NAME (--clone|--clone-all|--clone-from)|use|show|delete
anakot profile rename A B | alias NAME | export NAME | import FILE
anakot profile migrate-identity A B   Retry a completed rename's session/routing identity migration
```

### Credentials & Pools

```
anakot auth                 Interactive credential manager
anakot auth add [PROVIDER]  Add OAuth or API-key credential (nous, openai-codex, qwen-oauth, …)
anakot auth list|remove P IDX|reset PROVIDER|status
```
Multiple credentials per provider form a pool that rotates automatically and skips exhausted keys.

### Other

```
anakot desktop / gui        Native desktop app
anakot dashboard            Web admin panel + embedded chat (--stop / --status)
anakot proxy                OpenAI-compatible local proxy backed by an OAuth provider
anakot portal               Quick setup / sign in via Nous Portal
anakot kanban <verb>        Multi-agent work-queue board
anakot project              Named multi-folder workspaces
anakot skin list|use|set    Switch/tweak skins (see references/themes.md)
anakot pets <verb>          Pet mascots (see references/petdex.md)
anakot memory setup|status|off|reset   Memory provider
anakot secrets bitwarden|onepassword   External secret stores
anakot moa                  Mixture-of-Agents slots
anakot hooks / security / backup / import / checkpoints / console
anakot logs [-f] [errors]   View agent/error logs
anakot send                 One-off message through a gateway platform
anakot pairing / plugins / insights / journey / computer-use
anakot acp                  ACP server (IDE integration)
anakot completion bash|zsh|fish
anakot update / uninstall / claw migrate
```

Plugin- and provider-supplied subcommands (e.g. `anakot photon setup`) only appear once their plugin is installed/active.

### Where to Find Things

| Looking for... | Location |
|---|---|
| Config options | `anakot config edit` · [Configuration docs](https://anakot-agent.nousresearch.com/docs/user-guide/configuration) |
| Tools / toolsets | `anakot tools list` · [Tools reference](https://anakot-agent.nousresearch.com/docs/reference/tools-reference) |
| Skills catalog | `anakot skills browse` · [Skills catalog](https://anakot-agent.nousresearch.com/docs/reference/skills-catalog) |
| Provider setup | `anakot model` · [Providers guide](https://anakot-agent.nousresearch.com/docs/integrations/providers) |
| Env variables | `anakot config env-path` · [Env vars reference](https://anakot-agent.nousresearch.com/docs/reference/environment-variables) |
| Gateway logs | `~/.anakot/logs/gateway.log` (or `anakot logs`) |
| Sessions | `anakot sessions browse` (reads state.db) |
