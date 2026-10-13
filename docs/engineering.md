# Generalized engineering practices

Engineering setup includes the original HAE foundation, the `hae-engineering` skill and task-specific references. This is the generalized working method, without the author's accounts, employer exceptions, personal model choices or publishing permissions.

The foundation covers consequential assumptions, focused changes, reuse before abstraction, observable verification, concurrent contributors, relevant context, scoped client rules, explicit memory intake and resumable handoffs. The full text is in [the engineering preset](../presets/engineering.md). [Task workflows](../skills/hae-engineering/references/workflows.md) cover implementation, debugging, behavior tests, architecture, review/conflicts, research, UI and delivery.

The main conversation chooses a relevant method automatically from task intent. It uses host-native skill discovery first, or this bounded local helper when needed:

```sh
python3 -m hae skills route --task bug
python3 -m hae skills route --task ui-new
```

On Windows, use `py -3 -m hae` instead. No vault is required for routing. It searches standard personal skills plus a bounded `.agents/skill-library`, returns one primary entry path and loads no skill body. Read that entry and only the references relevant to the task. Host-managed plugins may need the host's own discovery.

| Task | Preferred installed integration |
| --- | --- |
| Bugs, tests, architecture, review, conflicts, research, prototypes, agent docs | Relevant Matt Pocock method |
| New UI | Taste |
| Existing UI improvement | Impeccable |
| Obsidian notes | Obsidian Markdown or CLI, according to the task |
| Documents, PDFs, spreadsheets, slides | Host-native tools, then a relevant installed document skill |
| Full community Karpathy guidelines or Graphify | Explicit user request only |

The included practices incorporate the general principles of understanding first, simplicity, focused edits and verified outcomes. In core, full third-party bundles remain optional: the catalog pins sources without installing or executing them. The new [full-team profile](team-setup.md) installs a separately pinned snapshot after plan review; it retains upstream licenses and never executes a skill’s dependency instructions during setup. The Karpathy-inspired collection is community-maintained, not an official Karpathy release. Missing integrations fall back to the included task workflow.

Core preserves existing style. Full-team enables Caveman full and Ponytail full through its managed root instructions, while preserving existing surrounding instructions. `/nocaveman` and `/noponytail` (Codex: `$nocaveman`, `$noponytail`) disable each for the session; `/caveman` and `/ponytail` re-enable them, optionally with `lite`, `full` or `ultra`. Code, comments, documents and team handoffs remain normal prose. `--style lean` selects concise replies and minimal complete changes. Caveman/Ponytail can be independently selected from the catalog. Code, documents and handoffs remain normal prose; required validation and accessibility are never dropped for brevity.

General-work setup uses its own practice and does not install the engineering skill through standalone setup. Plugins contain all capabilities, but coding workflows apply only to coding tasks. Memory can also be disabled while retaining engineering guidance and the user's existing memory authority.

On upgrade, installer-owned practice text can advance to the current version; edited or pre-existing practice notes are preserved. The current bundled reference remains available for comparison. Skills and runtime use the same checked reference files.
