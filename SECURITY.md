# Security and privacy

HAE is an early evaluation release. The source, test fixtures and release packages are intended to be public; your configuration, plans, notes and transcripts are not. No audit can guarantee the absence of every vulnerability or private fact.

## Defaults and trust boundaries

- The memory backend is local. There is no telemetry, automatic upload, generative memory worker or automatic backup. Approved saves use local code. The main agent still consumes tokens while reading context and writing prose.
- Setup changes only reviewed installer-owned integrations, retains recovery snapshots and checks file hashes. It preserves existing hooks, instructions, models and native memory. Ordinary concurrent edits cause conflicts instead of blind replacement.
- Automatic capture is opt-in per mapped project. It reads bounded event data, not transcript paths. Captures and retrieved notes are untrusted evidence, never instructions, authorization or verified current status.
- Scope filtering prevents accidental retrieval across mapped projects. It is not multi-user access control: a process with filesystem access can read the vault. The packet's `approved` field records the main chat's decision; it is not a cryptographic signature or authorization service.
- Notes and snapshots are not encrypted. Use an OS account and directory permissions appropriate to your work. Windows files inherit ACLs; POSIX mode bits do not replace Windows ACLs. These helpers are not hardened against an attacker who already controls the same writable directory tree or operating-system account.
- Jev is experimental and off by default. Enabling it requires chosen scopes, explicit spending limits and the user's environment key. Small selected content then leaves the machine for the provider. Local budget estimates are not the provider's billing balance. Never place keys in notes, commands, screenshots or Git.
- Secret-pattern checks catch recognizable formats, not all confidential prose or credential types. Review notes and portable handoffs before sharing. Keep memory/configuration and product source in separate locations; do not commit an entire vault to a public repository.

## Release integrity

Use a tagged release from this repository. Verify downloadable assets against its `SHA256SUMS`, or review a checkout pinned to that tag. Checksums establish artifact consistency, not independent publisher identity. Runtime files and plugin archives use explicit file lists; incidental files in a developer's workspace are not shipping inputs.

The release audit checks tracked source, reachable public Git history and nested release archives for recognized credentials and private machine paths. Commit metadata is reviewed separately. Synthetic fixtures and documentation are reviewed for private account/client details. This does not constitute an external security audit or a certification.

## Reporting a vulnerability

Use this repository's **Security → Report a vulnerability** private reporting channel when available. Do not post credentials, real notes, private configuration or unredacted logs in a public issue. Use synthetic reproduction data. If private reporting is unavailable, open only a content-free request for a private reporting channel.

For a leaked credential, revoke it at its provider; removing a Git commit is not revocation. For damaged setup, preserve the local journal and use the [documented recovery flow](docs/setup.md). Uninstall does not delete memory.
