# Owner review checklist ? no activation authorized

- [ ] Review the exact draft PR head, baseline blob inventory and all changed files.
- [ ] Confirm main still has the active Protect Main ruleset and decide whether zero
  required approvals is sufficient; this preparation does not change the ruleset.
- [ ] Independently inspect Codex and Vercel installation scopes and granted permissions;
  the API403 is an unresolved observability limit, not PASS.
- [ ] Reconfirm Actions disabled, no secrets, no workflows/runs/releases/deployments.
- [ ] Review pinned checkout SHA `11bd71901bbe5b1630ceea73d27597364c9af683` and
  `persist-credentials:false`; GitHub checkout network access is expected, provider
  network access is absent. No account tokens or operational credentials are supplied.
- [ ] Review the strict JSON/YAML disabled template: workflow_dispatch only,
  contents:read at both levels, windows-2022, 10-minute timeout, no expressions,
  no credential/runtime installation steps, no writes/uploads/cache/deploy/publication.
- [ ] Inspect the scanner/test Python source, not only its successful test summary.
- [ ] Re-run the offline suite and scanner from RESTART.md. Compare inventory hashes.
- [ ] Keep all authentic data, research results, archives, keys and production outside
  this repository; no publication permission is implied by approval of this PR.

## Separate future authorization

Merging this draft PR is not authorized. Enabling Actions, installing the disabled
workflow, running even a synthetic hosted test, and changing repository security
settings each require explicit owner authorization. Before any future synthetic hosted
run, recheck exact source SHA/settings, runner availability, permissions, timeout and
no operational inputs; inspect actual logs and effective permissions afterward.
Hosted execution remains PENDING. Real ingestion, secrets/key generation, archive
upload, releases, dashboards/Pages, schedules, external alerts and production actions
require separate scoped authorization and the original Phase 5 release gates.

No GitHub App/account permissions were narrowed or expanded here.
