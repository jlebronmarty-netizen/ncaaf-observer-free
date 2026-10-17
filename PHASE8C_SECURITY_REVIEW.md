# Phase 8C independent synthetic hardening

HOSTED_READY=false; MODEL_VALIDATED=false. No authentic records, frozen research, credentials, hosted resources or production systems were accessed or changed.

## Dependency and reproduction

New branch `research/phase8c-security-hardening` starts at exact PR #10 head `27ac1de2d7cb5a70d548a46bfd746dd003771ddd`, targeting `research/phase8b-synthetic-state`. Dependency: PR #9 (`94f2d9f7af92544282a1002fd198c0fcd582639e`) -> PR #10 -> this draft. Neither dependency is modified or merged. NCAAF source reference remains `55c99d359f833494d619c46014d5b8c431b4e7d9`.

Run Python 3.13: `python -I -m unittest discover -s tests -v`, `python -I scripts/security_preflight.py`, and Node 24: `node tests/synthetic_crypto_check.mjs`. `python -I scripts/synthetic_state_v1.py` runs a disposable synthetic demo. No network is used by these commands.

## Findings and corrections

Initial unchanged suite: 53 tests PASS; scanner PASS; Node AES-GCM PASS. Final suite: 78 tests (25 added), scanner and Node must pass before publication.

Reproduced defects before corrections:

1. Publication helper accepted paths outside the marked disposable workspace. All read/write destinations now validate ownership, components and file type.
2. Hard-linked markers/cache files and Windows directory junctions escaped the intended boundary. Reject reparse points, symlinks, special files and multiply-linked regular files; compare file identities around bounded reads.
3. Deep JSON and huge sequence watermarks could exhaust resources or raise uncontrolled overflow. Bound payload size, depth, node count, changes, generation count, SQLite size and aggregate transfer; reject noncanonical/duplicate-key JSON. No archive decompression is supported.
4. Reopening an unrelated SQLite file lacked synthetic namespace verification. Require application_id and immutable synthetic identity; missing DBs never silently become new authorities.
5. Malformed remote-head fields could reach the checkpoint before rejection. Validate exact identity schema first.
6. Writer reused parent metadata without verifying its object hash. Verify before reuse and refuse generation-limit overflow.
7. A logically corrupted forecast body could pass SQLite integrity and reach settlement. Verify its stored SHA256 and immutable identity before use.

Strict file allowlist gains only this document and the new regression test. Existing import assertion gains only stdlib `stat` for filesystem metadata checks. Workflow, disabled template and Node crypto test remain byte-identical Git blobs to PR #10. No security assertion was removed.

## Regression evidence

Tests exercise real disposable Windows junctions/hard links; hostile paths including ADS/reserved names; oversized/deep/noncanonical manifests; invalid heads/parents/ordering; resource limits; unrelated/corrupt SQLite; concurrent writers, leases, CAS and backup clients; duplicate settlements; clock rollback; immutable retained versions; injected permission denial, partial writes and ENOSPC; interrupted publication and restart with stale lock; cold restoration.

Windows-offline scenarios use controlled simulated gaps of 1, 3, 7 and 14 days. Hosted synthetic execution continues without the client. Catch-up downloads exactly the missing generations and leaves every previously verified object unchanged. These are synthetic observations, not real elapsed outages.

Contract golden SHA256 values from the unchanged PR #10 synthetic generator: initial batch `89569e7295490faf48207be46afffb1f7e60072aa0e053fa8680fa7cd23fe0bb`; final batch `b210a85b87b4293d3fbb63a5c8f5798a0cfcf4c0ab4063df959d5b4496c93078`. Model labels retain fake `SIMULATED_RULES_V1` artifacts; no real PPG/Ridge inference or import occurs. Synthetic namespace checks refuse authentic-shaped records. An unrelated external importer remains outside this prototype's control.

## Performance and retention

Measurements are local Windows/Python synthetic runs, not hosted capacity estimates. Exact final timings, source hashes and sizes are in the local `performance-final.json` receipt. For 20/100 fake events (40/200 generations), retained objects are 83,290/415,572 bytes, retained version pointers 8,867/8,891 bytes, restored SQLite 131,072/516,096 bytes. Hardening adds metadata/hash checks and measurable latency; previous measurements are preserved rather than replaced.

Offline 1/3/7/14-day cases downloaded 4,156/12,514/29,236/58,616 missing bytes; retained object bytes 7,493/15,851/32,573/61,953. Single preliminary catch-up times were 0.21/0.43/0.84/1.56 seconds. These are synthetic measurements, not real infrastructure promises. Retention preserves baseline plus newest K checkpoint pointers but all parent objects remain necessary. Growth is linear; no compaction or globally bounded calendar retention is implemented. Bounded sessions (16 MiB), 10,000 generations and other limits fail closed and eventually require a separately reviewed retention design.

## Remaining limitations and authorization gates

Portable lstat/fstat checks are not a complete hostile same-user/admin TOCTOU sandbox. Private directory ACLs and native platform review remain necessary; no Windows handle-relative race guarantee is claimed. Marker/application_id identify schema, not cryptographic authenticity. Fake snapshots are plaintext; no provider IAM, TLS, external CAS, signing or integrated AEAD is validated. The independent Node test verifies only the AES-GCM primitive contract.

Disk/permission faults are injected. Restart tests use exception boundaries and fresh instances, not OS power-loss or real process-kill durability. A stale backup lock blocks until explicit reviewed cleanup; there is no automatic unsafe takeover. Cloud persistence, independent-host recovery, website integration, credentials, resource budgets, alerting and production scheduling remain unverified and unauthorized. No provider cost or zero-cost guarantee is established here.

Restart: verify branch and exact commit, rerun all three offline checks, inspect the immutable local receipts, and resume only a newly authorized synthetic review. Never point this prototype at authentic ledgers. Do not activate hosting, uploads, schedules, keys or migrations without separate owner authorization.

Evidence directory: `C:/Users/jlebr/sports-edge-hub/research/ncaaf-observer-phase8c-20261017`. Contains baseline/final logs, pre-fix regression failures, performance measurements and hash manifests. An incidental test-authoring BOM encoding error was preserved and corrected by removing only the known erroneous prefix; it was unrelated to data integrity and no assertions changed. Exact published commit and evidence hashes accompany the draft PR receipt, avoiding a self-referential commit hash in this file.
