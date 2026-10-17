# Phase 9A — Hosted adapter contract and synthetic pilot plan (NOT ACTIVATED)

Status: PREPARATION ONLY. Parent main: `f65173563abf960ad2ca794919dbfed84185ece8`. No hosted job, schedule, writable endpoint, database, external transport or Windows task has been created.

## Objective
Prove on a future independently hosted run that a *synthetic* writer can commit an immutable generation, that a read-only adapter serves only committed generations, and that an independent reader can catch up while a Windows backup client is offline. This design **does not yet prove** hosted persistence or production compatibility.

## Proposed boundaries
- Public GitHub repository contains source and disposable test fixtures only, never state, forecast ledgers, credentials, private object names or generated backups.
- Writer: eventual one-shot isolated hosted worker, no direct frontend exposure. Enforce strict writer lease/epoch fencing, transaction-level generation CAS, deterministic input identity, time cutoffs, bounded payload sizes and idempotent settlement.
- Durable store: private project/account chosen after capacity and billing approval. Read-only credentials cannot commit, mutate or enumerate other sports.
- Reader: authenticated non-mutating projection adapter. Return `schema_version`, `synthetic=true`, `generation`, `head_digest`, `watermark`, and exactly the bounded authorized projection. No SQLite file serving, raw tokens, exception traces, directory listing or operational event disclosure.
- Publication: never expose orphan/uncommitted objects; checksum and checkpoint links validated before a generation is visible. No rollback on cache expiry, process restart, retry, or concurrent reader.
- Offline Windows: pull-only client stores encrypted, staged, versioned snapshots when connected, with no ability to write to hosted authority. Client downtime does not prevent hosted writer execution or website reads.
- Deployment separation: synthetic-only domain/namespace and disabled-by-default routes. Existing Sports Edge Hub production and NCAAF PPG/Ridge frozen models remain untouched.
- Strict cost goal: inventory actual billed plans, account-level quotas and capacity; do not equate an existing Pro subscription with zero incremental usage. No new billable resources without owner consent.

## Phased acceptance gates
1. **9A-1 local adapter contract:** implement a pure read-only projection serializer against the existing synthetic simulator; reject malformed/uncommitted/stale heads, invalid schema and oversized requests; test permissions, deterministic output and recovery.
2. **9A-2 hosted proposal:** identify an exact runner, private store, namespace, authentication, isolation and limit; create a cost/permissions matrix. No activation yet.
3. **9A-3 future separate approval:** explicitly authorize a time-bounded hosted *synthetic-only* test. Capture run ID, actual remote persistence over two independent runs, fresh-host retrieval, Windows-off condition and cleanup receipts.
4. **9B+ real authority:** separate approval for real forecast data, migration, secure production writes, live settlement, deployment and Windows synchronization.

## Negative controls
Reject unpublished generation; stale checkpoint; invalid schema; invalid or replayed lease; tampered object; unauthorized reader/writer; partial write; oversized page; process restart with empty ephemeral disk; duplicate settlement; and attempted cross-sport access. Test no plaintext, secrets or live model references in public outputs.

## What is NOT claimed
The Phase 8 simulator is not an operational hosted writer. A mock adapter is not a live website. Existing NCAAF forecasts (62 PPG, 59 Ridge), three PPG settlements and original models remain local. Off-host security, real power failure, retention/compaction, quotas and independent recovery remain unresolved.

`HOSTED_READY=false`; `MODEL_VALIDATED=false`; `BACKUP_PUBLICATION_AUTHORIZED=false`.
