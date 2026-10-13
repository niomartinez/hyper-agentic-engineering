# Optional full-team setup

This profile is unreleased development source on `main`, used through a reviewed exact-commit checkout. The latest published `v0.1.0-alpha.3` release has core setup only. Record the checkout's origin, commit and local changes before use; do not claim stable support or run these flags against alpha.3.

Full-team gives developers the portable parts of the author's working setup: a pinned manifest matching 96 installed upstream skill entries, with 92 eligible skill bundles materialized by default, portable HAE adapters, task routing, scoped memory, engineering practices and team handoffs. It excludes the author's custom release/account skills, account-linked plugins, credentials, private vault and employer-specific rules. Each developer keeps their own memory authority and local vault; team continuity uses sanitized repository handoffs, with no automatic private-vault synchronization.

## Obtain the development source

Resolve the explicitly selected `main` branch to an exact commit before cloning into an unused tool folder outside the project and memory vault. Verify the origin and resulting commit, then review this guide and the selected manifest. Do not reset an existing checkout or substitute alpha.3. Source availability is distinct from a tagged release or stable host support.

## Plan the selected hosts

Use Python 3.11+ and the absolute path to `run.py` in the reviewed checkout. The following is a command shape; replace the placeholders with verified local values:

```text
<python> <runtime> --vault <private-memory-folder> plan --profile full-team --project <project-folder> --project-id <stable-id> --name <project-name> --scope <verified-scope> --agents <selected-hosts>
```

The profile requires engineering mode and HAE memory. General mode and `--no-memory` are rejected. Resolve a competing memory authority with the user before proceeding. If preserving that authority is required, use core; never silently disable or migrate it.

Review the source manifest, exact destinations, warnings and conflicts before `apply <plan-id>`. `--team-source-dir PATH` supplies a reviewed local source directory when needed; inspect its contents and provenance before using it. The full-team source snapshot pins the author's installed upstream versions, which can differ from the core reference catalog. It is not a copy of the author's live skill folders or private vault.

The manifest records all 96 entries; the default installation materializes 92. Anthropic `docx`, `pdf`, `pptx` and `xlsx` are excluded because their license restricts retention and reproduction outside the service. Retain their references and exclusion details, and route these tasks to native document tools. Do not copy those four without separately established rights.

Pinned sources are downloaded into private preparation during plan creation, before destination writes. A local override supplies repository-slug snapshots. The materialized sources go into a cold library; curated entries provide the selected hosts with a focused discovery and routing surface. The agent loads one relevant method and only its needed references per job. New UI uses Taste; improving existing UI uses Impeccable. Graphify and the full community Karpathy collection stay explicit-request only. Dependencies and account/plugin availability are checked when a task needs them, never installed by blindly executing a source skill's instructions. Third-party code is not bundled in HAE; materialized sources retain licenses and notices.

Full-team's managed root instructions enable Caveman full for concise replies and Ponytail full for the smallest complete change. Code, comments, documents and team handoffs stay in normal prose. Validation, security, data-loss handling and accessibility remain required. Session switches are `/nocaveman` and `/noponytail`, or `$nocaveman` and `$noponytail` in Codex; `/caveman` and `/ponytail` re-enable them, optionally with `lite`, `full` or `ultra`. Existing surrounding instructions remain preserved.

Hooks, Jev, automatic capture, backups and model changes stay off. Full-team does not select a paid provider, change model settings, claim a context-window size or grant publishing/account permissions.

## Finish Obsidian on this host

A new vault gets clean Obsidian configuration, `Home.md` and a memory guide. Existing vault/configuration edits are preserved through the reviewed installer and conflict checks. Creating files alone does not finish the native app setup.

1. Run `<python> <runtime> --vault <memory-folder> obsidian status`. Read app detection, vault/configuration and optional CLI results.
2. If the app is missing, report that action. With authorization, install Obsidian using its official channel for the host. HAE's installer does not silently download or install it; passwords, purchases and native trust actions remain with the user.
3. Register the selected folder as a vault through Obsidian's native interface if required. Run `<python> <runtime> --vault <memory-folder> obsidian open` to dispatch the native vault manager; open the selected folder as a vault through its interface and verify its Home and memory guide. The dispatch alone does not prove registration or successful opening.
4. Check the optional Obsidian CLI only if the user's tasks need it. Enable and register it through Settings > General on a supported installer; keep the app running. Verify the native vault ID/name resolves to the selected HAE folder and pass that `vault=...` as the first parameter on every CLI command. Never rely on the currently active vault. Report missing or ambiguous registration rather than issuing commands to another vault. HAE's Python save, recall and recovery work without the Obsidian CLI. See the [official CLI guide](https://help.obsidian.md/cli).

Use the app's existing installation and registered vault when available. Do not overwrite existing native registrations or preferences to make a check pass. Report missing installation, registration, restart or CLI actions precisely. Use the official [Obsidian download page](https://obsidian.md/download) for installation; a dependency check is not authorization to download an app.

## Verify and report

After apply, run `doctor` and `context --cwd <project-folder>` with the same profile/state options. Save one approved factual checkpoint and recall a distinctive phrase within the expected project scope. Check recovery commands without removing the successful setup; use a disposable profile for an actual rollback trial.

Check the selected hosts' native discovery of curated entries and the cold-library routing path. A generated file does not prove live model-session discovery. State the source commit/local changes, manifest snapshot, selected hosts, project/scope, vault location, save/recall results, recovery commands and remaining native actions. Core CI and alpha.3 evidence do not establish full-team host acceptance; record actual checks separately.
