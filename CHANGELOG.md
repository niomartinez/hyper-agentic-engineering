# Changelog

## 0.1.0a4.dev0 — Unreleased

Optional full-team setup installs a hash-pinned snapshot of eligible upstream skills, curated host adapters, clean Obsidian/HAE memory files and Caveman/Ponytail full defaults. Four restricted document bundles remain references for native-tool routing. Private preparation validates source archives without executing them; installation and recovery preserve existing files and launcher permissions. Added native Obsidian readiness/vault-manager helpers and explicit vault targeting. Core remains the default. Live host acceptance and publication are pending.

Graphify-first toolchain (development): graphify is model-invocable on every host, and the full-team instructions add a graphify-first rule: read or build the repository graph before broad file reads, keep `graphify-out/` out of version control (a repository-local `info/exclude` fallback after `git check-ignore`), run the semantic layer only with the user's authorization of model cost and content leaving the machine, install graphify hooks only when the user asks and never write graphify sections, hooks or `.gitattributes` lines into tracked files. The instructions also tell the agent to ignore ICM's own store-on-every-trigger server text. Pins move to graphify 0.9.92 and add addyosmani/agent-skills (25 library bundles, nine task-routed) and Context7 (`find-docs`, `context7-cli`), with a curated tool-neutral `context7` adapter that uses an installed, pinned `ctx7`. The manifest now lists 123 entries (119 eligible, 874 files). `doctor` reports whether `graphify` and `ctx7` are on `PATH`. SETUP.md adds optional, user-authorized agent steps for pinned graphify and ctx7 and a hardened MCP-only ICM store; HAE writes no MCP configuration. The archive reader no longer rejects an upstream symbolic link outside the pinned paths (`addyosmani/agent-skills` ships `.opencode/skills`, and the existing `mattpocock/skills` pin ships a root `AGENTS.md` link that the old reader also refused): links are never extracted, and a link at a selected path is still refused. Core routing also changes: the `graph` route no longer needs `--explicit` and selects an installed graphify, the router gains the full-team task names, and the core practice text no longer calls graph analysis an explicit opt-in. The export tool reads versioned snapshot folders.

Fixed: a full-team upgrade now refreshes the vault's copy of the team lock (`System/hae-team-skills.json`) when it still matches what HAE last wrote; previously it was written only on first install and kept the old pins. An edited copy is preserved with a warning. Rolling back the upgrade restores the previous copy byte for byte unless it was edited afterwards; uninstall retains the current copy.

## 0.1.0a3 — Public alpha

Agent-led setup entrypoint, explicit release packaging allowlists, nested artifact and history auditing, and documented security boundaries. Existing memory, configuration and provider defaults are unchanged.

## 0.1.0a2 — Private alpha

Generalized engineering foundation and task workflows now ship with the engineering setup, alongside bounded installed-skill routing. Added native Windows process locks, pipe deadlines, UTF-8/binary-safe storage, PowerShell setup commands, executable/argument hooks and junction checks. Upgrades preserve edited practices; uninstall handles LF/CRLF conversion while retaining unrelated bytes. CI now runs Python 3.11 and 3.12 on Windows, macOS and Linux. Live authenticated agent-session acceptance remains separate from core and shell testing.

## 0.1.0a1 — Unreleased

Initial private alpha: reversible setup, shared scoped Markdown memory, native hook configuration, approved checkpoints and handoffs, optional general-work mode, experimental bounded Jev, text-only backup and generated plugin/skill packages.
