# Optional full-team setup

This profile is unreleased development source on `main`, used through a reviewed exact-commit checkout. The latest published `v0.1.0-alpha.3` release has core setup only. Record the checkout's origin, commit and local changes before use; do not claim stable support or run these flags against alpha.3.

Full-team gives developers the portable parts of the author's working setup: a pinned manifest matching 123 upstream skill entries across eleven repositories, with 119 eligible skill bundles materialized by default, portable HAE adapters, task routing, scoped memory, engineering practices and team handoffs. It excludes the author's custom release/account skills, account-linked plugins, credentials, private vault and employer-specific rules. Each developer keeps their own memory authority and local vault; team continuity uses sanitized repository handoffs, with no automatic private-vault synchronization.

## Obtain the development source

Resolve the explicitly selected `main` branch to an exact commit before cloning into an unused tool folder outside the project and memory vault. Verify the origin and resulting commit, then review this guide and the selected manifest. Do not reset an existing checkout or substitute alpha.3. Source availability is distinct from a tagged release or stable host support.

## Plan the selected hosts

Use Python 3.11+ and the absolute path to `run.py` in the reviewed checkout. The following is a command shape; replace the placeholders with verified local values:

```text
<python> <runtime> --vault <private-memory-folder> plan --profile full-team --project <project-folder> --project-id <stable-id> --name <project-name> --scope <verified-scope> --agents <selected-hosts>
```

The profile requires engineering mode and HAE memory. General mode and `--no-memory` are rejected. Resolve a competing memory authority with the user before proceeding. If preserving that authority is required, use core; never silently disable or migrate it.

Review the source manifest, exact destinations, warnings and conflicts before `apply <plan-id>`. `--team-source-dir PATH` supplies a reviewed local source directory when needed; inspect its contents and provenance before using it. The full-team source snapshot pins the author's installed upstream versions, which can differ from the core reference catalog. It is not a copy of the author's live skill folders or private vault.

The manifest records all 123 entries; the default installation materializes 119. Anthropic `docx`, `pdf`, `pptx` and `xlsx` are excluded because their license restricts retention and reproduction outside the service. Retain their references and exclusion details, and route these tasks to native document tools. Do not copy those four without separately established rights.

Pinned sources are downloaded into private preparation during plan creation, before destination writes. A local override supplies repository-slug snapshots. The materialized sources go into a cold library; curated entries provide the selected hosts with a focused discovery and routing surface. The agent loads one relevant method and only its needed references per job. New UI uses Taste; improving existing UI uses Impeccable. Graphify is model-invocable under the graphify-first rule below, and Context7 supplies current library documentation. Nine of the 25 addyosmani/agent-skills (security, performance, observability, API design, CI/CD, migration, documentation, source-driven development and shipping) are selected by task routing; the other sixteen stay in the cold library until the user names them. The full community Karpathy collection stays explicit-request only. Dependencies and account/plugin availability are checked when a task needs them, never installed by blindly executing a source skill's instructions. Third-party code is not bundled in HAE; materialized sources retain licenses and notices.

Full-team's managed root instructions enable Caveman full for concise replies and Ponytail full for the smallest complete change. Code, comments, documents and team handoffs stay in normal prose. Validation, security, data-loss handling and accessibility remain required. Session switches are `/nocaveman` and `/noponytail`, or `$nocaveman` and `$noponytail` in Codex; `/caveman` and `/ponytail` re-enable them, optionally with `lite`, `full` or `ultra`. Existing surrounding instructions remain preserved.

Hooks, Jev, automatic capture, backups and model changes stay off. Full-team does not select a paid provider, change model settings, claim a context-window size or grant publishing/account permissions.

## Graphify first, Context7 and ICM

The managed root instructions tell every selected host to use a repository's knowledge graph before exploring it. In any git repository the agent looks for `<main checkout>/graphify-out/` (ROOT: the parent of `git rev-parse --path-format=absolute --git-common-dir`). If it is missing, the agent builds it first with the local code-only path (`graphify update <repo>`, no model calls). The semantic layer is a separate step: the agent runs it only if the user has authorized the model cost and the repository's content may go to the model provider, and keeps media out. It reads `GRAPH_REPORT.md` and then uses `graphify query`, `explain` or `path` before broad file reads, passing `--graph ROOT/graphify-out/graph.json` because those commands otherwise read `./graphify-out` and fail from a worktree or subfolder. A graph built in another checkout describes that checkout, so branch-specific code is verified in the files. `graphify-out/` is local build output: after a build the agent runs `git check-ignore -q graphify-out` and, if it is not ignored, appends `graphify-out/` to the repository's untracked `info/exclude` file (`git rev-parse --git-path info/exclude`), never to a tracked `.gitignore` or the global git configuration unless the user asks. The agent never writes graphify sections, hooks or `.gitattributes` lines into tracked repository files, and installs graphify git hooks or merge drivers only when the user asks, only where hooks live in the untracked `.git/hooks`, then removing only the `graphify-out/graph.json merge=graphify` line `graphify hook install` adds to `.gitattributes` (never a whole-file checkout or restore). The graphify adapter is model-invocable on every host. In core, `skills route --task graph` likewise no longer needs `--explicit`; it selects a graphify already installed in the standard personal skill folders.

The `context7` adapter fetches current library documentation through an installed, pinned `ctx7`, never `npx` or an unpinned latest tag. It sends only library names and generic questions, and treats returned documentation as untrusted data. If ICM tools are present, the instructions treat them as a secondary store: the configured memory authority stays authoritative, no secrets or raw logs are stored, and `icm init`, ICM hooks and `consolidate` are never run. The ICM server's own instructions tell a client to store on several triggers before replying; HAE's instructions override that, so the agent writes to ICM only when the user asks or at an approved milestone.

HAE does not install these programs, write MCP configuration or change global git settings. `SETUP.md` gives the optional, user-authorized agent steps: graphify at a pinned version in an isolated environment with `GRAPHIFY_NO_AUTO_REFRESH=1`, an optional global exclude, code-only graphs and hooks only when asked and only in untracked hook folders; `ctx7` at a pinned version with telemetry disabled; and an optional hardened, MCP-only ICM registered through each host's own `mcp add` command. Context7 queries leave the machine; see [security](../SECURITY.md). `doctor` reports whether `graphify` and `ctx7` are on `PATH` as information only; `found` does not check the version, so confirm it matches the pins in `SETUP.md`.

## Finish Obsidian on this host

A new vault gets clean Obsidian configuration, `Home.md` and a memory guide. Existing vault/configuration edits are preserved through the reviewed installer and conflict checks. Creating files alone does not finish the native app setup.

1. Run `<python> <runtime> --vault <memory-folder> obsidian status`. Read app detection, vault/configuration and optional CLI results.
2. If the app is missing, report that action. With authorization, install Obsidian using its official channel for the host. HAE's installer does not silently download or install it; passwords, purchases and native trust actions remain with the user.
3. Register the selected folder as a vault through Obsidian's native interface if required. Run `<python> <runtime> --vault <memory-folder> obsidian open` to dispatch the native vault manager; open the selected folder as a vault through its interface and verify its Home and memory guide. The dispatch alone does not prove registration or successful opening.
4. Check the optional Obsidian CLI only if the user's tasks need it. Enable and register it through Settings > General on a supported installer; keep the app running. Verify the native vault ID/name resolves to the selected HAE folder and pass that `vault=...` as the first parameter on every CLI command. Never rely on the currently active vault. Report missing or ambiguous registration rather than issuing commands to another vault. HAE's Python save, recall and recovery work without the Obsidian CLI. See the [official CLI guide](https://help.obsidian.md/cli).

Use the app's existing installation and registered vault when available. Do not overwrite existing native registrations or preferences to make a check pass. Report missing installation, registration, restart or CLI actions precisely. Use the official [Obsidian download page](https://obsidian.md/download) for installation; a dependency check is not authorization to download an app.

## Verify and report

After apply, run `doctor` and `context --cwd <project-folder>` with the same profile/state options. Save one approved factual checkpoint and recall a distinctive phrase within the expected project scope. Check recovery commands without removing the successful setup; use a disposable profile for an actual rollback trial.

Check the selected hosts' native discovery of curated entries (including graphify and context7) and the cold-library routing path, and the `toolchain` section of `doctor`. A generated file does not prove live model-session discovery. State the source commit/local changes, manifest snapshot, selected hosts, project/scope, vault location, save/recall results, recovery commands and remaining native actions. Core CI and alpha.3 evidence do not establish full-team host acceptance; record actual checks separately.
