# Phase 9A — Hosted adapter contract and synthetic pilot plan (NOT ACTIVATED)

Status: LOCAL SYNTHETIC ADAPTER IMPLEMENTED; HOSTED PILOT NOT ACTIVATED. Parent main: `f65173563abf960ad2ca794919dbfed84185ece8`. No hosted job, schedule, writable endpoint, database, external transport or Windows task has been created.

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


## Implemented local Phase 9A-1 (2026-10-17)

`NCAAF_SYNTHETIC_PROJECTION_V1` in `scripts/readonly_projection_v1.py` is an offline read-only capability over a marked Phase8 host. It opens SQLite with mode=ro, starts one read transaction, verifies synthetic identity/integrity, validates the complete committed checkpoint chain against bounded original SHA256 objects, replays immutable facts in an in-memory synthetic SQLite verifier, and compares exact authoritative fact bytes. Only then does it serialize a canonical response. Orphans are ignored; missing/partial/corrupt committed objects reject the read. Writer fencing and original forecast/settlement IDs are unchanged. No existing simulator/model code is modified.

Request requires exactly version/offset/limit/max_age, with integer (not boolean) bounds: offset 0..10000, limit 1..50, max_age 0..86400 seconds. Caller supplies an integer trusted current clock and a trusted persisted checkpoint floor. State older than max_age, future commit clocks, floor rollback/equivocation, inconsistent heads or incompatible namespaces fail closed. At most 10000 facts, 10000 generations, 16MiB aggregate object bytes, 1MiB per object and 64KiB output are accepted. Full-chain replay costs grow with history; this is deliberately bounded and not a production-scale cache. No decompression, arbitrary query, path, model, sport or write action is accepted in requests.

Response contains version, synthetic=true, generation/head_digest/watermark/committed_at/fence, bounded forecast page, immutable original IDs/model versions/as_of/created_at, scores/probability, original verified final when present, and an explicit review_required flag. Reviewed original settlements are not silently replaced or declared eligible accuracy. No raw sources/features, SQLite files or directory listings are returned. The model names identify synthetic SIMULATED_RULES_V1 streams, never authentic PPG/Ridge inference. No metrics or real forecasts are invented.

The reader receives only marked paths, never a HostedSimulator/writer/transport reference. It exposes no write endpoint, accepts no credentials and makes no host writes. In-memory replay is internal validation, not an authority write. Read connections reject mutations; no source hashes change after concurrent reads. Python object access is not an authorization sandbox: a hostile caller with filesystem access can independently open files. Future hosted least-privilege identities/ACLs and process isolation remain mandatory.

There is no projection cache. Each read revalidates source state. Persisted floor custody is the caller's responsibility: pass the last accepted generation+digest on every request/restart and atomically advance it only after acceptance. An initial floor must come from an authenticated bootstrap. Dropping/resetting that floor can defeat rollback detection; no durability guarantee is claimed for unimplemented hosted storage. A stale read concurrent with a newer commit is a valid point-in-time snapshot only if it meets the supplied floor and freshness policy. No response trace sanitization/HTTP error mapping is implemented because there is no HTTP server.

Regression tests cover deterministic bounded output/IDs, concurrent readers/restarts, byte-preserving host reads, SQLite read-only enforcement, malformed/version/cross-sport requests, stale clocks/floors, cache rollback via caller floor, partial/missing/corrupt objects, orphan uploads, uncommitted head, logical fact corruption, namespace/resource limits, original settlement preservation, and reads while a writer has published an object but has not committed. Existing Phase8 suites retain fencing, duplicate-settlement and filesystem adversarial tests. The explicit file allowlist adds only this adapter and its test. Manual workflow/template remain byte-identical to reference main.

Reproduce: `python -I -m unittest discover -s tests -v`; `python -I scripts/security_preflight.py`; `node tests/synthetic_crypto_check.mjs`. Verified commit/log hashes and checkpoint live in `C:/Users/jlebr/sports-edge-hub/research/ncaaf-observer-phase9a-evidence-20261017`, with results published on draft PR12. Source baseline PR12 78de6f2f896f22a2c4c09bacc46eddef133eaf15; main f65173563abf960ad2ca794919dbfed84185ece8. HISTORICAL_GUARD_UNEXPLAINED remains an audit limitation.

Remaining hosted dependencies: separately authorized private runner/store; authentic transport and manifest trust; least-privilege reader/writer IAM; safe HTTP error mapping/request limits; durable rollback floor and trusted clock; provider-side transactional publication/CAS; quotas/cost approval; encrypted transport/storage/key custody; independent-host restoration and power-loss tests; compaction/retention; monitoring/alerts and reviewed deployment. No hosted pilot or production activation is authorized by these local tests. Existing Windows prototype is not encrypted by this adapter. No schedules, migrations, persistent credentials or real data are introduced.

HOSTED_READY=false; MODEL_VALIDATED=false; BACKUP_PUBLICATION_AUTHORIZED=false. Restart from the exact PR12 head, verify receipt hashes and rerun offline checks; do not activate external services.
