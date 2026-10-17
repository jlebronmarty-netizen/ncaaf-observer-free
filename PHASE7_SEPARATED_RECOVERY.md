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

## Independent validation corrections

The original helper used exists-then-copy and left a destination behind after copy
interruption or SQLite/content validation failures. Regression tests first reproduced
four failures. Restore now hashes and cold-validates a private same-volume staging
copy, closes SQLite explicitly, and publishes with atomic no-clobber `os.link`.
Rejected or interrupted copies never occupy the destination; staging is cleaned on
success and failure. Unsupported hard-link filesystems fail closed without a copy
fallback. This is a local synthetic demonstration, not hardened adversarial storage
or crash-durable/off-host recovery.

Seven added regression methods cover stale existence/overwrite, non-SQLite content
with a matching hash, wrong SQLite contents, copy tampering, interrupted copies,
missing/tampered objects and unsupported atomic publication. Temporary fixture and
staging deletion are explicitly asserted. A first regression-fixture implementation
left SQLite connections open; explicit closure corrected that fixture without
weakening assertions. Both failed runs are retained in the local evidence directory.

Validation commands: full Python suite, security scanner and the unchanged existing
Node AES-GCM test. The existing manual GitHub Actions workflow and Node test are
unchanged. Exact final SHA and verification log hashes are published in PR #5;
full local evidence is in `research/ncaaf-observer-pr5-validation-20261017/` outside
this observer checkout. No authentic data, operational keys or off-host access used.
