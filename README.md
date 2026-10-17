# NCAAF Observer — Safe Bootstrap

**STATUS: PREPARATION ONLY — NO HOSTED ACTIVATION**

Dedicated public repository for a future isolated NCAAF observer. Source: [Sports Edge Hub PR #21](https://github.com/jlebronmarty-netizen/sports-edge-hub/pull/21), Phase 5 baseline `55c99d359f833494d619c46014d5b8c431b4e7d9`.

This repository contains NO event data, forecasts, SQLite databases, backups (encrypted or otherwise), private keys, credentials, active GitHub Actions workflows or recurring schedules.

## Current authorization
- Repository creation and safe documentation/configuration preparation.
- Isolated **offline, synthetic** manual tests only.
- No upload of raw captures, forecasts, release assets or backups.
- No hosted job accessing real data, dashboard publication, external notification, production changes, or scheduled collection.

## Preconditions for any hosted manual job
Review GitHub Actions permissions, contributor ACLs, default branch protections, usage policy and runner quota; select backup encryption key custodians and two escrow locations; specify external backup destination, retention and costs; explicitly approve source/runtime and scope. Test with synthetic inputs first. Owner approval is required *before* any data transfer or secret setup.

Templates remain `.disabled` and are NOT installed under `.github/workflows/`.

See [SECURITY_REVIEW.md](SECURITY_REVIEW.md). Full release gates: [Phase 5 checklist](https://github.com/jlebronmarty-netizen/sports-edge-hub/blob/55c99d359f833494d619c46014d5b8c431b4e7d9/research/ncaaf-phase5/RELEASE_CHECKLIST.md).

## Offline security checkpoint (2026-10-17)

`SECURITY_PREPARATION_COMPLETE` describes accessible preparation checks only.
`HOSTED_READY=false`; `MODEL_VALIDATED=false`; `ACTIONS_ENABLED=false`;
`BACKUP_PUBLICATION_AUTHORIZED=false`.

Run `python -I -m unittest discover -s tests -v`, then
`python -I scripts/security_preflight.py`. Both are offline and use synthetic fixtures.
The workflow template is strict JSON (a YAML subset), deliberately outside
`.github/workflows/`. Do not install or run it under the current authorization.

See [security findings](SECURITY_REVIEW.md), [workflow review](WORKFLOW_REVIEW.md),
[restart instructions](RESTART.md), and [observed API metadata](audit/github-observations.json).
Exact published commit is the draft PR head and `git rev-parse HEAD`; the checkpoint
records the original baseline rather than embedding a self-referential final hash.
