---
name: hae-setup
description: Install, inspect, upgrade or remove Hyper Agentic Engineering while preserving existing agent instructions, hooks and memories.
---

# Set up HAE

Perform setup for the user; do not hand them a list of shell commands to carry out. In a generated skill or plugin, use the bundled `scripts/hae.pyz` with Python 3.11+. From the reviewed source repository, follow the root `SETUP.md` and use `run.py`. Read the selected runtime’s `--help`; never assume a sibling repository checkout exists. It contains the same deterministic installer as the CLI. If Python is unavailable, report the prerequisite instead of claiming setup succeeded. Use `python3` on macOS/Linux and an available Python 3.11+ executable or `py -3` on Windows. The CLI prints commands for the current platform; PowerShell paths use its call operator and literal quoting. Never change execution policy or bypass native hook trust.

Keep engineering as the default; its generalized practices and task-routing skill are included. Offer general-work mode when requested; it uses project folders and briefs without coding requirements. Preserve current styles; the lean preset, capture hooks, Jev and backups are opt-in.

Resolve the intended project folder, verified scope, memory folder and target agents from the request and existing setup. Run `plan` with those selections. Inspect its conflicts and exact changes; clarify unresolved ownership or competing memory authority. Show the concrete plan before applying, unless the user has already authorized these changes. Never rewrite host configuration yourself or silently replace native memory.

Run `apply <plan-id>`, then `doctor`. A configured hook is not proof it ran: Codex trust is reviewed through the native `/hooks` interface. Do not bypass it. Cowork requires a separately tested plugin/folder environment; a successful CLI run does not establish Cowork support.

Verify one approved save and recall in the selected project. For recovery, use `rollback`; for removal use `uninstall`. Both preserve notes and refuse edited owned fragments. Report actual results, unresolved prerequisites and the receipt. Do not install upstream skills or enable a provider merely because the catalog lists them.
