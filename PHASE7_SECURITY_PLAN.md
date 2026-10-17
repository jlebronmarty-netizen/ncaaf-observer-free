# Phase 7 — synthetic encryption and off-host backup design (NOT ACTIVATED)

Status: REVIEW ONLY. No upload or external recovery was authorized.

## Local synthetic verification
Run `node tests/synthetic_crypto_check.mjs`. Uses Node built-in crypto and assert only, AES-256-GCM with fresh one-time random in-memory key and nonce. Verifies correct roundtrip, SHA256 payload parity, and rejection of altered ciphertext, altered nonce/tag and wrong key. Does not write archives, persist a key, use actual NCAAF data, call APIs or produce an Actions artifact. This is **not** a production backup implementation and does not prove off-host restore.

The existing manual GitHub workflow remains unchanged and invokes Python tests only. The new Node exercise is for reviewed isolated use; it is not automatically triggered.

## Decisions REQUIRED before any real data transfer
1. Owner chooses exactly who holds the key, with two separate encrypted escrow/recovery copies. Never keep the only key in GitHub secrets or with the ciphertext.
2. Approve one off-host storage provider, repository visibility/ACL, quota, price, retention and deletion/recovery behavior. An immutable GitHub Release in a public repository exposes ciphertext and metadata to everyone; encryption does not hide filenames/sizes/timing.
3. Approve maximum backup bytes, archival growth, checksum manifests, confidentiality review, RPO/RTO, and a separately tested second-location restore.
4. Approve a dedicated operational repository workflow with explicit limited secret exposure, least privileges, collision protection, rotation procedure, and fail-closed execution. This requires **separate authorization**.
5. Authorize transfer only after actual hosted resource, owner access, key custody and rollback gates are independently verified.

## Candidate storage comparison (research, not selection)
- GitHub immutable releases: existing Phase 5 design; public metadata and ciphertext, service/storage eligibility and long-term availability must be verified. No repository releases authorized now.
- GitHub Actions artifacts: suitable for short-run evidence but not the sole long-term backup; run/log/artifact retention is configurable and finite (public repository up to 90 days, per GitHub docs).
- Owner-selected private remote object storage: can separate access controls from public code, but pricing, quotas, egress, retention and key recovery remain unverified.
- Separate owner-controlled offline disk: may offer independent recovery but requires physical custody, encryption, scheduled copy validation, and geographic separation.

No storage destination is selected. No ongoing cost is certified as zero. Source policies and retention are subject to change.

Current status remains HOSTED_READY=false; MODEL_VALIDATED=false; BACKUP_PUBLICATION_AUTHORIZED=false. NCAAF PPG/Ridge forecasts and data remain untouched.
