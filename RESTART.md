# Recovery and restart ? offline only

1. Inspect the draft PR head and `git status --short`; preserve later work. The base
   is `980c596d11b21572388e08d36367bf34fed053c4`. Do not reset main or existing files.
2. Verify `audit/BASE_INVENTORY.json` against the baseline's Git blobs and
   `audit/FILE_INVENTORY.json` against the reviewed tree (inventory excludes itself). Use git_sha256 for Git blob
   bytes; sha256 records local bytes, which may differ under Windows CRLF checkout.
   The exact checkpoint SHA is `git rev-parse HEAD` and the draft PR head.
3. Use an available Python3 interpreter. Tested locally with Python3.13.16 and Git.
   Run `python -I -m unittest discover -s tests -v` and
   `python -I scripts/security_preflight.py`. Windows needs ordinary temp-directory
   access for disposable synthetic fixtures. No network/paid packages are needed.
4. Recheck observed settings read-only before future work; API observations are a
   timestamped snapshot. A denied/missing endpoint is UNVERIFIED, not PASS.
5. Keep templates disabled. Do not enable Actions, execute jobs, install workflows,
   generate keys/secrets, transfer data, create releases, publish Pages or schedules.
6. If a check fails, preserve its output, quarantine only the new synthetic work,
   inspect the diff and fix without weakening assertions. Do not access forecast
   archives to debug this preparation. Restore code only into a NEW directory from
   the reviewed Git SHA; there is no operational state or database to restore here.

The parent Sports Edge Hub checkout and NCAAF PR21 are read-only references in this
work. Existing62 PPG/59 Ridge forecasts and3 PPG settlements are not re-audited or
modified. No workers were launched; there is no scheduler to stop or production rollback
needed. To discard the proposal, leave the draft unmerged and preserve its Git history.
