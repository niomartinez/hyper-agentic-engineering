# Release status

## Now — 2026-10-01

Alpha 3 is the first public evaluation release of [Hyper Agentic Engineering](https://github.com/niomartinez/hyper-agentic-engineering). Engineering and coding are the default; general work is optional. The author's live agent configuration and existing memory system have not been migrated or replaced by HAE.

Users hand the [README prompt](README.md#give-this-to-your-agent) to their agent. The pinned [setup instructions](SETUP.md) cover inspection, scoped selection, preservation of existing memory, installation, verified save/recall and recovery. No provider, capture hook, model change or cloud backup is enabled by default.

The standard-library core provides reversible plan/apply/doctor/rollback/uninstall, scoped Markdown memory, approved local saves, bounded recall, handoffs and explicit text backups. Engineering includes generalized practices and installed-skill routing. Packages use explicit shipping lists and include checksum manifests. Original code is MIT; upstream skills are references only, not bundled code.

The 71-test suite passed in all six Windows/macOS/Linux Python 3.11/3.12 jobs in [public CI](https://github.com/niomartinez/hyper-agentic-engineering/actions/runs/36863706202), including release-boundary and complete packaged setup/recovery checks. See the [evidence record](docs/evidence/README.md) for actual runs and limits. Source, public history, commit metadata and nested artifacts are audited before publication. [Security boundaries](SECURITY.md) explain what those checks do and do not establish.

## Known alpha limitations

- Authenticated live host save/resume and native hook trust still need acceptance checks. Direct helper execution and native plugin discovery are narrower evidence. Cowork and WSL remain unverified environments.
- Latency varies by machine. The previous Windows Python 3.11 run missed the proposed 250 ms warm p95 target. No universal speed or percentage token-savings claim is made.
- Jev remains experimental, with no paid held-out evaluation or semantic-quality claim in this release.
- Independent developer adoption and non-engineer usability testing remain future work. Do not contact testers automatically.
- This release has no marketplace or package-manager listing. Use the pinned source or GitHub release assets.

## Log

- `eadecc5`: created the private alpha and original extracted core.
- `af22d0a`: made capture permission project-specific, extended worktree and plugin delivery checks, retained the measured Mac benchmark; 53 tests passed in Linux CI.
- Completed required Codex plugin interface metadata and recorded reproducible artifact hashes and verification limits.

- `71a9cba` / `3aa76bc` / `74f970f`: generalized engineering pack, task routing and native Windows implementation; corrected managed-block and recall handling for CRLF; six-job, 68-test matrix passed.
