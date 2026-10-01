# Native Windows setup

Use Windows 10/11, Python 3.11+ and a reviewed checkout. No WSL, Bash, administrator terminal or execution-policy change is needed for the HAE core. Install Python and the desired agent separately if missing; HAE does not download applications or change account settings.

In PowerShell, from the HAE checkout, replace the project path and scope with your own:

```powershell
py -3 --version
py -3 -m hae --vault "$HOME\Documents\Agent Memory" plan --project "C:\Projects\Atlas" --project-id atlas --name Atlas --scope personal --agents codex,claude,copilot
```

Review the returned changes and conflicts. Then run the exact `apply` command printed by the CLI and inspect the result:

```powershell
py -3 -m hae doctor
```

PowerShell command previews use its call operator and literal quoting, including paths with spaces or apostrophes. A packaged `hae.pyz` prints commands that continue using that archive; it does not assume an installed Python module or a source checkout.

For a self-contained package:

```powershell
py -3 tools\build_plugins.py
py -3 dist\hae.pyz --help
```

Global `--home`, `--state-dir` and `--vault` options precede the command. Use a disposable profile to evaluate installation before adopting it. Default profile state is `$HOME\.local\state\hyper-agentic-engineering`; standard agent folders stay under the selected profile home. Do not mix one Windows profile with a WSL installation or assume account-synced plugins provide remote vault access.

## Files, hooks and recovery

- Memory uses UTF-8 and LF; imported CRLF metadata is recognized. CLI results are ASCII-safe JSON. Paths and Unicode content are exercised in the portable tests.
- Windows byte-range locks protect installer and memory operations. Atomic replacement checks existing hashes. Files inherit the chosen folder's Windows ACLs; POSIX permission bits are not an ACL guarantee. Use a private local profile/vault folder.
- Symlink and junction/reparse-point destinations are refused. Use a regular local directory, not a linked or cloud-placeholder vault, and keep backups separate. Very long paths still depend on Windows long-path settings; a short vault/profile location is simplest.
- Claude and Copilot CLI hooks use executable-plus-arguments configuration without a shell. Codex uses its documented Windows command override to invoke PowerShell with literal arguments. The generated configuration is tested directly; actual host dispatch and native trust still require a live host check.
- The documented command/argument hook forms require a current host version. Older hosts must be upgraded or use direct checkpoints. Installation does not bypass Codex `/hooks` trust or change shell execution policy.
- `rollback` and `uninstall` retain memory and refuse edited owned fragments, as on macOS/Linux. See [setup and recovery](setup.md).

References: [Claude command hooks](https://code.claude.com/docs/en/hooks#command-hook-fields), [Copilot hook configuration](https://docs.github.com/en/copilot/reference/hooks-reference), [Codex hooks](https://learn.chatgpt.com/docs/hooks), [Python Windows file locking](https://docs.python.org/3.13/library/msvcrt.html#msvcrt.locking). These describe the underlying interfaces, not a completed live-host acceptance test of HAE.
