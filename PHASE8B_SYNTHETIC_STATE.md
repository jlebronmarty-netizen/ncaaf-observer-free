# Phase8B ? offline hosted-state / Windows pull prototype

Status: SYNTHETIC_IMPLEMENTATION_VERIFIED, not hosted deployment or real model validation.
HOSTED_READY=false; MODEL_VALIDATED=false; BACKUP_PUBLICATION_AUTHORIZED=false.
No production schema/migration/credential, cloud resource, real upload, Windows task,
recurring workflow, source model change or PR merge. All generated data are obviously
fake; source program imports no network/client/credential/process-execution library.

## References and placement

- NCAAF PR21 frozen source:55c99d359f833494d619c46014d5b8c431b4e7d9.
- Observer PR9 reference:94f2d9f7af92544282a1002fd198c0fcd582639e.
- Production reference:d618287cabb3ec0dbe6ffb94cb14388c04827f54.
- Phase8A local receipt recorded62 PPG/59 Ridge forecasts and3 PPG settlements.
  This experiment does not open/re-export those databases, forecasts or artifacts.
- Prototype:scripts/synthetic_state_v1.py; tests:tests/test_synthetic_state_v1.py.
- Separate feature branch research/phase8b-synthetic-state is based on PR9's exact
  reference. A draft against main includes PR9's documentation dependency; no merge.

Run with an available Python3 (verified3.13.16):

```
python -I -m unittest discover -s tests -v
python -I scripts/security_preflight.py
node tests/synthetic_crypto_check.mjs
python -I scripts/synthetic_state_v1.py
```

The CLI has no real-data/root/network options. It creates a fresh marked system-temp
workspace, simulates host/client, prints metrics only, and removes the whole fixture.
A client can reattach only to marked synthetic persistence; missing markers fail closed.
No runtime packages or production setup are required. Existing manual GitHub workflow
and disabled template remain unchanged; they still run only the Python suite if the
owner separately dispatches it. No new hosted workflow was created or run.

## Minimum logical hosted schema (design, not a production migration)

The simulator encodes the following typed entities in append-only facts(seq,kind,id,
canonical_body,body_sha), checkpoints and one mutable control row. No complete local
SQLite database is imported. Real integration may use typed tables with the SAME
contracts, but needs its own migration/security review; this SQLite DDL is only a fixture.

| Entity | Immutable identity / minimum payload |
|---|---|
| model_artifact | model name + frozen version; artifact/code/protocol digest; freeze time. Real deployment also retains retrievable artifact bytes/URI, training cutoff and original manifests |
| event_identity | sport/provider event ID; participants, venue/neutral and season contract. Schedule revisions are observations, not overwrites |
| source_observation | canonical source-body digest; event, lifecycle, original source/capture/received timestamps and verified final scores; immutable raw/capture identity references |
| feature_bundle | hash of canonical model/event/as-of/input identities/values; missing-feature flags and frozen profile/artifact version; all inputs available before cutoff |
| forecast | unique(model-version,event); immutable original body/ID, source/feature/artifact references, created_at/as_of/kickoff, projections and confidence/abstention contract |
| settlement | forecast identity + policy; final observation reference, grading facts and original observation time; identical retry is a no-op, conflict requires append-only review |
| correction_review | forecast + corrected observation + reason/review state; original settlement retained, never silently replaced |
| committed_checkpoint | monotonic generation, parent SHA, exact object SHA/size, fact watermark, schema version, fencing epoch and commit time |
| writer_lease | owner, increasing epoch, expiry and expected committed generation; CAS/transaction fence checked inside commit |

Prototype intentionally limits fields to a fixture contract. Its two named model
streams use SIMULATED_RULES_V1, fake artifact digests and fixed21?17 /0.6 projections;
those are NOT NCAAF_PPG_V1/Ridge inference or actual forecasts. Feature inputs are
synthetic observations, not real priors/weekly profiles. Synthetic timestamps are
integer Unix-like seconds in a controlled clock, not actual prospective wall time.
A real adapter must preserve aware UTC original timestamps and original forecast IDs
byte-for-byte (alias existing IDs if needed), not regenerate the121 existing records
using the prototype's identity formula. No retuning/import adapter is included.

## Snapshot, idempotency, fencing and atomicity

NCAAF_PHASE8B_SYNTHETIC_V1 is canonical sorted UTF8 JSON with finite values, no duplicate
keys: format, synthetic=true, generation, parent, from_seq, watermark, fence,
committed_at, changes. Each change has contiguous seq, kind, immutable ID/body and
body SHA256. Snapshot object name is whole canonical SHA256. One delta contains at
most1MiB; model registry is emitted once, not recopied per generation. Initial
snapshot is a baseline from an empty fixture; later snapshots append new facts.

Forecast ID=SHA256(model-version + separator + event-ID). Event/model duplicates
with identical bodies do not allocate new rows/checkpoints; changed bodies under
an existing identity are rejected. New forecast.created_at must equal the simulated
commit clock, source/feature availability <=as_of<kickoff, and model freeze <=as_of.
Only verified matching FINAL observations can settle. Corrected finals append review
facts and do not overwrite the original settlement. The toy website projection shows
counts only; real corrected-metric exclusion/projection remains an integration gate.

A SQLite BEGIN IMMEDIATE transaction fences owner/epoch/expiry/expected generation;
lease takeover requires expiry AND explicit reviewed_takeover. Commit clocks and
snapshot fences cannot decrease. Facts and checkpoint journal reject UPDATE/DELETE.
The worker writes a no-clobber immutable object, then atomically commits facts,
checkpoint and head in one transaction. Failure after object/before commit leaves
an unreferenced orphan, never visible through the read-only transport. Retry is safe;
future hosted orphan cleanup must be separately reviewed. This is not a distributed
provider-CAS implementation or proof of cloud transaction semantics.

## Windows-off execution and pull-only backup

HostedSimulator.website_view reads committed host state without touching the client.
Tests advance several host sessions/settlements with the client unchanged/offline,
then catch up only missing objects. Recreated host/client instances retain their
synthetic durable checkpoints; no automatic reset. No actual PC shutdown or cloud
host is tested. A real hosted writer and website API remain missing.

ReadOnlyTransport exposes head/checkpoint/stream only. PullClient never calls a host
write path; before/after host file hashes are identical. This Python interface is
NOT a sandbox: it holds a host reference, so future provider-side read identity/ACL
must independently enforce read-only access. No such credential is configured here.

Pull stages bounded chunks, verifies whole SHA/strict format/full contiguous parent
chain and previous verified head, publishes no-clobber content-addressed objects and
version files using same-volume hard links, and performs a cold SQLite restore before
advancing last_verified.json by atomic local replace. Existing pointer is retained
on transfer, disk, checksum, semantic restore or pre-pointer failure. An interrupted
object restarts; previously verified complete objects are not downloaded twice.
No byte-range resumable network protocol is claimed. A10000-generation guard bounds
chain traversal; exceeding it blocks until a separately reviewed compaction protocol. Duplicate local clients fail
on an exclusive lock; crash-left locks require review, never automatic lock deletion.

Cold restore replays validated facts into a NEW synthetic SQLite file, checks complete
rows and PRAGMA integrity_check in a newly opened read-only connection, restores the
checkpoint journal/watermark and clears writer ownership/expiry. It is never pushed
up or promoted to host authority. Existing destination files cannot be overwritten.
Unsafe digest paths and destinations outside the disposable workspace are rejected.

Retention is explicit: retain baseline version file plus newest K files (default3);
keep ALL CAS parent objects needed by latest state. This is count-based recovery-point
retention, NOT the proposed calendar7daily/4weekly policy, full compaction or bounded
all-history storage. No referenced parent is deleted. Scientific archival retention,
compaction/rebase, secure local volume/ACL, true process-crash tests and global growth
caps remain later gates. Corrupt local checkpoint/cache blocks instead of silently
resetting; operator repair into a separate verified fixture is needed.

## Security scope and tests

53 Python tests pass (23 existing +30 new), plus offline scanner and existing Node
AES-GCM check. New tests cover offline multi-session catch-up; source-free replay;
model/event/feature identities and as-of; duplicate events/settlements; corrected
final reviews; stale writers/generations, lease expiry/takeover and clock rollback;
orphaned pre-commit objects; tampered bytes and matching-hash semantic corruption;
interruption, missing checkpoint/object, rollback/equivocation; simulated ENOSPC;
restore/pre-pointer failure and retry; no-overwrite; dependency-safe retention;
corrupt pointer/cache; local duplicate locks; restart; and host byte immutability.
AST regression verifies only the reviewed stdlib import set and no process/network
execution API. Exact source allowlist adds only module/test/this document, no wildcard.
All fixtures/staging directories close and disappear on test completion.

The existing Node test is a separate synthetic crypto primitive, not snapshot encryption.
Snapshots here are plaintext FAKE data and the transport is a trusted in-process fixture.
No signatures/provider authentication, AEAD envelope, real TLS/IAM, OS sandbox,
malicious filesystem/reparse race defense or power-loss durability is certified.
Hashes detect corruption relative to the trusted fixture; they do not authenticate
an attacker-replaced complete chain on a fresh client. Cryptographic manifest trust,
private persistence, least privilege and independent-host tests are required before
any actual input. No model validation/accuracy/ROI claims come from these tests.

## Observed synthetic measurements versus real-data estimates

Python3.13.16 on the current Windows machine, three independent runs/size. Full local
logs and raw measurements are outside the repo under the Phase8B evidence directory;
only aggregate metrics/hashes are published. Each event has two fake forecasts and
two fake settlements, across two committed generations. Timings include local disk,
not network/provider latency. These measurements cannot certify production throughput.

| Fake events | Generations | Initial / catch-up bytes | CAS bytes / cold SQLite bytes | Catch-up median s | Cold restore median s |
|---:|---:|---:|---:|---:|---:|
|20|40|4704 / 78586|83290 / 122880|0.3651|0.0597|
|100|200|4704 / 410868|415572 / 507904|1.8047|0.1807|

A first100-event benchmark exceeded its deliberately fixed synthetic lease clock
and failed closed. The demo now requests a lease spanning its requested clock range;
security lease checks/tests remain unchanged. The original failure log and original
measurements are preserved; benchmark-v2.json adds checkpoint-restoration metadata.
Any further measurements after code freeze are retained as new files.

Observed logical delta objects grow from83290 to415572bytes between20 and100 fake
events (~4154bytes/additional event including both streams). CAS storage retains the
whole chain; selecting only latest version pointers does not reduce that history.
The local client additionally stores a few duplicated version files and a scratch
cold-restored DB. Real observation/features/raw evidence can be orders larger.

Real planning scenarios, NOT measurements: at1000 future events, assume each model's
forecast body4?16KiB, feature bundle4?64KiB, combined source references/settlements
4?24KiB/event. That implies20?184KiB/event (~19.5?179.7MiB/1000) before indexes, raw
captures, encryption metadata, corrections and retained generations. Add source
objects separately; do not infer growth from historical backfill days. A future
approved adapter must measure actual payload sizes and full/delta dependencies.
Phase8A's226.44MB active DBs /2.97GB retained roots are reference inventory, not copied
or required by this simulator. The minimum future bootstrap must include all original
record IDs/bodies and necessary artifact/input lineage, then prove parity separately.

## Current Supabase/Vercel capacity and cost gates (read-only)

Provider metadata on2026-10-17 reconfirms existing Supabase organization Pro; sports
project database14763543699bytes,387public tables,0NCAAF-named tables,1storage bucket.
Only aggregate catalog metadata queried; no application rows/secrets or schema changes.
No dedicated NCAAF storage, policy or schema is assumed. Prefix absence is not a scan
of arbitrary generic rows. Existing Vercel project is Next.js/Node24.x; plan, invoices,
allocated capacity and remaining usage are not exposed by the inspected metadata.
The Phase8A production reference is unchanged by this work; no deployment was attempted.

[Supabase pricing](https://supabase.com/pricing) lists8GB/project disk,100GB file
storage and250GB egress on Pro. These are included allowances, not verified remaining
headroom in this shared account. A new paid-org project/compute may add charges.
[Spend Cap](https://supabase.com/docs/guides/platform/cost-control) covers specified
usage but excludes compute/opted-in add-ons; actual cap state is UNVERIFIED. Shared
resource exhaustion/caps could impair other sports. No quota or plan adjustment made.
[Vercel filesystem docs](https://vercel.com/docs/functions/runtimes) describe read-only
filesystems with temporary scratch, not durable SQLite; persistence/compute must be
external and a read-only projection adapter is still needed. Vercel pricing/headroom
and sport workload isolation need billing-owner verification before integration.
[Public standard Actions compute](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
may have no incremental minute charge; private/larger runners, cache/artifacts and
provider storage/API/egress costs are not assumed free. No recurring job is installed.
Supabase changelog was reviewed in Phase8A; no Supabase client/schema implemented here.

Zero additional recurring subscriptions is feasible as a conditional design objective
using already-paid spare capacity, not an established fact. Incremental charges can
be avoided ONLY if sufficient existing unused allowance/allocated compute is proven,
covered caps and all excluded costs are accounted for, no upgrades/add-ons are enabled,
and workload isolation passes. We cannot certify those conditions with current APIs.
No unconditional $0 claim or automatic paid fallback; HOSTED_READY remains false.

## Implemented / blocked / owner decisions

IMPLEMENTED/TESTED: minimum synthetic logical schema, versioned canonical deltas,
fenced atomic commit, offline-independent projection, read-only incremental client,
cold restore, version retention, fail-closed tests and reproducible benchmark command.

BLOCKED/PENDING: real hosted schema/adapter, authenticated/encrypted remote snapshot
transport, provider CAS/IAM/ACL proof, private artifact and source lineage storage,
actual OS/host failure/retention compaction tests, website integration/deployment,
current headroom/Spend Cap and incremental billing assurance. The prototype cannot
be pointed at real input by CLI and is not an activation path.

OWNER AUTHORIZATION: exact isolated synthetic hosted pilot account/destination and
budget/isolation approval; scoped identity/key custody and independent host; later
real bootstrap/parity and writer cutover; any migration/upload/production deployment,
merge, hosted scheduling/alerts, persistent Windows credential or Task Scheduler
registration. Each is separate; review/merging this draft does not authorize them.

Restart: preserve later branch changes; verify exact PR head and test source hashes,
run the four commands above. All demos/tests create fresh disposable roots, never
read original NCAAF state and never restore over it. Read local VERIFICATION.json
and evidence manifest for exact final SHA/log hashes; a source commit cannot contain
its own hash. No active worker remains after demo/test completion.
