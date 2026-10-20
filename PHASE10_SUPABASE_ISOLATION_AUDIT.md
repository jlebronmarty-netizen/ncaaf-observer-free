# Phase 10 — Supabase isolation and capacity gates (READ-ONLY AUDIT)

Status: REVIEW ONLY. Observed 2026-10-17 via connected project metadata and SELECT-only catalog queries. No migrations, permissions, credentials, deployments, schedules, backups, real NCAAF imports or production changes.

## Verified scope
- Observer main baseline: `89566fa7274175b111dfafaea83240b8f898f21c`.
- Existing accessible Supabase project: **Pick Analyzer** `ynuocvexviorgdjrfthw` (`us-east-2`), status ACTIVE_HEALTHY. Another accessible project **smart-shopping-app** is unrelated and must not be used.
- Pick Analyzer Postgres database size: **14,767,074,451 bytes** at audit time (dynamic value, not quota headroom).
- Public schema contains **387 ordinary/partitioned tables**, **130 without row-level security**. The absence of RLS on arbitrary legacy tables does not itself establish exposure; effective grants and API exposure need independent auditing.
- Two detected `public` schema SECURITY DEFINER functions executable by PUBLIC (verify effective grants before change):
  - `sync_mlb_pitcher_win_forward_starter_history_v1(p_target_date date)`
  - `sync_mlb_pitcher_win_forward_team_history_v1(p_target_date date)`
- No changes to these functions or other sports are authorized.
- Observer currently has no approved durable hosted authority; the Phase 9C bridge is synthetic-only. Neither existing Pro subscription nor database size proves free billing headroom.

## Minimum isolation acceptance design — not executable SQL
1. Seek billing-owner evidence: plan and actual budget, usage and project compute tier, IO, egress, storage, bandwidth and allowed incremental cost. Application-side caps are not a hard provider spending limit.
2. Inventory existing public/anonymous/authenticated service grants, API-exposed schemas, RLS, policies, unsafe DEFINER functions and other-sport dependencies *read only*. Review the two MLB functions' definitions/search_path/owners and invokers without changing them.
3. Only after separate owner approval, choose a fresh private synthetic NCAAF namespace inaccessible to existing exposed API roles by default. Schema separation alone is not sufficient security.
4. Design transaction-level writer fencing/CAS and append-only facts/checkpoints, plus private content-addressed objects. No service role in public frontend or public GitHub job; verify writer/reader/recovery/cleanup roles with negative permission tests in a disposable, isolated fixture.
5. Specify signed/authenticated durable checkpoint continuity, encrypted content with externally held keys, verified restore from fresh independent host, quotas and cleanup before any cloud pilot.
6. Never use production objects or reuse MLB/NBA schemas for synthetic pilot convenience. Preserve immutable NCAAF PPG/Ridge local forecasts and settlement exactly.
7. Prefer an isolated provider-neutral synthetic-only permissions test first; do not apply proposed SQL migrations to production during research.

## Gates for any later hosted activation
- Approved isolated destination and precise role matrix.
- Verified cost/budget/usage headroom and limits; zero incremental dollars must be substantiated, not inferred.
- Reviewed provider-specific transport/bridge and encryption/key custody, fenced publication, durable trusted checkpoint floor.
- Independent hosted recoverability, cleanup authority, source and bytes cap, exact owner approval for one bounded synthetic-only run.
- Explicit separate approval for real-data migration, recurring schedules, deployments and Windows startup tasks.

No actual NCAAF state has been transferred. Existing workflow remains manual-only. `HOSTED_READY=false`, `MODEL_VALIDATED=false`, `HISTORICAL_GUARD_UNEXPLAINED` preserved.
