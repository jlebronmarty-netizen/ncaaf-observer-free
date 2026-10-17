# Phase 7C â€” proposed OFF-HOST SYNTHETIC recovery design (NOT ACTIVATED)

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
2. Generate a one-time **test-only** encryption key in an isolated test process. Never persist the key in files, Git, logs, provider storage or secrets, and never reuse it for operations. For a second machine, a separately approved authenticated, encrypted, transient key handoff to the restore operator is required; see the protocol below. Client-side AEAD encryption is mandatory before any external transfer; authenticate version, algorithm, nonce and object context.
3. Generate a disposable fake SQLite database using obviously synthetic values, freeze a canonical manifest and SHA256, encrypt locally, and upload ONLY the synthetic ciphertext with a non-sensitive object name.
4. Download from an independently created fresh environment with explicitly scoped read credentials, verify ciphertext digest, AEAD tag, manifest, source hash, schema and SQLite cold integrity. Prove non-overwrite and no partial publication.
5. Inject incorrect key, corrupted object, missing object, altered metadata, revoked read access and premature retention/deletion scenarios. Require fail-closed behavior and no leaked secrets in logs.
6. Delete/revoke ONLY test resources and credentials under a separately reviewed cleanup protocol. Retain redacted test evidence and hashes without the test payload.
7. Document RPO/RTO, independent operator recovery, key-loss/rotation and residual single-account failure risk.

## Final review gates before real NCAAF data
Explicit owner authorization for (a) precise storage destination and cost cap; (b) identity/ACL scopes and retention; (c) secure operational key generation plus two independent recovery custody locations; (d) a true off-host restore demonstrating integrity; (e) scoped data-upload authorization; (f) durable hosted workflows and monitoring/schedules via a separate release decision.

`HOSTED_READY=false`; `MODEL_VALIDATED=false`; `BACKUP_PUBLICATION_AUTHORIZED=false`.

## Independent policy review ? 2026-10-17 (America/La_Paz)

Public official documents were reviewed; no account, balance, entitlement, storage
configuration or provider identity was accessed. Published free allowances are not
verified unused account capacity, a hard spending stop, perpetual retention or an SLA.

| Candidate | Official current allowance and constraints | Assessment for this test |
|---|---|---|
| Cloudflare R2 Standard | 10 GB-month storage, 1M Class A and 10M Class B operations/month free; direct egress free. Overage: $0.015/GB-month, $4.50/M A, $0.36/M B with unit rounding. Infrequent Access has no free allowance and a 30-day minimum. | Potential $0 usage only inside remaining allowances. R2 activation is described as a purchase prerequisite for tokens; billing/activation approval and account headroom remain unverified. No activation now. |
| Backblaze B2 pay-as-you-go | First 10 GB storage free; free egress up to 3x average monthly storage, then $0.01/GB. No minimum file size/storage duration. Published storage rate starts $6.95/TB/month; A/B/C calls free, D calls have a separate allowance/charge. | Potential $0 usage, not a guaranteed zero-cost restore. Short-lived stored objects can have a tiny average-monthly-storage egress allowance. Account payment, caps and request classes must be checked. |
| Public GitHub Releases | Up to1000 assets/release, each under2 GiB; docs state no aggregate release size or bandwidth limit. | Not a private or independent recovery account/control plane; policy is not perpetual archival assurance. Rejected for this confidentiality-focused test; no release authorized. |
| GitHub Actions artifacts | Public-repository retention can be1?90days, default90; settings/deletion affect availability. | Transient evidence, not selected as backup. No artifact upload authorized. |
| Existing separate offline disk | No new subscription if already owned; hardware, transport and custody costs unknown. | Valuable separately located copy, not proof of external provider/API recovery. No disk acquired/accessed. |

Sources: [R2 pricing](https://developers.cloudflare.com/r2/pricing/),
[R2 authentication/activation](https://developers.cloudflare.com/r2/api/tokens/),
[B2 pricing](https://www.backblaze.com/cloud-storage/pricing),
[GitHub release limits](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases),
[GitHub retention](https://docs.github.com/en/organizations/managing-organization-settings/configuring-the-retention-period-for-github-actions-artifacts-and-logs-in-your-organization).

**No provider selected.** Shortlist private B2 and R2 Standard; choose only after an
owner-approved, account-specific preflight. Both have usage billing risks. The target
is no fixed recurring subscription and a USD0 test ceiling, not an automatic payment
permission. Budget alerts are not hard caps. If zero charge cannot be established
under real provider controls/remaining allowance, stop BLOCKED or request a separate
explicit monetary authorization; never silently enable charges/trials/add-ons.

## Frozen proposed one-shot synthetic protocol (not executable or authorized)

### Scope, budget and independent roles

Before implementation/execution, freeze an approval receipt with exact Git SHA,
provider/account/bucket/region, random test namespace, two machine identities,
operators, permitted endpoints, expiry, request/byte caps and cleanup owner. No
production account, mounted source archive, shared sport credentials or GitHub-hosted
transfer workflow may be used. Machine B must be a different physical host or VM
control plane, not another local directory. Separately record shared account/provider
failure domains; no claim that a successful download survives account deletion.

One session: at most2hours, one SQLite fixture <=1MiB, at most8 opaque test objects,
<=2MiB per object and <=16MiB stored total, <=64MiB downloaded, <=256 total provider
requests including failures/retries. Retry only transient failures twice at most
within all caps; authorization, integrity, missing-object and budget failures never
retry automatically. Credentials expire within2hours; cleanup verification deadline
24hours after start. Account-wide free allowance shared with other workloads must be
reserved and checked; these local caps alone do not enforce a dollar ceiling.

| Role | Allowed | Explicitly denied / never supplied |
|---|---|---|
| W: upload identity, machine A | Create exact synthetic namespace objects only; optional exact-object metadata verification if provider requires it | Other buckets/namespaces, bucket/account management, deletion, retention changes; no admin credential |
| R: restore identity, machine B | Read exact approved namespace/objects | PUT, DELETE, configuration changes, other namespaces; no W credential |
| C: cleanup custodian | Separately approved deletion of the exact manifest-listed test object versions and temporary identities | No wildcard/prefix-wide deletion, no unrelated account cleanup |
| K: one-use test key custodian | Authenticated transient handoff to approved restore operator | Key in provider objects, public evidence, files, secrets, shell arguments or logs |

Separate credentials alone are insufficient: verify effective provider capabilities
and test denied operations. [B2 keys](https://www.backblaze.com/docs/cloud-storage-application-keys)
can restrict bucket/name prefix and distinguish readFiles/writeFiles/deleteFiles.
[R2 object tokens](https://developers.cloudflare.com/r2/api/tokens/) can be bucket-
scoped; basic read/write grants must not be described as write-only. Review
[R2 temporary credential scoping](https://developers.cloudflare.com/r2/api/s3/temporary-credentials/)
for the exact chosen operations. If required scope cannot be enforced, choose another
provider/design rather than weakening W/R separation. Do not hand parent/admin tokens
to either machine. Provider-side authorization tests remain PENDING.

### Fixture, trusted identity and encryption

1. Verify both clean environments have no real-data mounts, operational keys or
   production configuration. Disable command tracing, core dumps and verbose HTTP
   headers; never log credentials, signed URLs, Authorization headers or key material.
2. Generate only obvious fake rows in a closed SQLite fixture on A. Freeze schema,
   exact rows/count, UTC creation time, run ID, plaintext byte count and SHA256 in a
   canonical manifest. Expected hashes must reach B through a reviewed independent
   trusted channel; a mutable manifest downloaded beside ciphertext is not a trust root.
3. Generate a fresh32byte AES key and96bit nonce for each encrypted variant; never
   reuse a key/nonce pair. Use AES-256-GCM with a full128bit tag. Authenticated header
   (AAD) binds version, algorithm, run ID, object ID, lengths and plaintext/manifest
   identity. Encrypt the manifest with the fixture; keep external names opaque.
   Provider TLS and server-side encryption do not replace client-side authentication.
4. Mandatory future envelope implementation review precedes transfer. Existing Node
   tests demonstrate the primitive only; they do not implement this AAD/envelope.
   Freeze ciphertext SHA256/size and exact provider object/version identity before
   upload. Publish no sensitive filename, object URL or key in Git/Actions evidence.
5. K uses a separately approved encrypted authenticated transient session, verifying
   both recipients' identities, to hand the disposable key to B in memory. This is
   the explicit exception to 'never upload a key': never send it to the storage
   destination or persist it. If no such channel exists, stop BLOCKED. Retain only
   a non-secret handoff receipt. Do not claim secure RAM erasure is guaranteed.

### Off-host restore and failure matrix

Upload only approved synthetic ciphertext with W; record actual provider object ID,
version, timestamps and status. Stop A's transfer process. On fresh B, using R only,
download the exact identity to a NEW staging directory. Verify bounded size, trusted
ciphertext hash, header/AAD, GCM final tag, authenticated manifest, plaintext hash,
SQLite schema/complete row equality and cold read-only PRAGMA integrity_check. No
plaintext destination publication before all checks pass. Use atomic no-clobber
publication; never fall back to overwrite. Keep partial plaintext private, remove
staging on failure and prove pre-existing sentinel files remain byte-identical.

| Case | Required evidence / outcome |
|---|---|
| Valid object | Trusted source/restore hashes and exact rows equal; cold SQLite ok; actual remote download identity recorded |
| Wrong key; flipped/truncated ciphertext; changed/missing tag, nonce or AAD | Authentication/hash failure; no restored destination or plaintext in logs |
| Missing object / wrong run ID / replaced version | Explicit failure against pinned identity; no fallback to latest/another object |
| R PUT/DELETE and cross-namespace read; W DELETE/configuration/cross-namespace write | Provider denies; only synthetic canary targets exist. An accepted forbidden action FAILS ACL gate |
| Expired/revoked R credentials | Authorization failure; no privileged fallback or automatic credential creation |
| Interrupted download, low disk, existing destination | No partial publish/overwrite, bounded stop, staging cleaned |
| Premature deletion | C deletes only a designated sacrificial synthetic object; R detects missing identity. Does not claim lifecycle timing tested |
| Object lock / retention | No indefinite lock in this test. Any time-limited lock needs separate approval/expiry and observed deletion denial; otherwise mark UNTESTED |

All cases are future tests, not PASS receipts. A source-object digest may fail before
GCM; record the stage that rejected it rather than claiming every layer executed.
Keep the good object until B verification is complete. Record start/end UTC and
measured recovery time (target <=30minutes); synthetic RPO is the frozen fixture,
not an operational RPO guarantee. Lost test key must cause explicit unrecoverable
status, never a fabricated successful restore or real-key substitution.

### Retention, cleanup and audit evidence

Use an agreed <=24hour synthetic retention window with explicit immediate cleanup
after testing; verify effective lifecycle rules and existing object versions. No
indefinite retention, compliance lock, replication, event notifications, public
endpoint or lifecycle mutation is implicitly approved. Locks may prevent deletion;
[R2 lock precedence](https://developers.cloudflare.com/r2/buckets/bucket-locks/) and
[lifecycle timing](https://developers.cloudflare.com/r2/buckets/object-lifecycles/)
must be reviewed. Lifecycle expiration is not proof of deletion or secure erasure.

C first compares provider/account/bucket and the exact owned object/version manifest
with the approval receipt. Delete only those identities (including test versions or
multipart remnants if authorized), verify absence using scoped metadata/list checks,
revoke W/R and transient test credentials, close the handoff session, remove local
synthetic plaintext/ciphertext/staging from both hosts, and verify zero owned residuals.
Do not delete a bucket/account or weaken locks to force cleanup. Failed cleanup becomes
CLEANUP_PENDING with owner, object identifiers and deadline until confirmed resolved;
stop further tests and report cost/retention exposure. Never claim overall PASS while
unexpected test resources remain.

Retain redacted source SHA, approval reference, role-scope/denial receipts, request
counts, object/manifest hashes, provider timestamps, cases and outcomes, costs,
cleanup/revocation confirmations and full non-secret logs. Keep private account/object
identifiers outside the public PR. Hashes establish integrity, not authenticity alone.
No test keys, credentials, payloads, signed URLs or actual NCAAF evidence are retained
in public logs. Overall external PASS requires actual observed recovery, ACL denials,
all mandatory failure checks and cleanup; unexecuted/unsupported checks remain
PENDING/BLOCKED, never inferred from these offline tests.

## Current blockers and next approval

Only design/offline review is complete. Exact destination/account and unused budget,
provider policy/ACL enforcement, independent host/operator, temporary key-handoff
channel, scoped identities and owner-approved cleanup remain unverified. No external
recovery was executed. Next approval must name those resources, fixed source SHA,
USD0 ceiling (or a separately approved explicit cap), session/retention limits and
permit one manual synthetic-only setup/upload/download/failure/cleanup session.
Creating identities, storage activation or test keys is not authorized by this PR.
Operational data transfers and hosted schedules require later separate decisions.
