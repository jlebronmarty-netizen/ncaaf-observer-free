# Phase 7D â€” Cloudflare R2 synthetic-only recovery design (NOT ACTIVATED)

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
6. Encrypt the synthetic fixture locally, then upload **only** authenticated ciphertext to a private synthetic path. Use HEAD for bounded size/identity only (ETag is not a trusted SHA256); independently pin ciphertext SHA256 and verify the complete downloaded bytes; download from a genuinely separate fresh machine/runtime using read-only credentials. Authenticate ciphertext, verify manifest and SHA256, validate SQLite integrity in staging, and atomically publish without overwriting existing state.
7. Fail closed for wrong key, altered tag/ciphertext/nonce, missing object, expired/revoked credentials, failed download, partial copy, concurrency and retention/deletion. Preserve redacted evidence showing object count/size, request counts, exact SHA256, tested identities, and recovery time without revealing secrets.
8. Clean up only the approved synthetic test object, test bucket and scoped tokens after receiving separate cleanup authorization; verify no orphaned objects or live credentials remain. Never delete other buckets.
9. Determine practical off-host RPO/RTO and key recovery separately; a success with synthetic data does not authorize backups of PPG/Ridge forecasts or real historical captures.

## Owner decision checklist â€” no implicit permissions
- [ ] Approve **named Cloudflare account** and test bucket identifier.
- [ ] Confirm private-only bucket and Standard storage.
- [ ] Verify billing, current free allocation and enforceable spending controls; approve hard cost ceiling.
- [ ] Approve two narrowly scoped identities and key handoff channel.
- [ ] Approve the independent recovery host and the one synthetic-only external upload/download session.
- [ ] Approve explicit cleanup scope, retention and maximum test object size.
- [ ] Review and authorize any new workflow separately; existing manual security preflight stays unchanged.

Release flags: `HOSTED_READY=false`, `MODEL_VALIDATED=false`, `BACKUP_PUBLICATION_AUTHORIZED=false`, `R2_EXTERNAL_TEST_AUTHORIZED=false`.

## Independent official-policy review ? 2026-10-17

### Strict USD0 gate: BLOCKED for external execution

Cloudflare's [budget alert policy](https://developers.cloudflare.com/billing/manage/budget-alerts/)
states alerts notify on spend and do not stop usage or enforce a cap. The
[billable usage view](https://developers.cloudflare.com/billing/manage/billable-usage/)
is monitoring, not prepaid enforcement. A low alert threshold, empty payment card,
local request counter, small payload, token expiry or later cleanup is not an
account-level spending guarantee. Existing other usage can consume free allowances.

No documented/verifiable R2 hard-USD0 control was established from the reviewed
public policies. No account/billing dashboard was accessed, so account-specific
exceptions are UNVERIFIED. **Do not create/activate R2, mint credentials or transfer
anything while an absolute USD0 requirement remains unsatisfied.** A future owner
must either supply independently verifiable provider enforcement, choose a different
suitable destination, or separately change the requirement and expressly accept
metered billing exposure. A nominal dollar budget without provider enforcement is
not a guaranteed maximum. This review does not authorize any billing-risk waiver.

[R2 pricing](https://developers.cloudflare.com/r2/pricing/) confirms Standard-only
free allowances and metered overages stated above; GB-month is averaged usage,
not a permanent free allocation. Unit rounding applies. Additional connected
services may charge independently. Published free quota is not verified unused
account quota or proof that this owner has activated R2 without charges. The
[token guide](https://developers.cloudflare.com/r2/api/tokens/) requires R2 purchase/
activation before token generation. No purchase/activation or subscription change
is authorized. Standard has no minimum storage duration; that does not guarantee
retention or deletion timing. Infrequent Access remains excluded.

### Privacy, least privilege and provider enforcement

[Public bucket policy](https://developers.cloudflare.com/r2/buckets/public-buckets/)
confirms buckets are private by default, while custom-domain and r2.dev exposure
are independent. Future preflight must verify both OFF, no Worker proxy/binding,
public endpoint, replication, event notification or existing unrelated consumer.
Do not enable a public URL to test privacy; use scoped provider configuration and
an explicitly approved anonymous denial test only where an endpoint already exists.
Opaque names hide neither sizes/timing from the provider nor account metadata from
administrators. Client-side authenticated encryption remains mandatory.

[Basic R2 tokens](https://developers.cloudflare.com/r2/api/tokens/) offer bucket-
scoped Object Read/Write or Object Read, not a write-only security guarantee. The
[temporary credential specification](https://developers.cloudflare.com/r2/api/s3/temporary-credentials/)
supports exact bucket/object paths and S3 actions; action lists currently require
trusted local signing, not the temporary-credential API's preset permissions.
The parent token must stay with a separately approved trusted custodian, never on
the upload/restore host. Do not implement signing or create credentials now.

Proposed future roles: W permits PutObject on exact new synthetic object names;
R permits GetObject/HeadObject on exact approved identities; C separately permits
DeleteObject for manifest-listed test objects only. No List/Delete/Copy/multipart
or bucket/account management on W/R. A separate owner control-plane action handles
approved identity revocation/bucket cleanup. Credential TTL <=2hours. Conditional
no-overwrite PUT support must be checked against actual R2 behavior before use;
unique names alone are not overwrite protection. Required denied-operation tests
include R write/delete, W delete, cross-prefix/cross-bucket access and configuration
changes. If the selected credential mechanism cannot enforce this scope, stop
rather than using broad presets or shipping the parent secret.

### Precise proposed off-host session and trusted evidence

Inherit the frozen safeguards in [the Phase7C design](PHASE7_OFFHOST_SYNTHETIC_DESIGN.md).
Freeze exact source SHA/account/bucket/jurisdiction/endpoints, run ID, W/R/C custody,
independent host/operator, approval expiry, key-handoff channel and cleanup authority.
No real-data mounts or operational environment variables on either host. This is
one manually authorized session, not a hosted transfer workflow or recurring job.
Caps: <=1MiB fake SQLite, <=8 ciphertext objects/16MiB stored, <=64MiB downloaded,
<=256 provider requests including failures/retries, <=2hour run, <=24hour cleanup
deadline. These caps reduce risk but **do not satisfy the USD0 gate**.

Freeze schema/exact fake rows/byte counts/plaintext and manifest SHA256 before
transfer. The independent receiver must receive the trusted manifest/ciphertext
hash through an approved separate authenticated channel; mutable object metadata
or a colocated manifest cannot authenticate itself. Encrypt manifest and payload
with AES-256-GCM (fresh32byte test key, unique96bit nonce, full128bit tag), authenticating
version/run/object identity and lengths as AAD. Existing Node tests do not implement
this envelope; future implementation must be reviewed before any external use.
Neither public evidence nor the provider receives the test key. Its transient
encrypted handoff requires independent recipient verification and leaves no key in
files, GitHub Secrets, shell arguments or logs. Memory erasure is best effort only.

Host B must be a genuinely separate fresh machine/control plane, not another local
directory or process sharing A's disk. Download exact object identity using R only;
verify bounded length, trusted ciphertext SHA256, GCM final authentication, manifest,
plaintext hash, exact schema/rows and cold read-only SQLite integrity before atomic
no-clobber publication. Preserve sentinel destinations and clean private staging on
failure. Record measured recovery duration (target <=30minutes), source timestamp,
provider identity and outcome; no operational RPO/RTO claim from this exercise.

Future failure matrix: wrong key; modified/missing/truncated tag, ciphertext, nonce
or AAD; missing/replaced object/wrong run; expired/revoked R; forbidden W/R actions;
interrupted download; low disk; conflicting destination/concurrent publish; and
premature deletion of one explicitly sacrificial test object. Each must fail closed
with no plaintext output or privileged fallback. Record the rejecting layer accurately:
a hash failure does not prove the GCM check ran. Retry only transient transport errors,
at most twice and within all caps; no retries for integrity, authorization or cost gates.
All external cases remain NOT EXECUTED, not PASS.

### Cleanup: approve before setup, verify after completion

Approve C and exact cleanup scope as part of the session before creating anything;
do not start and then wait indefinitely for cleanup permission. No indefinite lock,
retention extension or lifecycle mutation is implicit. [Lifecycle behavior](https://developers.cloudflare.com/r2/buckets/object-lifecycles/)
and [bucket-lock precedence](https://developers.cloudflare.com/r2/buckets/bucket-locks/)
require inspection: lifecycle deletion is not instantaneous proof of absence, and
locks may prevent cleanup. Do not defeat a lock or expand permissions to force deletion.

Retain an exact test object inventory; C deletes only those keys and approved
multipart remnants. Confirm absence and revoke only dedicated test credentials;
parent revocation affects all derived credentials, so never use/revoke a shared
production parent. Delete the test bucket only with separate explicit approval,
proof this session created it, and proof it contains no unrelated objects/bindings.
No recursive prefix/bucket/account-wide cleanup. Confirm local fixture/ciphertext/
staging removal on both hosts. Any residual becomes CLEANUP_PENDING with owner,
identifier/deadline and cost exposure; no external overall PASS until resolved.
Keep redacted hashes, role/denial receipts, request counts, timestamps, recovery time,
retention/cost observations and cleanup evidence; no secrets, signed URLs or payloads.
Public documentation is not a place for private account/object identifiers.

## Current decision and outstanding approvals

Design/offline validation may PASS independently of the external execution gate.
External execution remains BLOCKED under strict USD0 until actual provider cap
proof or an explicit owner-approved requirement change. Also outstanding: named
account/bucket/region and activation/billing review; private configuration; trusted
signing custodian and effective W/R/C scopes; independent host/operator; transient
test-key channel; frozen source/envelope implementation review; and one time-limited
synthetic-only setup/upload/download/failure/cleanup authorization. No permission is
inferred from merging this documentation. No resource/token/key/secret/backup/upload/
release/schedule or production mutation occurred in this review.
