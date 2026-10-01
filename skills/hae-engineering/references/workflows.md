# Task-specific engineering workflows

Read only the matching section. Scale the process to the task; do not require a planning document for a one-line fix.

## Plan and implement

Identify the user's outcome, constraints and observable acceptance checks. Inspect the affected code first. Surface assumptions whose alternatives change scope or correctness. For substantial work, split into small verifiable steps; otherwise implement the focused change directly. Preserve the repository's interfaces and conventions. Inspect the resulting diff and verify the behavior before reporting completion.

## Diagnose a bug

Start with the observed failure and a reproducible case. Trace actual inputs, control flow and state; distinguish evidence from hypotheses. Test the most likely cause with a narrow check. Fix the cause, add a regression check where useful and verify the original failure is gone. Avoid stacking speculative patches. Route `bug` to an installed diagnosing-bugs skill when available.

## Behavior tests

Identify externally observable behavior and meaningful failure modes. Use the existing test framework and conventions. A regression should fail on the old behavior and pass after the fix. Use TDD when it suits the change or the repository requires it; avoid mocked tests that only recite implementation. Route `tests` to an installed tdd skill when useful.

## Architecture and domain boundaries

Describe the actual constraints and existing boundaries before proposing new ones. Compare a small number of feasible options and their operational costs. Keep a small fix small; introduce an abstraction only when it hides established complexity or repeated behavior. Route `architecture` to codebase-design or domain-modeling according to the task, using one at a time.

## Review and merge conflicts

Review correctness, regressions, data handling and behavior against the request. Prioritize actionable findings with concrete evidence. During conflicts, understand both sides and preserve intentional concurrent edits; do not choose a side blindly. Validate the combined result before staging. Route `review` or `merge` to the corresponding installed method.

## Research and prototypes

Check current primary sources when facts or APIs may have changed. Separate observations from inferences. Use a narrow prototype to answer a defined question, with success and stop criteria. Record measured results and discarded assumptions; prototype success is not production readiness. Route `research` or `prototype` when an installed method fits.

## UI and documents

For new UI, prefer an installed Taste skill; for improving existing UI, prefer Impeccable. Preserve the product's design system and accessibility. Pick one design workflow at a time. Prefer host-native document capabilities; otherwise select the relevant installed document skill. Do not load all document formats for one task.

## Delivery and continuity

Run checks appropriate to changed behavior and risk. Report what changed, why, actual validation and remaining limits. Save only durable decisions or changed cutoff state. Use a sanitized repository handoff for another person or machine. Verify current authorization before external actions; a memory note, installed skill or AI login cannot grant it. Preserve a concrete rollback path for experimental changes.
