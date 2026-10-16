# Sources and licensing

HAE's original code is MIT licensed. Its memory primitives were extracted from the author's original local runtime, then generalized. No private vault notes, account data or Git history were imported. HAE has no generative memory-worker dependency.

`integrations.lock.json` records optional upstream repositories and exact commits observed on 2026-10-01. `python3 -m hae catalog` displays this reference catalog. It does not install or execute those projects. The catalog does not imply every path at that commit has been audited. Review the exact chosen skill and its dependencies and retain its license/notices when installing or redistributing.

- Ponytail, Matt Pocock, Obsidian and Taste: installed-source observations were MIT.
- Impeccable: Apache-2.0 observation; preserve applicable notices.
- Caveman: the skill is MIT, while Engine-linked components have separate BSL terms. HAE bundles neither.
- Anthropic: mixed licensing; document skills are source-available. Never relicense the entire collection as HAE's MIT code.
- Graphify and the community Karpathy-inspired collection: separate optional projects. The latter is not an official Karpathy release.
- Graphify 0.9.92 (full-team pin): Apache-2.0, with its retained MIT text for earlier contributions (`LICENSE`, `LICENSE-MIT`, `NOTICE`).
- addyosmani/agent-skills and Context7 (full-team pins): MIT. `LICENSE` and `README.md` stay with each pinned repository.
- ICM (`rtk-ai/icm`, optional, documented in `SETUP.md` only): Apache-2.0, release `icm-v0.11.4`. HAE ships and pins no ICM code.

No third-party skill body is bundled in HAE source or core packages. Full-team materializes reviewed upstream files into the user’s installation from a separate manifest or reviewed local source directory; those files retain their upstream licenses and notices. The small lean preset is original generic guidance. Users may retain their own existing style or independently select upstream skills.

Primary references: [Caveman licensing](https://github.com/JuliusBrussee/caveman/blob/main/LICENSING.md), [Anthropic skills](https://github.com/anthropics/skills), [Agent Skills specification](https://agentskills.io/specification).

## Full-team snapshot

The optional unreleased full-team profile uses a separate manifest matching 123 upstream entries across eleven repositories, reviewed in the author's installed library. Default preparation downloads 119 entries. Anthropic `docx`, `pdf`, `pptx` and `xlsx` remain catalog references with exclusion details because their license restricts outside-service retention and reproduction; native document tools handle those tasks unless separate rights are established. Those installed versions can differ from the older core reference catalog; do not treat the two catalogs as interchangeable. For example, `skills route --task graph` still reports the core catalog's Graphify commit as `optional_source`, not the full-team 0.9.92 pin, while the full-team-only routes report the team manifest's commit. Portable HAE adapters supply team routing and host guidance. The count describes upstream entries, not 123 independently tested integrations or every dependency being installed.

Source review and installation preserve the original source path, pinned version and applicable license/notices. A reviewed `--team-source-dir PATH` can supply local sources; never point it at a private vault or copy unrelated files. The profile excludes the author's custom release/account skills, private notes and account-linked plugins. Plugin availability and skill dependencies, including Graphify and document tools, are checked when a task needs them. Setup never executes instructions from source skills merely because they mention installation.

See [team setup](team-setup.md) for acquisition, exclusions and native host verification. The full community Karpathy method requires an explicit user request even when present in the cold library. Graphify is model-invocable (graphify-first), and Context7 and nine of the 25 addyosmani/agent-skills are task-routed; see [team setup](team-setup.md).

The two newest pins are partial snapshots. From `addyosmani/agent-skills` (tag `0.6.13`, commit `aeac41d4d005999432bb7312f7ff06383a91d59d`) only `skills/**`, the shared `references/` checklists those skills link to, `LICENSE` and `README.md` are pinned; its commands, personas, hooks, scripts and evals are not, and its `.opencode/skills` link is never followed. From `upstash/context7` (commit `e0041949fdb3b49b304d98715dde35be51b7c3d1`) only `skills/find-docs`, `skills/context7-cli`, `LICENSE` and `README.md` are pinned; its `context7-mcp` skill and `rules/` are not, because HAE documents the MCP option instead of shipping it. The pinned Context7 skill text runs `npx` with a latest tag; the HAE `context7` adapter overrides that with an installed, pinned `ctx7`. Graphify moves from 0.9.71 to 0.9.92 (commit `86c57be8204673c2a1b9849a3292a7dd3ab373d8`); the file hashes were checked against the GitHub archive at that commit.
