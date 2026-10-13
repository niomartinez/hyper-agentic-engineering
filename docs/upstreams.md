# Sources and licensing

HAE's original code is MIT licensed. Its memory primitives were extracted from the author's original local runtime, then generalized. No private vault notes, account data or Git history were imported. HAE has no generative memory-worker dependency.

`integrations.lock.json` records optional upstream repositories and exact commits observed on 2026-10-01. `python3 -m hae catalog` displays this reference catalog. It does not install or execute those projects. The catalog does not imply every path at that commit has been audited. Review the exact chosen skill and its dependencies and retain its license/notices when installing or redistributing.

- Ponytail, Matt Pocock, Obsidian and Taste: installed-source observations were MIT.
- Impeccable: Apache-2.0 observation; preserve applicable notices.
- Caveman: the skill is MIT, while Engine-linked components have separate BSL terms. HAE bundles neither.
- Anthropic: mixed licensing; document skills are source-available. Never relicense the entire collection as HAE's MIT code.
- Graphify and the community Karpathy-inspired collection: separate optional projects. The latter is not an official Karpathy release.

No third-party skill body is bundled in HAE source or core packages. Full-team materializes reviewed upstream files into the user’s installation from a separate manifest or reviewed local source directory; those files retain their upstream licenses and notices. The small lean preset is original generic guidance. Users may retain their own existing style or independently select upstream skills.

Primary references: [Caveman licensing](https://github.com/JuliusBrussee/caveman/blob/main/LICENSING.md), [Anthropic skills](https://github.com/anthropics/skills), [Agent Skills specification](https://agentskills.io/specification).

## Full-team snapshot

The optional unreleased full-team profile uses a separate manifest matching 96 upstream entries observed in the author's installed library. Default preparation downloads 92 entries. Anthropic `docx`, `pdf`, `pptx` and `xlsx` remain catalog references with exclusion details because their license restricts outside-service retention and reproduction; native document tools handle those tasks unless separate rights are established. Those installed versions can differ from the older core reference catalog; do not treat the two catalogs as interchangeable. Portable HAE adapters supply team routing and host guidance. The count describes upstream entries, not 96 independently tested integrations or every dependency being installed.

Source review and installation preserve the original source path, pinned version and applicable license/notices. A reviewed `--team-source-dir PATH` can supply local sources; never point it at a private vault or copy unrelated files. The profile excludes the author's custom release/account skills, private notes and account-linked plugins. Plugin availability and skill dependencies, including Graphify and document tools, are checked when a task needs them. Setup never executes instructions from source skills merely because they mention installation.

See [team setup](team-setup.md) for acquisition, exclusions and native host verification. Graphify and the full community Karpathy method require an explicit user request even when present in the cold library.
