# Full-team setup — 2026-10-13

Owner: Nio Martinez. Scope: personal `niomartinez/hyper-agentic-engineering`.

## Task and working state

Add an optional full-team setup using the owner's verified installed upstream versions, a clean Obsidian-compatible memory vault, and Caveman/Ponytail full defaults. Nio authorized committing and pushing the feature to public `main`, based on `a764b2bee4de18eedec5883c058094fecacf13fa`. Use the feature commit in Git history for its exact revision. No tag or release assets were published. Existing unrelated untracked `marketing/` work was preserved.

The development runtime is `0.1.0a4.dev0`; the plugin manifest is `0.1.0-alpha.4-dev.0`. Published alpha.3 remains unchanged and does not accept `--profile`.

## Completed

- `plan --profile full-team` acquires a pinned library during private preparation, then uses the existing hash-checked, journaled installer. Core remains the default. Full-team requires engineering mode, HAE memory and selected supported Claude/Codex/Copilot hosts.
- `hae/resources/team-skills.lock.json` records all 96 verified upstream entries at nine exact installed commits. It includes source-relative assets, hashes, licenses/notices and host variants, with no private machine paths or vault contents. `tools/export_team_manifest.py` maintains the portable inventory.
- 92 eligible bundles materialize as 822 files, 19,824,733 bytes. The four Anthropic DOCX/PDF/PPTX/XLSX bundles are retained as references only because their pinned licenses restrict copying outside their services. Document workflows use native tools; there is no rights-bypass flag.
- `hae/team.py` supports bounded pinned HTTPS acquisition and a verified offline repository-slug snapshot. Archives are validated without extraction or execution. New caches retain only eligible, validated files. Sources stay separate from HAE's release packages.
- Curated host adapters expose eight entry points plus two off switches, loading intact source only when needed. Graphify/Impeccable use host-specific entries; shared Codex/Copilot adapters select the current host. Graphify/full Karpathy stay explicit-only.
- Full root instructions enable Caveman/Ponytail full, preserve required work and normal prose for persistent artifacts, and support session switches. Existing surrounding instructions are preserved.
- New vaults receive `Home.md`, a team guide and clean Obsidian configuration. Existing files remain intact. `obsidian status/open` reports native readiness and dispatches the vault manager without claiming registration/opening succeeded. CLI adapters require explicit targeting of the verified HAE vault.
- Installer previews handle binary assets and bounded text diffs, with the full private plan retained. Executable launcher permissions are journaled, checked against concurrent changes and restored on recovery.
- README, SETUP, setup/engineering/compatibility/upstream guides and mirrored setup skill describe the unreleased development option and native completion checks.

## Verification

- `python3 -m unittest discover -s tests -v`: 100 tests passed locally on macOS, Python 3.14.7. New tests cover acquisition bounds, hashes, exclusions, native opener mocks, modes, coexistence and recovery. No new Windows/Linux CI run is claimed.
- `python3 tools/build_plugins.py`: rebuilt runtime, standalone skills and all four plugin packages with updated manifests/checksums.
- Packaged full-size offline roundtrip in a disposable profile configured Claude/Codex/Copilot, installed all 822 eligible library files, routed debugging to the expected installed method, saved and recalled a checkpoint, produced an unchanged replan, and uninstalled while restoring pre-existing instructions byte-for-byte and preserving notes/vault configuration.
- Pinned file hashes matched the retained original source snapshots. Complete upstream ZIP fixtures validated for all nine sources. Read-only HEAD checks returned HTTP 200 with matching URLs for all nine pinned archive endpoints; live archive downloads were not exercised.
- Source and nested artifact recognizable-secret/path scans found no findings; eight new implementation/test files were also scanned separately. `git diff --check` passed. These checks are not an independent security audit.

## Remaining and next action

Check the native CI matrix triggered by the authorized source push and record its result. Tagged release publication remains a separate action requiring owner authorization. Each consenting developer must verify live native skill discovery, registered Obsidian vault opening and any optional CLI setup. Tests mock native opens; no live model-session acceptance is claimed. Cowork full-team remains unsupported. Provider use, capture hooks, backups, account plugins and model settings remain unchanged by this option.

Use a reviewed current checkout/runtime for full-team; published alpha.3 can only perform core setup. Obsidian app installation uses its official channel with applicable authorization. Memory itself requires no Obsidian app, paid provider or secondary memory model.
