# NCAAF Dedicated Observer — Security and Data Publication Review

| Area | State |
|---|---|
| Public code and safe documentation | APPROVED |
| Forecasts, raw captures, SQLite databases | NOT APPROVED for upload |
| Encrypted backup upload | NOT APPROVED |
| Backup encryption key generation and custody | NOT APPROVED / NOT CONFIGURED |
| GitHub secret NCAAF_BACKUP_KEY | NOT CONFIGURED |
| Two independent key escrow/recovery locations | NOT SELECTED |
| Off-host backup provider, ACL and retention | NOT SELECTED |
| Manual hosted run with authentic data | NOT APPROVED |
| Synthetic offline manual checks | APPROVED |
| Active workflow file, scheduled triggers | NOT APPROVED |
| Public Pages/dashboard | NOT APPROVED |
| Alerts/heartbeat receiver | NOT SELECTED |
| Production merge, deploy, migrations | NOT APPROVED |

## Before data transfer
Review public-repository exposure, release deletion and retention, confidentiality of filenames and manifests, authenticated-encryption (AES-GCM) implementation, key loss/rotation, backup integrity and recovery, Git state-journal concurrency, provider quota/terms, and scope of administrators. Verify ciphertext and restored plaintext hashes with an explicitly approved off-host destination. Do not transfer even encrypted captures until the owner separately approves.

## Current boundaries
No workflows are activated; no keys, secrets, raw data or research results have been published here. Preserve the original PR #21 ledger and all local parent/delta backups. Never reset live data with an earlier backup.

## Independent observation ? 2026-10-17

Preparation status: **SECURITY_PREPARATION_COMPLETE**, not a hosted security certification.
Evidence: `audit/github-observations.json`; source baseline
`980c596d11b21572388e08d36367bf34fed053c4` (all five original blobs inventoried).
The Phase 5 architecture and release checklist at source checkpoint
`55c99d359f833494d619c46014d5b8c431b4e7d9` were reviewed read-only.
No forecast archives, SQLite state, backup files or operational encryption keys were accessed.

| Control | Independent result |
|---|---|
| Visibility/default branch | VERIFIED public / main |
| Protect Main | VERIFIED active default-branch ruleset; no exclusions/bypass actors; deletion and non-fast-forward prohibited; PR required |
| Review strength | FINDING: zero approving reviews required; no CODEOWNER/last-push approval; stale approvals not dismissed; thread resolution required. PR requirement is not independent approval |
| Classic branch protection endpoint | HTTP404; not evidence against the separately verified ruleset |
| Collaborators | VERIFIED zero non-owner direct collaborators; API includes owner admin as one returned entry |
| Actions | VERIFIED disabled; zero workflows and workflow runs |
| Workflow token defaults | VERIFIED contents read default; Actions cannot approve PR reviews; repository-wide SHA pinning requirement false |
| Secret scanning / push protection | VERIFIED enabled; non-provider patterns and validity checks disabled |
| Dependabot | VERIFIED alerts enabled (HTTP204), security updates enabled/not paused; no dependency manifest or update schedule in source |
| Repository secret/variable metadata | VERIFIED zero each; no values requested. Does not establish installation/account-level secret absence |
| Releases/webhooks/deployments | VERIFIED zero each at observation time |
| Pages | HTTP404; absence not independently certified through this response alone; no local publication configuration |
| GitHub App installation selection | UNVERIFIED: authorized user/installations API returns403. Owner reports Codex and Vercel retain all-repository access; no account setting changed |
| Effective authenticated API authority | Repository reports admin/push rights. This audit used GETs only; credential is not technically read-only |
| Operational files / source credentials | PASS bounded local scanner and manual inventory; not a complete DLP proof for arbitrary encodings or future commits |
| Hosted enforcement/runtime/logging | PENDING, no hosted job executed; no runtime log masking or provider-side behavior claimed |

### Residual risks and owner decisions

All-repository GitHub App access increases the impact of an app compromise or mistaken
repository targeting, including other sports. Branch rulesets do not revoke app tokens,
protect all feature branches, or prove that an app cannot read or deploy public source.
Zero direct collaborators does not mean zero apps, administrators or inherited access.
The current API cannot certify installation selection, permission changes, Vercel
integration behavior or external app retention. The owner should inspect both installed
apps and their exact granted permissions in account settings; preserve existing projects.
No active webhook in this repository does not exclude app-wide webhook mechanisms.

`.gitignore` is defense in depth: it does not prevent force-add, generic JSON renamed
as documentation, malicious code changes or remote API uploads. The fail-closed file
allowlist, binary signatures, credential pattern tests and manual diff review reduce
accidents, not deliberate administrator action. Review scripts and tests before any
hosted approval; the read token can read public code and checkout contacts GitHub.
The template's pinned checkout is third-party executable code, so review its exact
SHA/security advisories and normal runner/network assumptions before eventual use.
No dependencies, runtime installers, artifact/release APIs or provider integrations are
introduced. No secret-bearing live logs exist here to validate masking against.

### Tests and failures retained

Original bootstrap:4/4 passed. Expanded suite:14/14 passed, including forbidden
triggers/permissions/actions, synthetic credential redaction, disguised archives/SQLite,
operational paths, checkout persistence/pin changes and ignore-pattern checks.
The first expanded run failed:8 fixture errors were restricted Windows temp-directory
permissions;1 assertion failure was text-mode CRLF input to git check-ignore. Synthetic
fixture execution was rerun with normal authorized temp access; the test now uses NUL-
delimited binary stdin/stdout. Assertions were not relaxed. Final log is
`audit/OFFLINE_TEST_RESULTS.txt`. No active hosted or authentic forecast tests were run.

`HOSTED_READY=false`; `MODEL_VALIDATED=false`; `ACTIONS_ENABLED=false`;
`BACKUP_PUBLICATION_AUTHORIZED=false`.
