# Approved packets

`memory save --packet -` accepts JSON on stdin; files are also accepted. Maximum 24 KB and five records/updates. Main chat approves the prose and scope; no second model is called.

```json
{
  "approved": true,
  "job_id": "atlas-offline-decision-1",
  "mode": "remember",
  "project": "atlas",
  "scope": "personal",
  "source": "User decision in current task",
  "records": [{
    "title": "Offline storage decision",
    "summary": "Use SQLite for offline drafts.",
    "next": "Verify reconnect behavior."
  }]
}
```

Modes: `remember`, `checkpoint`, `override`. Use a new stable job ID for new content. Retrying the same packet returns its receipt; different content under the same ID is rejected. Explicit saves bypass automatic classification. An approved flag represents main-chat approval; it is not an access-control boundary between users.

For an override, supply `updates` with `path` (vault-relative), `expected_sha256` of the complete existing UTF-8 text, and `content` containing the complete approved replacement. Only scoped Profile/Practices notes or this project's mapped note can be updated. Keep its scope property and explain which earlier decision is superseded. Changes to another project's note or a stale hash are refused. `records` may accompany the update for a brief audit checkpoint.

Optional packet attribution: `agent`, `actor`. Record only known authors. A record supports `title`, `summary`, `next`, and an absolute `handoff_path` reference. Memory stores no raw transcript and does not follow that reference.

`handoff --project atlas --packet handoff.json --output /absolute/project/docs/handoffs/topic.md` creates a new file inside the mapped project. Its separate packet has `approved: true`, `task`, `completed`, `evidence`, `remaining`, `owner`, `references` and optional `branch_commit` (engineering). No private memory is imported automatically. Existing files are never overwritten.
