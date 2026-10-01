# Initial HAE alpha implementation

Historical checkpoint; continued in [Engineering and Windows — alpha 2](2026-10-01-engineering-and-windows.md).

## Task and scope

Implement the approved engineering-first toolkit with optional general-work setup. Keep the initial repository private. Preserve the author's live memory and agent configuration.

## Completed

The Python standard-library core supports reviewed setup plans, durable transaction cursors, owned instruction/hook fragments, recovery, uninstall with memory retention, scoped Markdown memory, idempotent approved packets, bounded recall, experimental opt-in Jev, handoffs and explicit text backups. Capture permission is scoped to each project. Generated skills/plugins contain the runtime. Upstream sources remain an optional pinned reference catalog; their code is not bundled.

Source is on private `niomartinez/hyper-agentic-engineering`, branch `main`. Core commit `af22d0a` passed 53 tests on both Linux Python 3.11 and 3.12. CI also built all packages, ran the source audit and measured 1,000-note recall. The subsequent package metadata and evidence changes are described in RELEASE-STATUS.md. No live personal profile was used for HAE installation.

## Evidence and limits

See `docs/evidence/README.md` and `RELEASE-STATUS.md` for actual results. All 53 tests also passed on macOS. Codex plugin/skill validation, native Claude manifest validation and Copilot plugin discovery passed. CLI authentication is unavailable for Claude; native Codex hook trust and actual model-session dispatch remain untested. Cowork has a generated evaluation package only. The first Mac recall run missed the speed target; a repeat after the test workload ended had warm p95 60.71 ms and cold recall 5.45 seconds. All measurements are retained. No paid model or Jev call was required.

## Resume

1. Read the latest release status and inspect the current commit before using these historical references.
2. Use a disposable profile for a live authenticated host save/resume test, review native hook trust, and uninstall afterward. Do not replace the author's existing memory system.
3. Investigate cold indexing and load sensitivity before making broad performance claims. Keep earlier results for comparison.
4. Run held-out optional-provider tests and approved independent pilots before broader claims.
5. Public visibility, publication and contacting testers require a separate owner decision. Do not publish or recruit automatically.
