# Anakot Agent ☤

> **Anakot is a fork of [Nous Research's Hermes Agent](https://github.com/NousResearch/hermes-agent).** Enormous credit to the Nous Research team — the agent, the self-improving learning loop, the tool ecosystem, the gateway, and the desktop app are all their work. This project would not exist without it.
>
> This fork does what forks are for: **cut the weight, and add what upstream doesn't have.** Upstream is not deprecated and not abandoned — if you want the canonical project, use [hermes-agent](https://github.com/NousResearch/hermes-agent). If you want the leaner build with a free-model browser and a connectors layer, you're in the right place.

<p align="center">
  <a href="https://github.com/Chensihakniroth/anakot-agent-v1/releases">⬇ Releases</a> ·
  <a href="#quick-install">⬇ Install</a> ·
  <a href="#what-this-fork-adds">What this fork adds</a> ·
  <a href="https://github.com/Chensihakniroth/anakot-agent-v1/issues">Issues</a>
</p>
<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT License"></a>
  <a href="https://github.com/NousResearch/hermes-agent"><img src="https://img.shields.io/badge/fork%20of-hermes--agent-blueviolet?style=for-the-badge" alt="Fork of hermes-agent"></a>
  <a href="README.zh-CN.md"><img src="https://img.shields.io/badge/中文-red?style=for-the-badge" alt="中文"></a>
  <a href="README.ur-pk.md"><img src="https://img.shields.io/badge/اردو-green?style=for-the-badge" alt="اردو"></a>
  <a href="README.es.md"><img src="https://img.shields.io/badge/Español-orange?style=for-the-badge" alt="Español"></a>
</p>

---

## What this fork adds

Everything below is fork work. Everything else is upstream Hermes, credited as such.

| | |
|---|---|
| **Free Model Suite**<br>`plugins/free-model-suite` | Browse, probe, and apply free models from providers you've already configured. Test a candidate with a one-shot completion *before* you commit to it. Reads your existing model inventory — it owns no provider or model policy of its own. |
| **Connectors**<br>`tools/connectors/portal` | Connect an app without opening a chat session. Portal catalog, account management, policy checks, and a cached tool list. |
| **Disk Cleanup + Security Guidance** | Hardened ports of both plugins. |
| **Plugin-declared settings** | Plugins now render their own settings in the desktop Plugins tab, and each gets a **per-plugin load deadline** — one hung `register()` can no longer stall app startup. |
| **Aux-call hooks** | Plugins can fire `pre_auxiliary_call` / `post_auxiliary_call` around every auxiliary LLM call. |
| **Bloat removed** | 30 MB of duplicate 3 MB icon PNGs collapsed to real display sizes. Build logs, scratch notes, and generated `egg-info` are untracked. |
| **~20 perf & hardening fixes** | Gateway thread and rich-sent persists moved **off the event loop**, leaner structural summary input, context/TLS/ledger hardening, retention and temp-media cleanup, Tauri updater staging. |

> **Not in this fork:** the CLI/TUI skin work lives in separate Anakot trees, not here. Don't expect it from this repo.

---

## Quick Install

The installers in this repository install **Anakot** — they point at this fork, not upstream.

### Linux, macOS, WSL2, Termux

```bash
curl -fsSL https://raw.githubusercontent.com/Chensihakniroth/anakot-agent-v1/main/scripts/install.sh | bash
```

### Windows (native, PowerShell)

```powershell
iex (irm https://raw.githubusercontent.com/Chensihakniroth/anakot-agent-v1/main/scripts/install.ps1)
```

Native Windows is fully supported without WSL — CLI, gateway, TUI, and tools all work. Prefer WSL2? The Linux one-liner works there too. Native installs live under `%LOCALAPPDATA%\anakot`; WSL2 installs under `~/.anakot`.

The installer handles uv, Python 3.11, Node.js, ripgrep, ffmpeg, **and a portable Git Bash** (MinGit → `%LOCALAPPDATA%\anakot\git`, no admin, fully isolated). If you already have Git, it's detected and used instead.

Then:

```bash
source ~/.bashrc    # or: source ~/.zshrc
anakot              # start chatting
```

<details>
<summary><b>Android / Termux</b></summary>

Anakot installs a curated `.[termux]` extra, because the full `.[all]` extra pulls Android-incompatible voice dependencies.
</details>

<details>
<summary><b>Windows Defender flags <code>uv.exe</code> as malware</b></summary>

A **false positive**. `uv.exe` is Astral's Rust-based Python package manager, which Anakot bundles to manage its Python environment. ML-based engines commonly flag unsigned Rust binaries that download packages.

Verify your copy is authentic:

```powershell
winget install --id GitHub.cli
gh auth login

$uv = "$env:LOCALAPPDATA\anakot\bin\uv.exe"
$ver = (& $uv --version).Split(' ')[1]
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest "https://github.com/astral-sh/uv/releases/download/$ver/uv-x86_64-pc-windows-msvc.zip" -OutFile "$env:TEMP\uv.zip" -UseBasicParsing
gh attestation verify "$env:TEMP\uv.zip" --repo astral-sh/uv
Expand-Archive "$env:TEMP\uv.zip" "$env:TEMP\uv_x" -Force
(Get-FileHash "$env:TEMP\uv_x\uv.exe").Hash -eq (Get-FileHash $uv).Hash
```

Attestation says "Verification succeeded" **and** the last line prints `True` → you're good.

Whitelist the **folder**, not the file hash — Anakot updates `uv` and the hash changes every version:

- **Windows Defender:** `Add-MpPreference -ExclusionPath "$env:LOCALAPPDATA\anakot\bin"` (as Admin)
- **Bitdefender:** Protection → Antivirus → Settings → Manage Exceptions

Upstream reports: [astral-sh/uv#13553](https://github.com/astral-sh/uv/issues/13553) · [#15011](https://github.com/astral-sh/uv/issues/15011) · [#10079](https://github.com/astral-sh/uv/issues/10079)
</details>

---

## Getting Started

```bash
anakot              # Interactive CLI — start a conversation
anakot model        # Choose your LLM provider and model
anakot tools        # Configure which tools are enabled
anakot config set   # Set individual config values
anakot gateway      # Start the messaging gateway (Telegram, Discord, etc.)
anakot setup        # Full setup wizard
anakot claw migrate # Migrate from OpenClaw
anakot update       # Update to the latest version
anakot doctor       # Diagnose any issues
```

### Use any model you want

Nous Portal, OpenRouter, OpenAI, your own endpoint, and [many others](https://hermes-agent.nousresearch.com/docs/integrations/providers). Switch with `anakot model` — no code changes, no lock-in.

**Want free models?** That's what the [Free Model Suite](#what-this-fork-adds) is for — browse what's actually available on the providers you've configured, probe it, then apply it.

### Skip the API-key collection

If you'd rather not collect five separate keys for the model, web search, image generation, TTS, and a cloud browser, **[Nous Portal](https://portal.nousresearch.com)** covers all of them under one subscription:

- **300+ models** — pick any with `/model <name>`
- **Tool Gateway** — web search (Firecrawl), image generation (FAL), TTS (OpenAI), cloud browser (Browser Use), all through your sub

```bash
anakot setup --portal
```

Logs you in via OAuth, sets Nous as your provider, and enables the Tool Gateway. Check wiring anytime with `anakot portal info`. You can still bring your own per-tool keys — it's per-backend, not all-or-nothing.

---

## What you get

| | |
|---|---|
| **A real terminal interface** | Full TUI with multiline editing, slash-command autocomplete, conversation history, interrupt-and-redirect, and streaming tool output. |
| **Lives where you do** | Telegram, Discord, Slack, WhatsApp, Signal, and CLI — from a single gateway process. Voice memo transcription and cross-platform continuity. |
| **A closed learning loop** | Agent-curated memory with periodic nudges. Autonomous skill creation after complex tasks, and skills that self-improve during use. FTS5 session search with LLM summarization for cross-session recall, plus [Honcho](https://github.com/plastic-labs/honcho) dialectic user modeling. Compatible with the [agentskills.io](https://agentskills.io) open standard. |
| **Scheduled automations** | Built-in cron scheduler with delivery to any platform. Daily reports, nightly backups, weekly audits — natural language, unattended. |
| **Delegates and parallelizes** | Spawn isolated subagents for parallel workstreams. Write Python scripts that call tools over RPC, collapsing multi-step pipelines into zero-context-cost turns. |
| **Runs anywhere** | Seven terminal backends — local, Docker, SSH, Singularity, Modal, Daytona, Vercel Sandbox. Modal and Daytona offer serverless persistence, so the environment hibernates when idle. Run it on a $5 VPS or a GPU cluster. |
| **Research-ready** | Batch trajectory generation and trajectory compression for training next-generation tool-calling models. |

---

## CLI vs Messaging

Two entry points: the terminal UI with `anakot`, or the gateway talking to you from Telegram, Discord, Slack, WhatsApp, Signal, or Email. Most slash commands are shared.

| Action | CLI | Messaging |
|---|---|---|
| Start chatting | `anakot` | `anakot gateway setup` + `anakot gateway start` |
| Fresh conversation | `/new` or `/reset` | `/new` or `/reset` |
| Change model | `/model [provider:model]` | `/model [provider:model]` |
| Set a personality | `/personality [name]` | `/personality [name]` |
| Retry / undo last turn | `/retry`, `/undo` | `/retry`, `/undo` |
| Compress / usage | `/compress`, `/usage`, `/insights [--days N]` | `/compress`, `/usage`, `/insights [days]` |
| Browse skills | `/skills` or `/<skill-name>` | `/<skill-name>` |
| Interrupt work | `Ctrl+C` or a new message | `/stop` or a new message |
| Platform status | `/platforms` | `/status`, `/sethome` |

---

## Migrating from OpenClaw

Anakot imports your settings, memories, skills, and API keys automatically. The setup wizard detects `~/.openclaw` and offers migration before configuration begins.

```bash
anakot claw migrate              # Interactive migration (full preset)
anakot claw migrate --dry-run    # Preview what would move
anakot claw migrate --preset user-data   # Migrate without secrets
anakot claw migrate --overwrite  # Overwrite existing conflicts
```

Imports SOUL.md, memories (MEMORY.md / USER.md), user-created skills → `~/.anakot/skills/openclaw-imports/`, command allowlist, messaging settings, allowlisted API keys (Telegram, OpenRouter, OpenAI, Anthropic, ElevenLabs), TTS assets, and AGENTS.md workspace instructions.

---

## Documentation

Upstream's docs remain the reference for the bulk of the agent, and they're good: **[hermes-agent.nousresearch.com/docs](https://hermes-agent.nousresearch.com/docs/)**.

The full documentation source — **461 pages** — also ships in this repo under [`website/docs`](website/docs), so the fork can self-host docs that match its own code. Key sections:

| Section | Covers |
|---|---|
| [Quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart) | Install → setup → first conversation |
| [CLI Usage](https://hermes-agent.nousresearch.com/docs/user-guide/cli) | Commands, keybindings, personalities, sessions |
| [Configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration) | Config file, providers, models, all options |
| [Messaging Gateway](https://hermes-agent.nousresearch.com/docs/user-guide/messaging) | Telegram, Discord, Slack, WhatsApp, Signal, Home Assistant |
| [Security](https://hermes-agent.nousresearch.com/docs/user-guide/security) | Command approval, DM pairing, container isolation |
| [Tools & Toolsets](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools) | 40+ tools, toolset system, terminal backends |
| [Skills System](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills) | Procedural memory, Skills Hub, creating skills |
| [Memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory) | Persistent memory, user profiles, best practices |
| [MCP Integration](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp) | Connect any MCP server |
| [Cron Scheduling](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron) | Scheduled tasks with platform delivery |
| [Architecture](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture) | Project structure, agent loop, key classes |
| [Contributing](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing) | Development setup, PR process, code style |
| [Environment Variables](https://hermes-agent.nousresearch.com/docs/reference/environment-variables) | Complete env var reference |

---

## Contributing

Use the standard installer first, then work from the git checkout it creates at `$ANAKOT_HOME/anakot-agent` (usually `~/.anakot/anakot-agent`). That matches the layout `anakot update`, the managed venv, lazy dependencies, gateway, and docs tooling all expect.

```bash
curl -fsSL https://raw.githubusercontent.com/Chensihakniroth/anakot-agent-v1/main/scripts/install.sh | bash
cd "${ANAKOT_HOME:-$HOME/.anakot}/anakot-agent"
uv pip install -e ".[all,dev]"
scripts/run_tests.sh
```

**Manual clone fallback** (for throwaway clones or CI where you deliberately don't want the managed layout) — create the venv *outside* the source tree, since a venv inside the directory the agent operates from can be wiped by a relative-path command the agent runs against its own checkout:

```bash
git clone https://github.com/Chensihakniroth/anakot-agent-v1.git
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv ~/.anakot/venvs/anakot-dev --python 3.11
source ~/.anakot/venvs/anakot-dev/bin/activate
uv pip install -e ".[all,dev]"
scripts/run_tests.sh
```

**Syncing from upstream:** the porting tracker that records what's synced, what's skipped, and why is maintained outside the public tree. Open an issue if you need a specific upstream change ported.

---

## Community

- 🐛 [Issues](https://github.com/Chensihakniroth/anakot-agent-v1/issues) — fork-specific bugs and features
- 💬 [Nous Research Discord](https://discord.gg/NousResearch) — upstream community, where the core agent is discussed
- 📚 [Skills Hub](https://agentskills.io)
- 🔌 [computer-use-linux](https://github.com/avifenesh/computer-use-linux) — Linux desktop-control MCP server with AT-SPI accessibility trees, Wayland/X11 input, and compositor window targeting
- 🔌 [AnakotClaw](https://github.com/AaronWong1999/anakotclaw) — community WeChat bridge for running Anakot and OpenClaw on one account

---

## License

MIT — see [LICENSE](LICENSE).

Originally built by [Nous Research](https://nousresearch.com). This fork is maintained independently under the same MIT terms.
