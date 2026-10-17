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
