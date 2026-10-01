# Memory, privacy and providers

HAE uses Markdown for approved memories and project notes. A local SQLite database contains derived text caches, idempotent save receipts and content-free provider usage accounting. The main chat decides what a user meant; local code writes the approved packet. No additional generative worker is involved.

Use [the packet reference](../skills/hae-memory/references/packets.md). Reusing a job ID with different content is rejected. Exact-hash updates protect authoritative notes. An `approved` flag records the caller's assertion of main-chat approval, not identity verification. Filesystem access is the trust boundary.

## Retrieval and freshness

Project matching checks explicit folder mappings and Git worktree boundaries. Unknown ownership remains unresolved. Local search filters note metadata by project and scope before selecting bounded excerpts. Optional Jev only sees approved scopes and shortlisted text. Original captures remain unverified evidence and cannot authorize a new action.

The required project note and mode practice are outside semantic ranking. Read those at task start, then retrieve narrowly. Recall returns at most five matches/evidence items and at most 3,600 excerpt characters. This bounds excerpt output, not the total cost of an agent session. The assistant still spends tokens reading returned context.

`memory health` reports missing notes, pending captures and review dates older than 14 days. It does not rewrite history or declare old facts current. Maintain authoritative project status after verification. Explicit overrides should explain which earlier statement they supersede.

## Jev: experimental and off by default

The built-in experimental endpoint is `https://api.typesafe.ai/v1/systemone`. Credentials come only from `HAE_JEV_API_KEY` in the process environment; never paste keys into a packet, command argument, configuration file, repository or note. Use your own shell/OS secret-management workflow. HAE does not read another user's keychain or reuse the author's account.

Enable only with explicit mapped scopes and your own limits:

```sh
python3 -m hae memory backend jev --scopes personal \
  --daily-budget 0.10 --lifetime-budget 2.00
```

These are example limits, not recommended expenditure or an account-balance check. Set `--price-per-million` to the rate you have verified with the provider. The current default estimate originates from the initial integration and can become outdated. Usage reserves a conservative estimate before a request; failures retain the reserve. Local limits cannot enforce the provider account's total spending by other apps.

Selection classifies bounded excerpts, preserves selected text verbatim and marks uncertainty for review. Recall ranks a small local shortlist. Requests have byte/count/time limits; redirects are refused; responses require the expected typed schema. Failed selection leaves inputs pending; failed ranking falls back to local search. There is no expensive fallback.

Disable provider use immediately with `python3 -m hae memory backend local`. Notes remain available. Hooks themselves capture locally and detach selection only when Jev is enabled. An absent API key does not prevent approved local saves.

## Sharing and backups

Each person owns their memory folder. Do not share a personal vault simply because agents work on the same team. Export only approved project handoffs containing relevant evidence and the next step. AI account changes do not prove authorship or grant access to another person's account.

`backup --dest /chosen/private/folder` creates a local ZIP of allowlisted Markdown folders after a recognizable-secret scan. Media, captures, runtime state and machine configuration are excluded. It never uploads, stages, commits or pushes. Destination access control is the user's responsibility. Keep local media or approved private backup URLs as references in notes.

For Git backups, use an existing verified private repository and review exactly what will be committed. Keep `.hae-state/`, `System/hae-projects.json`, `System/hae-config.json` and `Inbox/` ignored. Never turn the memory repository into the product source repository. Secret-pattern checks are not a guarantee that prose contains no private information.

Automatic evidence is selected per project. Adding a new project does not inherit another project’s capture opt-in. Use `memory capture off --project PROJECT_ID` to stop capture for one project, or `memory capture on --project PROJECT_ID` to permit it; an installed and trusted host hook is still required.
