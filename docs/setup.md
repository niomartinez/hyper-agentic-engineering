# Setup and recovery

Most users should give the [README prompt](../README.md#give-this-to-your-agent) to their agent. The agent follows [SETUP.md](../SETUP.md). This page is the technical reference, not a required user checklist.

Start from a reviewed, pinned checkout and Python 3.11+. Run `python3 -m hae --help`. Global `--home`, `--state-dir` and `--vault` options go before the subcommand. The default profile state is `~/.local/state/hyper-agentic-engineering`; the default new memory folder is `~/Documents/Agent Memory`.

On native Windows use `py -3 -m hae --help`; see [PowerShell setup](windows.md). The plan prints commands for the current platform and executable. The core does not require WSL, an administrator shell or execution-policy changes.

## Adopt an existing setup

Choose the real project folder, a stable project ID, verified owner/client scope, and a memory folder outside the source repository. Engineering is the default. Select agents with `--agents codex,claude,copilot`; use `--mode general` for non-coding project work.

Engineering includes the [generalized practices and routing skill](engineering.md). Existing style stays in place unless `--style lean` is selected. Installing HAE does not install the optional upstream collections.

`plan` reads the relevant files, detects known competing memory and produces a diff, warnings and a plan ID. It only writes a private plan and recovery snapshots. It does not disable other memory products or infer ownership from a login. The detection is bounded, not a universal inventory of every extension.

Inspect the plan. `apply PLAN_ID` checks every original hash before its first write and checks each destination again immediately before replacement. An identical apply or replan changes nothing. Preserve the state directory: it contains recovery snapshots. All agent configuration and snapshots remain local; they are not part of the source repository or text backup.

`doctor` reports configured tool versions, modified owned files and incomplete transactions. Hook trust and actual dispatch remain separate host checks. Restart or open a new session when the host requires it to discover skills.

## Optional hooks and plugins

Add `--hooks` to opt into local evidence capture for mapped projects. Claude and Codex use native Stop and PreCompact handlers. Copilot uses its own stop/session-end payload format. The helper emits neutral JSON, never requests another model turn, and never opens transcript paths. If the event lacks final text, the agent still needs an explicit checkpoint.

For Codex, inspect and trust the exact definitions through `/hooks`. HAE does not modify hook trust, `notify`, models or permission settings. A successful install only establishes configuration.

Build artifacts with `python3 tools/build_plugins.py`. Generated packages contain the complete runtime and focused skills. Install the appropriate package through the host's supported plugin interface. Plugin setup passes `--delivery plugin` so standalone skills are not also installed. The plugin itself has no lifecycle hooks: the reviewed installer owns the optional native hook entries once. This avoids registering both a plugin hook and a standalone hook for the same event.

For removal, run HAE `uninstall`, then remove the plugin in the host's own interface if applicable. HAE does not control the host's plugin cache or account-synced installation. Cowork remains an evaluation target until its sandbox, Python availability, folder access and save/resume path are tested live.

## Recovery

`rollback` reverses the latest active transaction. `rollback TRANSACTION_ID` requires that ID to be the latest; unwind newer transactions first. `uninstall` reverses all active integration transactions in reverse order.

Notes, project maps, provider configuration and vault ignore rules are retained. Matching installed files are restored from snapshots. Owned instruction blocks and hook entries can be removed while preserving unrelated later additions. If an owned fragment was edited, removal refuses that transaction before changing its files. Inspect the specific conflict, preserve the user's change and reconcile it deliberately; there is no force-delete flag.

LF/CRLF conversion alone is accepted for a managed instruction block, with surrounding bytes preserved. Actual content changes still require reconciliation. Untouched installer-owned practice notes can be updated during an upgrade; local practice edits are preserved with a warning and the new packaged reference remains available.

An interrupted apply leaves a small durable cursor. Recovery compares the pending write with its before/after hashes before deciding whether it ran. Multiple file writes are not one atomic transaction. Runtime locks coordinate HAE processes; compare-before-write checks reduce races with external editors but are not a filesystem authorization boundary against a hostile process running as the same user.

Uninstall does not erase recovery snapshots. Review and archive or remove the profile state separately only when rollback is no longer needed. This is intentionally distinct from deleting memory.

Automatic evidence is selected per project. Adding a new project does not inherit another project’s capture opt-in. Use `memory capture off --project PROJECT_ID` to stop capture for one project, or `memory capture on --project PROJECT_ID` to permit it; an installed and trusted host hook is still required.
