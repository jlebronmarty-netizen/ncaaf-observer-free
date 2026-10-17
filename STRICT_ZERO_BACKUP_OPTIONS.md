# Strict USD 0 external recovery alternatives — research only

Date: 2026-10-17. No new account, storage bucket, key, backup, upload, job or subscription created. The public repository remains code/design only. This does not authorize actual data transfer.

## Gate definition
An acceptable STRICT_ZERO destination must **not permit automatic overage charges** under the actual account/payment state, not merely show a free allowance or spend alert. Also require sufficient *remaining* capacity, authorized automation/API path, private object visibility, independent failure domain, real restore test and reviewed loss/retention behavior. A source with no confirmed zero-overage mechanism is not qualified.

| Candidate | Published free allocation | Quota behavior / residual risk | Automation and operational status |
|---|---|---|---|
| Google Drive Personal | Up to 15 GB shared across Gmail/Drive/Photos | When quota is full, new uploads stop; account-wide mail and storage operations may be affected; potential data deletion after prolonged overage. **Confirm owner account has no paid storage enabled and unused quota.** | Possible connector/API path requires explicit scope/quota/terms review; not authorized. Not necessarily enough for >500MB snapshots and multiple generations. |
| OneDrive free personal | 5 GB | Upload/edit/sync stop when over quota; prolonged overage may freeze account and later cause deletion. Verify account plan and actual available capacity. | Integration/authentication/terms require investigation; no operational app connection authorized. |
| Proton Drive Free | 5 GB Drive allocation | Free storage plan without automatic overage entitlement assumed; owner must confirm exact signup/billing and account limits. | Automated noninteractive compatible API/SDK for unattended GitHub Windows jobs is **not verified**; manual encrypted recovery alternative only until proven. |
| GitHub Releases on public repository | Up to 1000 assets/release, each <2GiB; docs state no total release/bandwidth quota | Potential zero incremental billing under standard repository policies but retention, terms and availability are not guaranteed backups. Encrypted files and metadata would be PUBLIC. Shared GitHub control plane and administrator risk. | Not acceptable as a *private* independent recovery store under current disclosure policy. Not authorized. |
| Separate offline drive already owned | Capacity depends on owned hardware | No provider upload overages, but purchase/hardware cost not zero if not already owned; physical failure/theft and geographic separation critical. | Suitable possible secondary manual recovery, not unattended off-host operation without operator/replication design. |
| Cloudflare R2 Standard | 10 GB-month free with request allowances | Budget alerts do not enforce strict $0; provider overage possible. | BLOCKED under strict cap. |

## Source documentation reviewed
- Google: https://support.google.com/drive/answer/6374270
- Microsoft: https://support.microsoft.com/en-us/onedrive/microsoft-storage-quotas
- Proton: https://proton.me/es-419/drive/pricing
- GitHub: https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases
- Cloudflare: https://developers.cloudflare.com/r2/pricing/ and https://developers.cloudflare.com/billing/manage/budget-alerts/

## Research recommendation, not provider approval
For *private and strict-zero* synthetic tests, first verify an owner's **existing free** Google Drive account, current usage, and that no paid storage/overage contract applies, without sending any data. Second compare existing free OneDrive, with 5GB limit. Proton may be useful for manually controlled independent archival custody but lacks verified unattended API capability. A separate offline drive is a complementary recovery domain.

Do not rely on public GitHub Releases for private backups. Quota-blocked consumer drives may be $0 but do not necessarily support automation, immutable object locking, narrow credentials or high-frequency archival.

## Next gates (each requires new authorization)
1. Select exact existing free account and independently check plan, billing/overage constraints and free *remaining* capacity.
2. Propose a synthetic test object <=1MiB and retention period; select separate restore host/operator and authenticated transient key channel.
3. Review API/OAuth scopes, paid features, terms and request/traffic ceilings; if this cannot be automated safely, record MANUAL_ONLY.
4. Approve one isolated synthetic-only upload/download/verify/cleanup session. No operational NCAAF data.
5. Run a fresh-host restore; inspect actual integrity, overwrite, missing/corrupt key/object and retention behavior.
6. Only later consider an independent authorization for operational encrypted backups and monitoring.

No account inventory or external restore has been performed.
HOSTED_READY=false; MODEL_VALIDATED=false; BACKUP_PUBLICATION_AUTHORIZED=false.
