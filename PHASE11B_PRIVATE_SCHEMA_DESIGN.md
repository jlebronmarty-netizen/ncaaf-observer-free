# Phase 11B — private NCAAF namespace, local-engine verification plan

Status: DESIGN ONLY. Nothing in this document authorizes running DDL on Supabase, changing MLB grants, creating cloud credentials, altering production, or enabling hosted jobs. Baseline observer main `a3c8f2584fd4f7195a4e2dc7a666c3f86ebeea3c`; PR #18 is a separate pending billing/isolation review.

## Facts to preserve
- Owner screenshots (2026-10-20) show Supabase Pro organization, Spend Cap enabled, two paid Micro compute instances, and Pick Analyzer t4g.micro in us-east-2. Storage Size is object storage, **not** PostgreSQL disk headroom. Point-in-time CPU/RAM/Disk is not a guaranteed spare allocation. Spend Cap does not guarantee zero extra compute/add-on charges.
- Data API currently exposes `public` and `graphql_public`; panel indicates zero of 63 functions exposed through Data API. SQL `PUBLIC EXECUTE` and Data API exposure are different controls. Two legacy MLB SECURITY DEFINER routines with SQL PUBLIC EXECUTE were identified separately, but must not be changed without a distinct impact review.
- Phase 10 synthetic local PostgreSQL tests passed; these do not certify the shared hosted project.

## Candidate private schema (NOT a production migration)
Use a *new, unexposed* schema such as `ncaaf_observer_private`, subject to account approval. Distinct provider principals: synthetic writer, read-only verifier, recovery verifier, and offline cleanup, not a blanket service_role in browser or public Actions code. Deny schema USAGE and function EXECUTE to PUBLIC, anon, authenticated and unrelated application roles unless expressly reviewed; consider global default EXECUTE semantics and object-owner behavior. Lock down search_path and privileges for every SECURITY DEFINER function. Force RLS and test actual effective privileges; RLS alone does not protect against privileged owner or bypass roles.

Minimal logical tables: immutable model-version registry; immutable synthetic event/observation/fact ledger; checkpoint journal (generation, authenticated parent/hash, watermark, fence epoch, committed_at); fenced head/lease control; collision/review journal. Immutable objects must be content-addressed with no-clobber semantics. Head advancement must be transactional CAS and never expose uncommitted objects. Prototype field contracts must remain identical to Phase 9 bridge, with explicit versioning and migration plan.

## Local disposable PostgreSQL test gates
1. Use exclusively fresh local PostgreSQL 17.11 clusters in short, private, ACL-verified Windows TEMP/TMP roots; no remote endpoints, Supabase connection strings, operational datasets or credentials.
2. Create synthetic shadow roles for existing exposed API roles, legacy MLB canary owner/definer, and proposed NCAAF identities. No copies of actual MLB function bodies/data.
3. Verify that a genuine restricted login cannot SELECT/INSERT/UPDATE/DELETE in another sport, invoke definer canary, change role, create functions in a privileged schema, or change checkpoint head without writer privilege.
4. Explicitly test default global PUBLIC EXECUTE, the interplay of schema USAGE and function grants, forced RLS, role inheritance, search_path/temp object shadowing, token revocation analogues, writer fencing, CAS races, duplicate settlement, rollback and cold recovery.
5. Exercise a compromised/unauthorized Data API role *in the fixture only*, and prove there is no path to NCAAF read/write or privileged legacy canary. Record actual PostgreSQL denial SQLSTATEs, not merely static expectations.
6. Re-run all existing 124 Python tests, scanner and Node AES-GCM; any new fixture/tests must stay within strict allowlist. No modifications to existing manual workflow/template.
7. Record exact executable source/tree hashes, asserted/failed/unreached engine checks, network isolation, bounded runtime, cleanup and logs.

## Hosted activation prerequisites — all BLOCKED
- Independent review of **effective shared-project** grants and legacy functions, API exposed-schema settings and role paths. No MLB remediation in this task.
- Verified provider-specific transport, authenticated durable checkpoint custody, AEAD key ownership/rotation, reader-writer separation, and independent hosted recovery.
- Owner-verified billing headroom, database disk/compute/IO limits and incremental-cost policy. A favorable pilot-size estimate is not a hard $0 billing certification.
- Explicit authorization naming hosted destination, privileges, bounded synthetic-only execution, cleanup, and later separate approvals for real NCAAF data, schedules, deployment and Windows sync.

`HOSTED_READY=false`; `MODEL_VALIDATED=false`; `HISTORICAL_GUARD_UNEXPLAINED` preserved.
