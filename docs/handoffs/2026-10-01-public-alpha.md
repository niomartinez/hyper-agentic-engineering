# Public alpha 3 handoff

## Result

The owner authorized the first public alpha release. Agent-led onboarding starts with the README prompt and pinned SETUP.md. The runtime remains local by default; automatic capture, Jev and backups require explicit selection. Existing instructions, hooks and memory are preserved.

Shipping files are allowlisted. Auditing covers current tracked source, public Git objects/commit metadata and recursively nested release archives, without printing matched secrets. Checksums accompany the runtime and four host packages. The public repository starts with reviewed source and GitHub no-reply commit metadata; it does not import private development history.

## Evidence

Runtime commit `082a919454496cea428ec504a59d262a60e921a1` passed 71 tests in each of six native Windows/macOS/Linux Python 3.11/3.12 jobs, with builds, audits and 1,000-note local benchmarks. See [the run](https://github.com/niomartinez/hyper-agentic-engineering/actions/runs/36863706202) and [raw results](../evidence/public-alpha3.json). Three new tests cover excluded incidental files, nested credential detection and a complete generated-runtime install/save/recall/uninstall cycle that preserves prior instructions and saved memory.

## Remaining work

Authenticated host lifecycle acceptance, native hook trust, Cowork/WSL support, optional Jev evaluation and independent adoption remain unverified. Do not claim stable universal host support, measured total-token savings, encryption or an independent security audit. Read RELEASE-STATUS.md and SECURITY.md before extending claims. Source privacy and exact packaged contents must be rechecked for each release. Marketplace publication and contacting testers remain separate work.
