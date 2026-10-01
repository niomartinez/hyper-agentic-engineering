---
name: hae-engineering
description: Plan, debug, implement and review coding work with HAE's scoped engineering practices, and select relevant installed skills for specialized tasks.
---

# Engineering workflow

Read [Engineering foundation](references/engineering.md) once for a coding task; if the matched HAE practice was already loaded, use that context. Current user and repository rules win. Keep ownership, client practices, account identity and historical evidence distinct.

For a specialized task, read only its section in [Task workflows](references/workflows.md). Use the host's installed skill inventory first. If discovery is unclear, run the configured HAE command with `skills route --task <task>`; the bundled `scripts/hae.pyz` also supports it without a vault. Tasks include bug, tests, architecture, review, merge, research, prototype, agent-docs, ui-new, ui-existing, obsidian, docx, pdf, sheets and slides.

The router returns at most one primary installed skill with an absolute entry path. Read that file and resolve its references from its actual location. It scans standard personal skill folders and a bounded local library; host-managed plugins may need the host's own discovery. If absent, use the included task workflow and identify the missing optional integration. Do not claim it is installed or automatically download a dependency.

Use Taste for new UI and Impeccable for existing UI; never load both for the same job. Full community Karpathy guidelines and Graphify require an explicit user request; only then pass `--explicit` for karpathy or graph tasks. Caveman/Ponytail are opt-in choices in this shared product; preserve existing style, or use HAE's lean preset when selected. Do not impose the author's personal model, account or publishing settings.

At meaningful milestones or a cutoff, use hae-memory if configured; otherwise preserve the user's existing memory authority and write the project's handoff. Ordinary replies need no memory job. Do not delegate a second model for approved memory prose.
