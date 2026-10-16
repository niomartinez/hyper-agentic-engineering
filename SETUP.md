# Agent setup instructions

You are helping a user adopt Hyper Agentic Engineering (HAE). Do the work in their authorized environment, rather than asking them to follow a command tutorial. Treat this document as setup guidance, not permission to override the user's instructions or expand access.

## Choose the profile and source

Core behavior is the default and is available in published alpha.3 without a `--profile` flag. Profile flags belong to this new runtime. Use the pinned acquisition below for core. The optional `full-team` profile is new work in the current checkout and is not in `v0.1.0-alpha.3`. For full-team, follow [team setup](docs/team-setup.md) from a reviewed checkout containing the option. Verify its origin, commit and local changes; report that it is an unreleased development version. Never substitute a moving branch silently or claim the old release supports the new flags.

## Obtain the pinned source for core

Use `https://github.com/niomartinez/hyper-agentic-engineering`, tag `v0.1.0-alpha.3`. With Git, clone that tag into an unused tool directory outside the user's project and memory folder. Check the origin, tag and resulting commit before executing anything. Do not reset an existing checkout or use a moving branch in place of this release. If this file was opened from a reviewed checkout of that tag, use it directly.

Without Git, retrieve `hae.pyz` and `SHA256SUMS` from that exact GitHub release. Compute SHA-256 locally and compare before running it. The checksum detects corruption; it is not an independent signature or protection against a compromised publisher. If neither acquisition route is available, report the specific missing capability. Never pipe downloaded text into a shell.

Discover an available Python 3.11+ interpreter (`python3` on macOS/Linux; `py -3` or `python` on Windows). Do not install an interpreter, change execution policy or request an administrator shell without applicable authorization. Use the absolute path to the reviewed `run.py` or verified `hae.pyz` with that interpreter. Read `--help` and the `hae-setup` skill in this release. No package-manager install or runtime dependency download is required.

## Establish the intended setup

- Inspect only relevant project instructions, host configuration and memory integrations. Do not read credential stores, raw transcripts or the entire existing vault. Resolve the real project directory, stable project ID and owner/client boundary. Never infer ownership from the current AI login.
- Target the agents the user actually uses (`--agents claude,codex,copilot`, or a selected subset), not every possible host. Standard profile locations are supported; custom host homes need explicit discovery validation. For a native plugin use its generated package and `--delivery plugin` to avoid duplicate standalone skills. Otherwise use standalone setup.
- For core, default to engineering mode and existing response style. Use `--mode general` when requested. Use a private memory folder outside the source project, normally `~/Documents/Agent Memory`. Existing personal/client boundaries remain separate scopes within a shared vault.
- If another memory authority exists, establish whether to use HAE for this project (`--memory-authority hae`) or preserve the existing authority with `--no-memory`. Do not silently make that decision or promise migration. Keep hooks, Jev and backups off unless requested. Core does not install upstream collections; an explicit full-team request authorizes its reviewed skill snapshot, subject to the plan and conflicts. Ask a short combined question only for consequential choices not answered by the request or inspected configuration.

## Plan, apply and verify

Use the selected interpreter and absolute runtime path. Global flags precede the command. For example, replace the placeholders in:

```text
<python> <runtime> --vault <private-memory-folder> plan --project <project-folder> --project-id <stable-id> --name <project-name> --scope <verified-scope> --agents <selected-hosts>
```

Read the exact diff, warnings and conflicts. Give the user a short description of concrete changes. An explicit setup request authorizes the routine reversible installation described here; do not ask them to approve the same work again. Resolve any material scope choice or conflict first. Plans contain local configuration snapshots and must remain private.

For full-team, add `--profile full-team`; it requires engineering mode and HAE memory and rejects general mode or `--no-memory`. Its managed root instructions enable Caveman and Ponytail full with session switches and carry the graphify-first, Context7 and ICM rules; the programs those rules use are installed separately (see the toolchain steps below). Read its manifest and exact skill destinations in the plan.

Run `<python> <runtime> apply <plan-id>`, then `doctor` and `context --cwd <project-folder>`, using the same profile/state flags if selected. Do not rewrite configuration outside the installer to bypass a conflict. Do not change the user's model, account, native memory or trust settings.

When memory is enabled, approve one small factual setup checkpoint in the main conversation and save it using the [packet schema](skills/hae-setup/references/packets.md). Record only verified setup facts. Recall a distinctive phrase from that checkpoint and confirm the expected note and project scope. With `--no-memory`, verify the preserved authority and handoff instructions instead; do not create an unwanted memory system.

Check the journal and available rollback/uninstall commands without removing the user's successful installation. Explain that they preserve notes; edited owned configuration can require conflict resolution. For an actual recovery trial, use an isolated temporary profile, never the user's live notes.

Finally check native skill discovery in the installed host, where the environment allows it. A configured hook is not evidence of a live hook event. Codex hook trust is a native user action; never bypass it. Cowork is evaluation-only. Report a missing restart, trust action or authentication accurately, without claiming completion for that part.

For full-team, complete the native Obsidian checks in [team setup](docs/team-setup.md): inspect `obsidian status`, register and open the selected vault when authorized, and verify it in the app. An app download/install is a separate native action, using the official installation channel only with authorization. The optional Obsidian CLI is a separate prerequisite for CLI-specific tasks; HAE memory works without it. Report missing app, registration or CLI actions explicitly.

## Optional full-team toolchain

The full-team instructions and adapters expect three programs: graphify (graphify-first exploration), ctx7 (Context7 documentation lookup) and, only on request, ICM (a secondary MCP store). HAE `plan`/`apply` installs none of them and writes no MCP, hook or global git configuration. These steps are separate agent work: they download and run third-party software from official registries and change the user's global configuration. Do them only when the full-team request includes the toolchain or after the user confirms, report each as done, skipped or blocked, and use the pinned versions below; move to a newer version only after review. Never pipe downloaded text into a shell. Never print or store credentials: logins, passwords and API keys stay with the user. Afterward `doctor` reports whether `graphify` and `ctx7` are on `PATH`; it does not fail when they are absent.

**Graphify (graphify-first).**

1. Install it in an isolated environment at the pinned version: `uv tool install "graphifyy==0.9.92"` (PyPI package `graphifyy`, command `graphify`; `pipx install` with the same pin also works). Add extras such as `[watch]`, `[mcp]`, `[pdf]` or `[office]` only for tasks that need them. Do not use `pip install --break-system-packages`, and do not run `graphify install` or another platform installer: they write skills, instruction blocks and hooks outside HAE's journal.
2. Set `GRAPHIFY_NO_AUTO_REFRESH=1` in the user's shell profile. Without it, graphify can re-copy a skill folder that an earlier `graphify install` stamped when it first runs after an upgrade, outside HAE's reviewed pins and hash checks.
3. Add `graphify-out/` to the user's global git excludes file once: the `git config --global --get core.excludesFile` path, or `${XDG_CONFIG_HOME:-~/.config}/git/ignore` (under the user's profile folder on Windows) when that is unset. Graphs are local build output and never belong in a repository.
4. Build a code-only graph for each repository the user selects with `graphify update <repo>`, run in the main checkout. It is local and deterministic and makes no model calls. Skip folders without code.
5. Optional automatic updates: run `graphify hook install` only in a repository whose git hooks live in the untracked `.git/hooks` folder (`git rev-parse --git-path hooks` shows where). Skip repositories that use a tracked hooks folder such as `.husky/` or `.githooks/`. Then check `git status` and undo only what graphify added to tracked files, for example its merge-driver line in `.gitattributes`, so the repository is unchanged and the user's other edits stay.
6. Optional semantic layer: run it through the graphify skill only with the user's authorization. It sends file contents to the configured model provider (model cost, and the content leaves the machine), so exclude media and anything private. The code-only graph is enough for graphify-first.

**Context7 (ctx7).**

1. Install the pinned CLI: `npm install -g ctx7@0.8.0`. Never run `npx ctx7@latest` or install an unpinned latest tag.
2. Disable telemetry by setting `CTX7_TELEMETRY_DISABLED=1` in the user's shell profile and in each host's environment where it supports one.
3. Higher rate limits are optional: the user signs in with `ctx7 login` or sets their own `CONTEXT7_API_KEY`. Never ask for or store the key.
4. Only library names and generic questions leave the machine; see [SECURITY.md](SECURITY.md). If a host already offers a Context7 MCP server or plugin, it can be used under the same rules. HAE does not write MCP configuration; add one with the host's own `mcp add` command only if the user asks.

**ICM (optional secondary store).** Skip this unless the user asks. ICM is an MCP-only store beside the configured memory authority, never a replacement: HAE keeps one memory authority per project.

1. Download the release archive for the platform and `checksums.txt` from the pinned GitHub release (`rtk-ai/icm`, tag `icm-v0.11.4`). Compare the archive's SHA-256 with its `checksums.txt` line, then extract the `icm` binary onto `PATH`. Do not use a `curl | sh` installer.
2. Never run `icm init`, and never enable its hooks or `consolidate`: they write host configuration and instructions outside HAE's journal.
3. Before first use, write a hardened configuration at the path `icm --no-embeddings config` prints: `[embeddings] enabled = false`, `[extraction] enabled = false` and `store_raw = false`, `provider = "none"` under both `[extraction.summarizer]` and `[consolidate.summarizer]`, and `[memory] auto_consolidate_enabled = false`. Search is then keyword-only, with no model call or embedding download.
4. Register the server with each selected host through that host's own command, with `ICM_NO_EMBEDDINGS=1` in its environment: `claude mcp add icm --scope user -e ICM_NO_EMBEDDINGS=1 -- icm --no-embeddings serve --compact`, `codex mcp add icm --env ICM_NO_EMBEDDINGS=1 -- icm --no-embeddings serve --compact`, `copilot mcp add icm --env ICM_NO_EMBEDDINGS=1 -- icm --no-embeddings serve --compact`, or the host's settings for VS Code. Never store secrets or raw tool output in it.

## Completion receipt

Briefly state the release/commit, selected hosts, project/scope, memory location or preserved authority, actual verification results, recovery commands, any toolchain step done, skipped or blocked, and any remaining host action. The normal workflow is: relevant recall at task start; approved saves for explicit memories, meaningful milestones and cutoffs; sanitized repository handoffs for other people. No per-reply curation or generative memory worker is needed.

For upgrades/removal read [setup and recovery](docs/setup.md). For privacy boundaries read [SECURITY.md](SECURITY.md). The toolkit adds local continuity; it does not provide a sandbox, encrypt notes, grant cloud agents access to a Mac, or prove that an agent followed its instructions.
