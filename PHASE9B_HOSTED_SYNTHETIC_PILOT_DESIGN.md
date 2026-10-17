# Phase 9B: hosted synthetic-only pilot technical design

DESIGN ONLY. No pilot, resources, deployment, credential, database migration, transfers or schedules are authorized or implemented. HOSTED_READY=false; MODEL_VALIDATED=false; HISTORICAL_GUARD_UNEXPLAINED remains preserved.

## Verified source baseline and evidence limits

PR12 was squash-integrated as f956029ca1064d8e1e8754d76f54bd482706912e, tree268243c0c4318a4e112023e43e4a1a27bce476b7. Exact reviewed PR12 head0df0d422c920f7c165ef46330fff0f0668074729 passed89 tests, scanner and Node AES-GCM in a clean checkout. Source integration is not hosted verification. Existing manual workflow/template remain unchanged. Real PPG/Ridge source reference55c99d359f833494d619c46014d5b8c431b4e7d9 and actual records are outside this pilot.

Earlier Phase8B metadata recorded Supabase Pro, about14.76GB database/387public tables/one bucket and Vercel Next.js/Node24. Those are dated aggregate observations, not a fresh account audit or proof of free headroom. No account/database rows, invoices, environment variables or production configuration were accessed in this design task. Actual plan/region/permissions/unused quotas and spend controls must be rechecked by the billing owner before choosing a destination.

## Capability comparison and provisional selection

| Option | Useful existing capability | Missing proof / risk | Decision |
|---|---|---|---|
| Existing Supabase project | Durable Postgres transactions and private Storage with policy controls | Shared compute/IO/egress, schema isolation, grants, quotas and billable headroom unproven; schema is not physical resource isolation | Conditional durable backend candidate only after owner isolation/budget evidence; no production schema changes now |
| Existing Vercel project | Request compute/website platform | SQLite filesystem is not durable authority; production coupling, Python runtime support, authentication and plan limits unverified | Do not attach pilot routes to existing production; separately approved isolated preview only if no added cost and no shared side effects |
| Existing public GitHub standard runners | Manually invoked independent disposable execution; source pinned to reviewed commit | Runner disk is not durable; current workflow intentionally has no provider access or uploads | Preferred future bounded manual compute, subject to separate workflow/security approval; leave existing workflow untouched |
| Windows-only worker | Existing local synthetic tests and pull prototype | Owner PC may be off; cannot meet independent hosted execution | Keep as optional pull-only observer, never authority |
| New external project/storage | Stronger isolation potentially possible | No existing eligibility, account, billing or retention proof | Not selected; no new resources or subscriptions proposed for activation |

Provisional architecture: two separately authorized one-shot standard hosted runner sessions, private durable transactional metadata plus immutable content-addressed synthetic objects in a vetted existing store. A third independent read identity/session validates recovery. There is NO currently approved destination; if shared resource safety cannot be proven, stop rather than provisioning a paid isolated project or silently using production.

Phase9A Reader consumes a marked SQLite authority, not Postgres/remote Storage. A hosted transport/transaction bridge or verified materialization step is still missing. Do not point the existing reader at a copied live SQLite file. Proposed bridge reconstructs a bounded synthetic authority from committed immutable objects in fresh scratch, verifies complete journal/facts/namespace, closes writer, then exposes read-only projection. This bridge requires implementation and independent tests before a pilot. Existing frozen fact IDs, synthetic FORMAT, fencing and settlement contracts must remain byte-identical. No new model fitting or authentic forecast import.

## Publication, authorization and separation contracts

Proposed writer role can append only the approved synthetic namespace and atomically CAS its committed head using owner/fencing epoch/expected generation inside a transaction. Publish object first with no-overwrite create; verify digest/size; then commit metadata and head atomically. Interrupted orphan objects never become visible. A stale writer cannot publish by changing an object alone. Metadata and object store must not be assumed to share a transaction: failure handling and committed-object durability require explicit proof.

Reader identity can select committed checkpoint metadata and fetch only referenced synthetic objects, not update heads, acquire leases, list other namespaces or read other sports. Restore/verifier identity is independently read-only. Cleanup identity is distinct and unavailable during normal writer/reader runs. No service-role/project-owner key in frontend or public job. Prefer short-lived federated identities if actually supported; otherwise separately approve scoped expiring secrets with revocation/key custody. No credentials are created in this design.

For a shared Supabase destination, use unexposed synthetic-only namespace, explicit minimal grants and RLS defense in depth; private Storage policies restrict exact bucket/prefix and operations. Public/authenticated role alone is insufficient isolation. Avoid service-role bypass, public buckets and default function grants. Browser only sees bounded sanitized projections; read credentials never appear in responses. Return generic errors without paths/tokens/raw traces. Trust a signed/authenticated head and protect the caller checkpoint floor in durable storage; SHA256 alone is not authentication. Bind encrypted object metadata to schema/namespace/generation/digest, enforce fresh nonces, authenticate before decode. Existing Node crypto tests do not implement these integrations.

## Bounded future acceptance protocol (requires separate approval)

1. Owner records exact source SHA, provider account/region/namespace, budget and identity matrix; review all new code/workflow separately. No existing manual workflow changes. No recurring trigger.
2. Approve at most two writer runs, one independent fresh-host restore and one offline catch-up session, within24hours. Proposed ceilings:20fake events/40generations,100requests,16MiB stored,32MiB transfer,20runner-minutes total. These are engineering limits, NOT provider quota facts or a spending guarantee. Disable retries after two bounded failures.
3. RunA creates only clearly marked synthetic facts; store original identities, clocks, artifact SIMULATED_RULES_V1 labels, committed receipts and hashes. Dispose runner. Keep Windows disconnected; no Windows task installation.
4. RunB on a fresh runner must recover remote committed state, preserve old bytes, continue fenced generations and serve deterministic projection. Capture independent run IDs/UTC/provider resource identities redacted to safe receipts. No outcome is counted as authentic prospective success.
5. Fresh read-only verifier rejects write attempts and cross-namespace reads. Test stale lease/CAS, wrong identity/key, altered/missing objects, interrupted publication, checkpoint replay, restart with empty scratch, clock rollback and max-age failure. Caller persisted floor must survive runner replacement; failure to retrieve it causes abstention, never bootstrap reset.
6. Independent cold restore verifies all parent hashes, full SQLite integrity and exact fact/journal parity; simulate multiple missed Windows sessions and download only missing generations. Two sessions from one physical provider are not proof against provider-wide loss; independent-host retrieval is distinct from independent-storage disaster recovery.
7. Stop on source/schema mismatch, quota alarm, side effects, any write by reader or unexpected charge. Retain bounded safe receipts, revoke scoped credentials after review and delete only the exact pilot namespace with separately approved cleanup identity. Verify absent objects, revoked access and no running jobs. Do not delete shared buckets/tables or roll back production. Leave original source/frozen evidence intact.

## Durability, retention and costs

Proposed pilot RPO: last acknowledged committed generation, RTO target10minutes for this bounded fake dataset; both unmeasured. A provider acknowledgement alone is not verified recovery. Retain every ancestor needed by40generations until the owner reviews restore receipts; proposed expiry7days, followed by approved namespace cleanup. No silent compaction. Object versioning/backup availability must be checked; Windows copies alone do not protect against provider loss while offline. Future independent off-host encrypted recovery needs a separately approved destination; no cloud transfer is authorized now.

Phase8 measurements:100fake events produced415572object bytes and516096restored SQLite bytes; local catch-up10.80s/restore0.73s. These are synthetic local observations, not hosted capacity. Phase9A currently full-replays at most10000facts/16MiB and returns at most50forecasts/64KiB. Measure request count, object/DB/index/encryption overhead, peak memory, runner time, egress and retained versions during any later pilot. Reject before budget exhaustion, never upgrade automatically.

Zero incremental cost requires billing-owner evidence that ALL usage fits already-paid unused allowances, no extra compute/project/branching/add-ons, compatible runner eligibility, headroom reserved away from other sports, and effective provider controls plus app ceilings. No such evidence is established. Supabase Spend Cap excludes compute and certain opted-in items; it is not a universal dollar budget. Vercel spend controls may pause availability and do not establish separate shared-project isolation. Public standard Actions compute eligibility does not make durable storage/egress/artifacts free. A strict universal $0 cap cannot currently be certified. If cost safety is unavailable, retain local-only status.

## Official policy references (reviewed2026-10-17)

- [Supabase cost control](https://supabase.com/docs/guides/platform/cost-control): covered usage can stop at quota; compute and listed add-ons are excluded. Current actual cap/account headroom unknown.
- [Storage access control](https://supabase.com/docs/guides/storage/security/access-control): object permissions require deliberate policies; do not use service-key bypass as reader isolation.
- [Supabase changelog](https://supabase.com/changelog): reviewed relevant TLS deprecation; HTTP clients must support modern TLS. The markdown index fetch failed content-type handling, so HTML was reviewed. No SDK/schema implementation in this PR.
- [Vercel runtimes](https://vercel.com/docs/functions/runtimes): scratch filesystem is not durable state; external verified persistence is required.
- [Vercel spend management](https://vercel.com/docs/spend-management): review actual controls and plan before any pilot; no account settings changed.
- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions) and [hosted runners](https://docs.github.com/en/actions/concepts/runners/github-hosted-runners): standard public runner billing and disposable runtime do not imply free durable authority.

## Decision / restart checkpoint

DESIGN_PREPARED; PILOT_BLOCKED_PENDING_AUTHORIZATION_AND_ENGINEERING. Missing: destination/cost/isolation proof, authenticated transport and durable floor, reviewed bridge, credentials custody, independent recovery and cleanup tests. Owner must authorize precise hosted synthetic-only scope after design/code review. This draft grants none of those permissions. No merge requested. Restart by verifying PR head/base and receipt hashes, rerun89tests/scanner/Node, then address design blockers without changing real NCAAF or other sports. HOSTED_READY=false; MODEL_VALIDATED=false.
