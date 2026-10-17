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
