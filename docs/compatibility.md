# Compatibility and evidence

The implementation is a public alpha. Engineering is the default; general work is optional. A unit fixture, a direct helper invocation, native plugin discovery, and a live model session are different kinds of evidence.

| Surface | Integration | Current limitation |
| --- | --- | --- |
| Claude Code | Personal skills or generated plugin, native settings hooks | CLI authentication is required for a live model-session test |
| Codex CLI/app | Shared skills or generated plugin, native hooks.json | Exact hook trust must be reviewed in the host; config alone does not prove dispatch |
| Copilot CLI | Shared skills or generated plugin, owned user hook file | Parent stop may be metadata-only; direct checkpoint needed |
| Claude Cowork | Generated plugin and optional general-work setup | Sandbox Python/folder access and real save/resume remain unverified |
| Cloud/IDE variants | Portable skills/instructions and sanitized handoffs where supported | Local profile installation does not establish remote vault access |

macOS is the implementation host. Alpha 2 adds native Windows file locking, bounded pipe input, Unicode/binary-safe storage and platform-specific command generation. All 68 tests, package builds, source audits and benchmarks passed in six CI jobs: native Windows, macOS and Linux on Python 3.11/3.12. See the verified run (private predecessor; retained measurements below) and [evidence record](evidence/README.md). WSL remains a separate untested environment. Core/shell checks do not establish live host integration or independent adoption.

The default layout targets `~/.agents/skills`, `~/.claude/skills`, `~/.codex/AGENTS.md`, `~/.claude/CLAUDE.md`, and `~/.copilot/copilot-instructions.md`. Custom `CODEX_HOME`, `CLAUDE_CONFIG_DIR` or `COPILOT_HOME` values are not silently redirected. Select a disposable `--home` for tests and inspect the plan. Do not claim a custom layout works without checking discovery.

The provider tests use synthetic deterministic responses, not the author's paid key. They establish scope, bounds and failure behavior, not general semantic quality. A separate held-out benchmark and actual adoption evidence are required for Jev recommendations.

Efficiency measurements must report cold indexing, warm recall and actual model usage separately. No percentage token-savings claim is made for style presets. The main model still reads context and produces approved packet prose.

The [evidence record](evidence/README.md) retains both Linux and Mac results, including the Mac performance miss. The alpha does not claim the latency target is met across machines.

Before claiming stable, broadly validated support: portable extraction audit; coexistence/crash/uninstall tests; live host acceptance; held-out memory tests; comparable efficiency measurements; three consenting developer pilots. General-work onboarding needs a consenting non-engineer acceptance test before it is advertised as supported. Do not contact testers automatically.

Official references checked for this implementation:

- [Codex hooks](https://learn.chatgpt.com/docs/hooks)
- [Claude Code hooks](https://code.claude.com/docs/en/hooks)
- [Copilot hooks](https://docs.github.com/en/copilot/reference/hooks-reference)
- [Copilot plugins](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference)
- [Cowork plugins](https://support.claude.com/en/articles/13837440-use-plugins-in-claude)
- [Cowork project memory](https://support.claude.com/en/articles/14116274-organize-your-tasks-with-projects-in-claude-cowork)
