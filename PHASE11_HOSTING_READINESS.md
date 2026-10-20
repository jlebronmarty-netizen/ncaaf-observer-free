# Phase 11 — hosted capacity, security and cost gates (RESEARCH ONLY)

Source baseline: observer main `a3c8f2584fd4f7195a4e2dc7a666c3f86ebeea3c`.
No production modifications, migrations, credentials, schedules, deployments or uploads authorized.

## Current read-only observations — 2026-10-20

- Accessible Supabase projects: Pick Analyzer (`ynuocvexviorgdjrfthw`, us-east-2), smart-shopping-app (unrelated, out of scope). Pick Analyzer status ACTIVE_HEALTHY; PostgreSQL 17.
- Via read-only PostgreSQL catalog query, Pick Analyzer database `pg_database_size` = **14,817,102,995 bytes**; public tables = **387**, public tables with RLS disabled = **130**. This is *not* a direct measure of plan storage remaining, allocated compute, IO, egress, billing or security exposure.
- Existing Phase 10 audit identified two MLB `SECURITY DEFINER` functions executable by PUBLIC. No permissions were changed. Effective attack surface, API-exposed schema configuration and dependencies require separate owner review.
- Vercel `sports-edge-hub` project metadata reported Node 24.x and most recent deployment readyState READY. That is not confirmation of NCAAF routes, allocated budget or end-to-end service health.
- Supabase billing/usage and precise spend caps are not exposed by these read-only tools. An existing paid subscription does not establish zero incremental billing. No account invoice or sensitive data accessed.

## Decision gates before any synthetic hosted pilot

| Gate | Required evidence | Current status |
|---|---|---|
| Namespace isolation | Explicit private schema, default revoked permissions, effective API-exposed schemas and role matrix, denial tests for all other sports, security-definer access review | BLOCKED |
| Durable authority | Transactional immutable generation CAS, authenticated checkpoint floor, provider-specific object/metadata atomicity or fail-closed bridge | NOT IMPLEMENTED HOSTED |
| Authentication/encryption | Least-privilege read/write/recovery principals, short-lived secret custody, AEAD and origin verification with key rotation and revocation plan | BLOCKED |
| Zero incremental cost | Owner-provided redacted plan/Usage/Billing, current allocations and actual headroom, spend-control limitations; no surprise compute or add-ons | UNVERIFIED |
| Runner execution | Existing standard GitHub hosted manual runner limits, access policy, no new schedules and isolated non-production execution | DESIGN ONLY |
| Recovery | Fresh independent host validates decrypted synthetic committed state, negative controls, immutable records and authorized cleanup | NOT TESTED HOSTED |
| PC backup | Pull-only encrypted snapshots when online with bounded retention; no Windows task yet | LOCAL SYNTHETIC ONLY |

## Safest next action

1. Gather redacted **billing owner** screenshots or approved read-only reports of Supabase plan, Usage, spend cap state, database/compute/IO/egress quotas; and verify Vercel project spending/capacity.
2. Gather precise Supabase Data API exposed schema settings and effective object/function grants in **read-only mode**. Do not expose keys, billing identity, card numbers or credentials.
3. Produce a limited, provider-neutral synthetic permission/transport design and review package without changing shared database.
4. Choose an exact isolated destination only after the above facts support the budget and security gates. Never silently use Pick Analyzer or create a paid project.
5. Separately authorize one bounded synthetic-only pilot and cleanup. Data migration, hosted schedules, production changes, Windows synchronization and operational secret creation remain separately gated.

`HOSTED_READY=false`; `MODEL_VALIDATED=false`; `HISTORICAL_GUARD_UNEXPLAINED` remains on record.
