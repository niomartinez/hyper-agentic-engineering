# Engineering workflows and native Windows — alpha 2

## Completed

Implemented the user's requested generalized engineering practices and native Windows setup in the private HAE repository. Engineering remains the default; general work is optional. The engineering skill includes assumptions, focused implementation, reuse, debugging, meaningful verification, review/conflicts, research, scoped memory and resumable handoffs. Specialized tasks route to relevant installed skills; missing integrations use the included workflow. Full third-party bundles remain optional, with community Karpathy/Graphify explicitly requested.

Windows support covers locking, pipe deadlines, literal shell arguments, executable/argument hook forms, binary/Unicode storage, reserved identifiers and junction refusal. Existing user settings and memory remain protected. LF/CRLF conversion is accepted for managed blocks, with surrounding bytes preserved; actual edits still stop removal. CRLF metadata is excluded from recall scoring.

## Verification

Core commit `74f970f100be99bdf1850d34c81313e512c03d56` passed 68 tests in all six Windows/macOS/Linux Python 3.11/3.12 CI jobs, plus builds, audits and benchmarks: private predecessor CI (measurements retained in docs/evidence/). Local macOS Python 3.14.7 passed the same 68 tests. Generated command execution is tested directly; authenticated host lifecycle dispatch is not claimed. Claude plugin validation, Copilot discovery and Codex plugin/three-skill rule validation passed. No paid model/provider evaluation was used.

Read RELEASE-STATUS.md and docs/evidence/README.md for the current evidence, including the Windows Python 3.11 latency miss. docs/windows.md is the native PowerShell quickstart; docs/engineering.md describes defaults and optional integrations. HAE was not installed over the author's live memory system.

## Resume

Validate actual authenticated host save/resume and native hook trust in a disposable profile, then remove the integration. Cowork and WSL still need their own environment acceptance. Evaluate held-out Jev quality, independent adoption and performance variability before broader claims. Historical private-alpha constraint: current public-release authorization and status are recorded in RELEASE-STATUS.md. Marketplace publication and contacting testers remain separate work. Recheck current branch/commit and service state before relying on this handoff.
