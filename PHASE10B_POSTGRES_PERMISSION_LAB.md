# Phase10B disposable PostgreSQL permission laboratory

POSTGRES_EXECUTION=BLOCKED_MISSING_LOCAL_RUNTIME. This is a NON-EXECUTED fixture, not PostgreSQL security certification. HOSTED_READY=false; MODEL_VALIDATED=false; HISTORICAL_GUARD_UNEXPLAINED preserved.

## Scope and source

Separate branch research/phase10b-offline-postgres-permission-lab based on main89566fa7274175b111dfafaea83240b8f898f21c. PR15 reference723ed23d072e5d1d3df5304fa78a0935a5245512 remains untouched/unmerged; this branch does not incorporate its document or scanner change. No Supabase calls, hosted services, other-sport source, real function definitions/rows, production keys or operational records are used. All SQL/functions below are newly authored obvious canaries, not copies of existing MLB routines.

Runtime discovery: psql/postgres/initdb/pg_ctl/docker/podman absent from PATH. Checked C:/Program Files/PostgreSQL, C:/Program Files/Docker/Docker/resources/bin, C:/PostgreSQL and C:/pgsql: absent. No install, service registration, package download or container pull attempted. This does not prove binaries exist nowhere; it establishes no discovered usable isolated runtime. Current PostgreSQL results are NOT RUN.

Artifacts: templates/phase10b-permission-lab.sql.disabled, tests/test_postgres_lab_contract.py. SQL is deliberately disabled and not loaded by any Python test/workflow. The new tests are static contract assertions only. Original109Python tests continue to exercise the existing offline SQLite synthetic systems; they do not execute this PostgreSQL lab. Existing workflow/template/simulator/adapter/bridge unchanged. Scanner adds only this document, disabled SQL fixture and static test paths.

## Proposed runtime and safe reproduction (NOT EXECUTED)

Prerequisite: approved local PostgreSQL17 binaries initdb/pg_ctl/createdb/psql, private disposable OS account or equivalent isolated container network, no mounted credentials/data and no existing database connection. Use a newly created empty temporary directory whose canonical path is confirmed under the system temp directory; use a new ephemeral port verified unused. Never use an existing cluster, PGDATA, DSN, .pgpass or Supabase address. Clear inherited PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD/PGSERVICE/PGSERVICEFILE/PGPASSFILE/PGOPTIONS in the child environment only; do not print their values. This is a local preparation prerequisite, not authorization to install software or change persistent settings.

Illustrative commands require substitution of validated temp path/unused port and must NOT be run now:

```
initdb -D <NEW_PRIVATE_TEMP>/data -U synthetic_lab_admin --auth=trust
pg_ctl -D <NEW_PRIVATE_TEMP>/data -l <NEW_PRIVATE_TEMP>/server.log -o "-c listen_addresses=127.0.0.1 -p <UNUSED_LOCAL_PORT>" -w start
createdb -h 127.0.0.1 -p <UNUSED_LOCAL_PORT> -U synthetic_lab_admin synthetic_permission_lab
psql -X -h 127.0.0.1 -p <UNUSED_LOCAL_PORT> -U synthetic_lab_admin -d synthetic_permission_lab -v ON_ERROR_STOP=1 -f templates/phase10b-permission-lab.sql.disabled
pg_ctl -D <NEW_PRIVATE_TEMP>/data -m fast -w stop
```

Trust authentication is ONLY for a disposable isolated local namespace; other local users could otherwise impersonate the lab admin. Do not expose host port beyond loopback, reuse an existing machine/service or call this operational authentication. No passwords/operational credentials are created by the fixture. Windows local-system execution/interactive shared host and root initdb limitations must be reviewed before use. An isolated runtime with no external network is preferred; no image pull is authorized by this document.

Harness must capture binary version, source SHA256, admin identity/port/cluster location and all psql stdout/stderr/exit codes without secrets. Database name and absence of ncaaf_lab_* roles are mandatory guards; SQL refuses a collision. Those guards are not permission to connect to an existing database renamed to match. Fixtures run in one transaction with ON_ERROR_STOP and end in ROLLBACK, so successful execution leaves no lab roles/schemas/rows. On failure, psql exits and transaction rolls back. In a finally block, stop only this newly created cluster, verify no server process/listener remains, and retain logs outside its directory. Before any recursive deletion, resolve the target and prove it is exactly the recorded newly created temp cluster below temp root; never delete a computed unverified path. Prefer preserve-on-failure with STOPPED checkpoint and a separately reviewed cleanup.

A future executor must not accept arbitrary connection URLs, remote hosts or provider credentials. No automated launcher or runnable hosted workflow is added in this PR. The existing manual workflow runs only the Python suites; it will not run SQL or start PostgreSQL.

## Synthetic schema / role design

Five NOLOGIN/NOSUPERUSER/NOCREATEDB/NOCREATEROLE/NOINHERIT/NOBYPASSRLS fixture roles: owner, writer, reader, recovery, cleanup, all prefixed ncaaf_lab_. Admin uses SET ROLE for assertions; this tests privilege execution contexts, NOT login authentication or credential theft. A future multi-connection test needs explicit separate identities, not shared superuser assumptions.

synthetic_mlb.canary is a private one-row fake counter. Its newly authored bump_canary SECURITY DEFINER deliberately starts with default PUBLIC execution and PUBLIC schema USAGE to demonstrate the risk. Table owner bypasses its own non-FORCE RLS even though the owner is NOBYPASSRLS. Writer's direct SELECT is denied while the definer call increments the counter. Only in this disposable fixture is PUBLIC execution then revoked; no actual MLB function is accessed or modified.

An owner-level global ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC precedes NCAAF function creation. A per-schema revoke cannot undo PostgreSQL global default EXECUTE grants; the global change here affects only the fresh synthetic owner, never real defaults. Tables have no PUBLIC access. Explicit writer RPC/reader table grants follow. Fixed search_path=pg_catalog,pg_temp and qualified table names avoid temp-name shadowing in privileged routines; an explicit temporary-control-table probe verifies the intended behavior when eventually run.

synthetic_ncaaf has control (one fenced lease/generation row), forecasts (SYNTHETIC-* immutable ID and NCAAF_SYNTHETIC marker), and committed checkpoints (unique generation/forecast ID/fence). FORCED RLS and policies scope owner and reader/recovery access. UPDATE/DELETE triggers block immutable records even for the fixture owner/admin absent trigger disabling. Writer has no raw table access; only claim/publish EXECUTE. SELECT FOR UPDATE serializes control; expected fence, unexpired lease and generation CAS are checked inside one transaction. Duplicate immutable ID raises an error and rolls back, not an upsert. This is a toy privilege fixture, NOT a replacement Phase8/9 contract or an exact duplicate-retry implementation. Existing bridge's original contracts remain unchanged.

Cleanup can call only a non-destructive review receipt function, not delete forecasts or DROP schema. Actual cluster teardown belongs to the separate privileged harness after restore/test review. Production cleanup RPC remains a future reviewed capability, not claimed implemented here. synthetic_checks.expect_state is SECURITY INVOKER and executes negative statements as the selected low-privilege role; it asserts the precise SQLSTATE. The helper is deliberately lab-only and must never be deployed.

## Expected permission matrix ? ALL POSTGRES RESULTS UNEXECUTED

| Operation | Writer | Reader | Recovery | Cleanup |
|---|---|---|---|---|
| Raw forecast SELECT | deny | allow RLS-filtered | allow RLS-filtered | deny |
| Raw INSERT/UPDATE/DELETE | deny | deny | deny | deny |
| Claim lease / publish | allow fenced CAS | deny | deny | deny |
| Immutable ID overwrite / checkpoint rewrite | deny | deny | deny | deny |
| MLB canary SELECT or function after hardening | deny | deny | deny | deny |
| Create object / assume owner / create superuser | deny | deny | deny | deny |
| Catalog schema-name enumeration | visible names possible; no secrecy guarantee | same | same | same |
| Cleanup receipt only | deny | deny | deny | allow |
| Cluster destruction | not permitted | not permitted | not permitted | not permitted; harness only |

Explicit SQL assertions cover writer raw CRUD, reader raw mutation/publication/claim, recovery INSERT/UPDATE/DELETE/publication and cleanup SELECT/delete/publication; shared grants/defaults and function ACL checks cover other matrix entries. Do not label every matrix cell dynamically tested before a runtime run; expanded all-role Cartesian/independent-session tests remain a gate. Catalog namespace visibility is expected and tested as visible; object access denial is separate from schema-name hiding. PostgreSQL catalogs cannot be treated as a secret namespace mechanism.

## Failure / recovery controls and static verification

Assertions include baseline definer bypass/hardened denial, RLS exclusion probe inside a savepoint, immutable row/checkpoint guards, cross-sport ID marker, stale generation/fence, duplicate identity, privileged role creation/owner escalation, expired-lease takeover, interrupted publication rolled back to savepoint and valid fresh recovery. End-state row counts/generation verify partial publication never remains. Search-path probe publishes while a fake temp control table exists; original qualified authority changes, shadow table stays999, then savepoint rolls back the probe. No concurrent-session contention, OS crash, restart persistence or backup restore claim: none can be certified without runtime. Existing109tests independently cover SQLite bridge recovery, not PostgreSQL parity.

Five new Python tests inspect only fixture guards/names/defaults/negative assertions and absence of remote/credential commands. They do NOT parse/execute PostgreSQL syntax and are not a substitute for engine validation. Initial static check found fewer explicit denial cases than its required threshold; log preserved, recovery/cleanup denials added without weakening the assertion. Final exact counts/hashes are in the draft PR receipt. Run python -I -m unittest discover -s tests -v; python -I scripts/security_preflight.py; node tests/synthetic_crypto_check.mjs. Source and full logs retained locally under C:/Users/jlebr/sports-edge-hub/research/ncaaf-observer-phase10b-evidence-20261017.

Remaining prerequisites/approvals: approved isolated LOCAL PostgreSQL17 runtime provision (no automatic install), then execute exact fixture and capture engine SQLSTATE matrix; add independent-session lock/CAS tests, cold restart/restore and exhaustive role-negative tests after initial execution. Any shared-project permission hardening, real database connection, hosted pilot, credentials, production schema or schedule needs separate authorization. This fixture proves no actual Supabase isolation or $0billing headroom. PR15 is untouched; do not merge this draft as production readiness evidence. HOSTED_READY=false; MODEL_VALIDATED=false; HISTORICAL_GUARD_UNEXPLAINED preserved.

Official review references: https://www.postgresql.org/docs/17/sql-alterdefaultprivileges.html and https://www.postgresql.org/docs/17/sql-createfunction.html (consulted2026-10-17). Per-schema default revokes do not remove globally granted defaults; SECURITY DEFINER execution/search_path and PUBLIC execution need explicit review.
