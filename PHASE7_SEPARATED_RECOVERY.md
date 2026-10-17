# Phase 7B — simulated separate-directory restore (review only)

This **offline synthetic** test copies a disposable SQLite fixture between separate directories, verifies SHA256 and cold read-only SQLite integrity, rejects overwrite, detects tampering and missing remote objects. It does **not** contact an external provider, use real NCAAF state, encrypt a backup, set an operational key, or test independent physical failure domains. No outputs are committed or uploaded.

Run: `python -I -m unittest discover -s tests -v`; then `python -I scripts/security_preflight.py`. The approved manual workflow is unchanged. It will run the added Python test if this PR is separately merged and explicitly manually dispatched later.

## Remaining actual off-host gates
- Choose provider, independent custody/account/ACL, cost and retention.
- Review data sensitivity and real encryption/key escrow design.
- Authorize a dedicated **synthetic-only** off-host test first, in a future separate action.
- Independently verify download, ciphertext authentication, cold SQLite restore, deleted/lost objects, wrong key, and rollback across separate machines/accounts.
- Obtain separate explicit approval before transferring any operational NCAAF data, creating secrets, releases, hosted schedules, dashboards or production changes.

`HOSTED_READY=false`, `MODEL_VALIDATED=false`, `BACKUP_PUBLICATION_AUTHORIZED=false`.
