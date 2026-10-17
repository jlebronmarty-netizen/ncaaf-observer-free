# Phase 7D — Cloudflare R2 synthetic-only recovery design (NOT ACTIVATED)

Status: DOCUMENTATION / REVIEW ONLY. No R2 account, bucket, API token, credential, operational encryption key, transfer, or hosted job created. Public NCAAF observer repository stays free of data and backup assets. No modification to the existing manual-only workflow.

## Proposed destination (requires separate owner authorization)
Cloudflare R2 **Standard** private bucket in an owner-controlled Cloudflare account. Proposed non-sensitive placeholder bucket name: `ncaaf-synthetic-recovery-test` (not created, availability unknown). Public access and custom-domain/r2.dev access must remain OFF. No operational NCAAF payload may ever enter the synthetic test namespace.

Official docs:
- https://developers.cloudflare.com/r2/pricing/
- https://developers.cloudflare.com/r2/api/tokens/
- https://developers.cloudflare.com/r2/buckets/public-buckets/

R2 Standard currently documents 10 GB-month storage, 1M Class A and 10M Class B requests free per month, plus no direct egress fees. These are account-level allowances, **not** guaranteed unused quota or a hard billing cap. Published overage is $0.015/GB-month, $4.50/M Class A, $0.36/M Class B. Infrequent Access is excluded from the free tier. Account activation/payment conditions and actual spending controls must be confirmed in the owner's dashboard before creating any resource.

## Future synthetic-only test boundaries (not yet approved)
1. Confirm account identity, billing state, available free-tier headroom and an enforceable owner-approved cost ceiling. **If $0 is a strict hard cap and Cloudflare cannot enforce it, do not create the bucket or run the test.**
2. Create one private R2 Standard test bucket only after owner approval, with public bucket access explicitly disabled and no public bindings. Never use an existing production bucket.
3. Create separate time-limited, bucket-scoped identities for write and read where supported: write only necessary object operations, read only necessary retrieval operations. No account-wide API tokens, unrestricted delete rights, or GitHub repository secrets. If independent scoped identities are unavailable, stop.
4. Generate a visibly synthetic SQLite fixture in an isolated ephemeral process and create a manifest of schema/version, length and SHA256. Generate a **disposable test-only** random 256-bit AES-GCM key; use a unique 96-bit nonce and authenticated metadata. Never print or persist the test key in the public repository or logs.
5. The independently authorized receiver must obtain the short-lived test key through a separately approved authenticated encrypted one-time channel; never transfer it with the encrypted object or publish it in GitHub. If a secure cross-host handoff cannot be demonstrated, stop.
6. Encrypt the synthetic fixture locally, then upload **only** authenticated ciphertext to a private synthetic path. Verify an object HEAD/hash; download from a genuinely separate fresh machine/runtime using read-only credentials. Authenticate ciphertext, verify manifest and SHA256, validate SQLite integrity in staging, and atomically publish without overwriting existing state.
7. Fail closed for wrong key, altered tag/ciphertext/nonce, missing object, expired/revoked credentials, failed download, partial copy, concurrency and retention/deletion. Preserve redacted evidence showing object count/size, request counts, exact SHA256, tested identities, and recovery time without revealing secrets.
8. Clean up only the approved synthetic test object, test bucket and scoped tokens after receiving separate cleanup authorization; verify no orphaned objects or live credentials remain. Never delete other buckets.
9. Determine practical off-host RPO/RTO and key recovery separately; a success with synthetic data does not authorize backups of PPG/Ridge forecasts or real historical captures.

## Owner decision checklist — no implicit permissions
- [ ] Approve **named Cloudflare account** and test bucket identifier.
- [ ] Confirm private-only bucket and Standard storage.
- [ ] Verify billing, current free allocation and enforceable spending controls; approve hard cost ceiling.
- [ ] Approve two narrowly scoped identities and key handoff channel.
- [ ] Approve the independent recovery host and the one synthetic-only external upload/download session.
- [ ] Approve explicit cleanup scope, retention and maximum test object size.
- [ ] Review and authorize any new workflow separately; existing manual security preflight stays unchanged.

Release flags: `HOSTED_READY=false`, `MODEL_VALIDATED=false`, `BACKUP_PUBLICATION_AUTHORIZED=false`, `R2_EXTERNAL_TEST_AUTHORIZED=false`.
