# Verification evidence

## Public alpha 3

Alpha 3 adds three tests for allowlisted shipping inputs, nested archive auditing, and the generated runtime’s plan/apply/save/recall/uninstall flow. All 71 tests passed locally on macOS Python 3.14.7. [Public CI run 36863706202](https://github.com/niomartinez/hyper-agentic-engineering/actions/runs/36863706202) verified commit `082a919454496cea428ec504a59d262a60e921a1`: **71 tests passed in each of six Windows/macOS/Linux Python 3.11/3.12 jobs**, along with package builds, nested artifact audits and 1,000-note benchmarks. [Raw results](public-alpha3.json) preserve all timings. Each benchmark returned the expected note first, no irrelevant matches and zero provider calls. Earlier results below describe the private predecessor and are retained as historical measurements, not authenticated live host acceptance. — 2026-10-01

This record distinguishes deterministic core tests, packaging checks and actual host sessions. The last category remains pending.

## Alpha 2 — engineering workflow and native Windows

CI run 36849451698 (private predecessor; retained measurements below) verified commit `74f970f100be99bdf1850d34c81313e512c03d56` with **68 passing tests in each of six jobs**: Windows, macOS and Linux, each on Python 3.11 and 3.12. Package builds, source audits and the 1,000-note benchmark passed in every job. The same 68 tests passed locally on macOS Python 3.14.7 in 15.817 seconds.

The new tests execute generated hook commands and plan/apply previews in the actual platform shells, including Windows PowerShell/cmd, paths with spaces, apostrophes and metacharacters, Unicode memory, binary-safe I/O, process-lock exclusion/release, input deadlines, junction refusal, LF/CRLF conversion, practice upgrades and bounded skill routing. The earlier Windows run exposed a line-ending conflict during removal; its regression test now passes. Benchmark review also caught CRLF metadata being ranked as memory; the benchmark now rejects those irrelevant matches.

These are real core/filesystem/subprocess tests. They are not authenticated Claude/Codex/Copilot sessions or proof of native hook trust. The generated alpha 2 Claude plugin passed native validation; Copilot discovered it as version 0.1.0-alpha.2. The Codex plugin and all three skills passed the bundled rules with the same Ruby/Psych YAML parsing adapter described below.

| CI platform | Python | Cold recall | Warm p95 | Provider calls | Irrelevant matches |
| --- | --- | ---: | ---: | ---: | ---: |
| Darwin | 3.11.9 | 126.34 ms | 41.38 ms | 0 | 0 |
| Darwin | 3.12.10 | 194.89 ms | 76.19 ms | 0 | 0 |
| Linux | 3.11.16 | 344.93 ms | 140.06 ms | 0 | 0 |
| Linux | 3.12.14 | 457.51 ms | 131.00 ms | 0 | 0 |
| Windows | 3.11.9 | 1282.55 ms | 438.33 ms | 0 | 0 |
| Windows | 3.12.10 | 681.36 ms | 162.23 ms | 0 | 0 |

All runs returned the expected memory first with 442-character responses on this fixture and no generative worker calls. Windows Python 3.11 missed the proposed 250 ms warm p95 target in this run; the other five jobs met it. These are synthetic repeated-query measurements, not a universal speed or total-token guarantee. [Raw alpha 2 results](cross-platform-alpha2.json) include timing and version details. Earlier measurements remain below for comparison.

## Earlier alpha 1 core and recall

CI run 36841470968 (private predecessor; retained measurements below) tested core commit `af22d0ab3b48bc0a3d0080bbbe478d97b2bd84e2`. All 53 tests passed on Ubuntu with Python 3.11.16 and 3.12.14. Each job also built packages, completed the tracked-source audit with no findings and ran the synthetic benchmark.

Tests cover exact approved saves, retry/crash recovery, scope isolation, provider failure/caps, worktree matching, existing instructions/hooks, edited fragments, repeat installation, malformed config, per-project capture opt-in, out-of-checkout runtime execution, memory-preserving uninstall, general work and text backup exclusions. Installer transaction tests use real files and a small runtime payload fixture; the portable zipapp and hook subprocess tests build the actual runtime.

The same 53 tests passed on the Mac implementation host with Python 3.14.7 in 200.971 seconds. Linux runs took 2.466 and 2.933 seconds. Machine and filesystem conditions differ substantially; these durations are not a controlled platform comparison.

| Environment | Cold recall | Warm median | Warm p95 | Expected result first | Provider calls |
| --- | ---: | ---: | ---: | --- | ---: |
| Linux CI, Python 3.11.16 | 165.91 ms | 56.17 ms | 91.52 ms | Yes | 0 |
| Linux CI, Python 3.12.14 | 392.01 ms | 111.99 ms | 125.35 ms | Yes | 0 |
| Mac implementation host, Python 3.14.7 | 374,313.21 ms | 1,667.57 ms | 2,936.32 ms | Yes | 0 |
| Mac repeat after the test workload ended | 5,451.97 ms | 58.11 ms | 60.71 ms | Yes | 0 |

Each run uses 1,000 synthetic notes and 20 warm queries. The response was 442 characters; excerpts are bounded at 3,600 characters. These are repeated-query local retrieval timings, not end-to-end model latency, held-out semantic quality or a total-token comparison. Raw reports are [Linux](linux-recall.json), [first Mac run](local-recall.json) and [Mac repeat](local-recall-repeat.json).

The first Mac run overlapped heavy filesystem work and showed severe I/O delays. Contention is a possible contributor, not a proven explanation. It missed the proposed 250 ms warm p95 target. The repeat started after the local test workload ended and met the warm target without a runtime change. Cold indexing and load sensitivity still need investigation; neither run establishes a universal latency guarantee.

## Package checks

- Claude Code 2.1.281 accepted its generated plugin manifest with no warnings.
- Copilot CLI 1.0.89 discovered the generated external plugin as enabled.
- The bundled Codex plugin validator and both bundled skill validators passed. PyYAML was unavailable locally, so the unchanged validation rules used system Ruby/Psych to parse the actual YAML frontmatter through a temporary compatibility adapter. This validates package structure, not live Codex execution.
- Generated artifact hashes are in [artifacts.json](artifacts.json); rebuild with `python3 tools/build_plugins.py`. No binary is committed or publicly released.
- Host discovery and manifest validation do not establish trusted lifecycle dispatch, live checkpoint/resume, or adoption by another person. Cowork remains an evaluation package.

No live paid model or Jev call was made for these checks. Scope/provider tests use deterministic synthetic responses. Source auditing found no recognized credentials or private machine paths; pattern scanning is limited and does not replace manual review before publication.
