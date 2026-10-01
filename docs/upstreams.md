# Sources and licensing

HAE's original code is MIT licensed. Its memory primitives were extracted from the author's original local runtime, then generalized. No private vault notes, account data or Git history were imported. HAE has no generative memory-worker dependency.

`integrations.lock.json` records optional upstream repositories and exact commits observed on 2026-10-01. `python3 -m hae catalog` displays this reference catalog. It does not install or execute those projects. The catalog does not imply every path at that commit has been audited. Review the exact chosen skill and its dependencies and retain its license/notices when installing or redistributing.

- Ponytail, Matt Pocock, Obsidian and Taste: installed-source observations were MIT.
- Impeccable: Apache-2.0 observation; preserve applicable notices.
- Caveman: the skill is MIT, while Engine-linked components have separate BSL terms. HAE bundles neither.
- Anthropic: mixed licensing; document skills are source-available. Never relicense the entire collection as HAE's MIT code.
- Graphify and the community Karpathy-inspired collection: separate optional projects. The latter is not an official Karpathy release.

No upstream skill body is copied into HAE. The small lean preset is original generic guidance. Users may retain their own existing style or independently select upstream skills.

Primary references: [Caveman licensing](https://github.com/JuliusBrussee/caveman/blob/main/LICENSING.md), [Anthropic skills](https://github.com/anthropics/skills), [Agent Skills specification](https://agentskills.io/specification).
