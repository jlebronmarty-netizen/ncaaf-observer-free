# Phase 7C — proposed OFF-HOST SYNTHETIC recovery design (NOT ACTIVATED)

Status: design-only, not a provider selection, upload permission, or test receipt.
No real NCAAF data, keys, forecasts, historical captures or backups may be read or moved.

## Security boundary
The repository is public. Its code and test-only documentation may be public; **not even encrypted operational backup objects are approved**. A public GitHub Release leaks timing, object sizes, provenance and ciphertext; do not choose it automatically.

The approved manual workflow remains exactly as-is, without schedules, secrets, uploads, cloud API calls, or artifact publication. A new hosted/off-host workflow requires separate authorization and review.

## Compare independent recovery locations before selecting one

| Candidate | Separation and confidentiality | Unresolved acceptance checks |
|---|---|---|
| Separate owner-controlled private object storage/account | Potentially different account and failure domain; private ACL can protect ciphertext and metadata | Contract, cost, storage, egress, access-key scope, versioning/immutability, deletion, region, provider policy, restore from a truly separate machine |
| Separate owner-controlled offline disk | Offline recovery independent of GitHub account; physical access restrictions | Encryption, transport, independent location, damage/theft risk, inspection cadence, restore testing |
| Immutable GitHub Releases in public observer repo | Different durable host from local Windows, but same GitHub control plane as Actions and code; public metadata/ciphertext | Provider limits, terms, permanence, release immutability, account compromise, key escrow, public disclosure; **not approved** |
| GitHub Actions artifacts | Convenient transient evidence from hosted tests | Not a durable primary backup; retention and provider quotas need verification; **not approved** |

No claimed free quota or $0 cost without an actual provider/account/eligibility review.

## Future isolated synthetic-only external test (requires a NEW approval)
1. Select an explicitly named destination and account; validate terms, public/private visibility, all access policies, lifecycle/retention, available quota, region and cost ceiling. Do not test against an unknown production account.
2. Generate a one-time **test-only** encryption key in an isolated test process. Never store or upload the key, and never reuse it for operations. Prefer client-side AEAD encryption before any external transfer; include authenticated version, algorithm, randomly generated nonce and object context.
3. Generate a disposable fake SQLite database using obviously synthetic values, freeze a canonical manifest and SHA256, encrypt locally, and upload ONLY the synthetic ciphertext with a non-sensitive object name.
4. Download from an independently created fresh environment with explicitly scoped read credentials, verify ciphertext digest, AEAD tag, manifest, source hash, schema and SQLite cold integrity. Prove non-overwrite and no partial publication.
5. Inject incorrect key, corrupted object, missing object, altered metadata, revoked read access and premature retention/deletion scenarios. Require fail-closed behavior and no leaked secrets in logs.
6. Delete/revoke ONLY test resources and credentials under a separately reviewed cleanup protocol. Retain redacted test evidence and hashes without the test payload.
7. Document RPO/RTO, independent operator recovery, key-loss/rotation and residual single-account failure risk.

## Final review gates before real NCAAF data
Explicit owner authorization for (a) precise storage destination and cost cap; (b) identity/ACL scopes and retention; (c) secure operational key generation plus two independent recovery custody locations; (d) a true off-host restore demonstrating integrity; (e) scoped data-upload authorization; (f) durable hosted workflows and monitoring/schedules via a separate release decision.

`HOSTED_READY=false`; `MODEL_VALIDATED=false`; `BACKUP_PUBLICATION_AUTHORIZED=false`.
