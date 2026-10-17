# Phase 8 proposal — hosted NCAAF operations with opportunistic PC backup (NOT ACTIVATED)

Owner's PC is generally powered on for several hours daily, but is **not an always-on worker**. The website and prediction/settlement services must remain available while the PC is off. This is a proposed architectural pivot, not evidence of hosted readiness.

## Intended separation

- GitHub: versioned source and manual/offline testing; the current public observer repository remains synthetic-only.
- Hosted durable state: **reuse an existing vetted database**, preferably the existing Supabase project **only if** owner-approved environment, service quotas, data isolation, secure credentials and schema compatibility pass independent checks. Do not assume a database has been deployed or a prediction ingestion path exists.
- Hosted compute: inspect existing GitHub Actions and Vercel capabilities/quotas and current ingestion/settlement dependencies; specify reliable idempotent execution, frozen as-of forecasts, deduplication, no secrets in public workflows, failure notification and verifiable schedules. Do not enable any schedules now.
- Website: a hosted frontend reading the durable state via least-privilege APIs. Public endpoints must not expose write credentials.
- Local Windows PC: **pull-only, versioned, authenticated** backup of a point-in-time consistent hosted snapshot at Windows logon and optionally at bounded intervals when online. The backup must not run the website or prediction engine. Backups must fail closed and not silently overwrite old versions.
- Restore: a separate owner-approved procedure, never automatic upward sync. A PC backup may be stale while it is off; record last verified checkpoint, source sequence/watermark and SHA256 to measure recovery gap.

## Before implementation — read-only inventory
1. Verify real NCAAF production/experimental source of truth and environment (where forecasts and settlements currently live), remaining quota and jurisdiction. Preserve PPG/Ridge immutable ledgers, as-of and frozen model artifacts.
2. Verify existing Supabase schema, migrations, RLS, backup/export method, API scopes and atomic snapshot capability. Do not rely on copying active SQLite database files.
3. Inventory existing Vercel/GitHub cron schedules, activation state, permissions and actual costs. Do not add schedule or broad credentials.
4. Inspect Windows startup integration options, local free disk space, Windows volume ACL, BitLocker/device encryption availability and full backup lifecycle. Never commit machine/user paths or tokens.
5. Specify full/delta backup, finite retention (e.g. proposed 7 daily + 4 weekly subject to sizing), copy verification, partial-file cleanup, disk-full/connection-failure behavior, redaction, minimum restore test and corruption handling.
6. Compare a PC-only last-known-good backup with an independent off-host backup for disaster tolerance; do **not** falsely present PC copies as disaster-proof or current while offline.

## Safe next steps
- Stage 8A: produce read-only inventory evidence from existing infrastructure and estimated bytes/day; no production mutations.
- Stage 8B: design a synthetic Windows scheduled-at-login pull-only backup fixture, without persistent tokens or automatic registration.
- Stage 8C: run synthetic local cold-restore/integrity failures and log safe receipts.
- Stage 8D: seek separate owner approval before implementing real read access, Windows Task Scheduler activation, any hosted schedules, or hosted schema changes.

STRICT_ZERO: leverage already-existing free eligibility, but verify provider limits and avoid new billable resources. Public repository and manual workflow remain unchanged. The still-open PR #8 is a **superseded research alternative** for optional external cloud backup; do not merge it merely as part of this pivot.

Current flags remain HOSTED_READY=false, MODEL_VALIDATED=false and BACKUP_PUBLICATION_AUTHORIZED=false.
