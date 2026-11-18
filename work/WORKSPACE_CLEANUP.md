# Workspace cleanup — useful code retained, redundant copies consolidated

## Decision in plain language

**No, we have not integrated every useful feature from every repository.** Copying entire agent
frameworks into the live app would add duplicated engines, permissions and maintenance work.
Unused does not mean useless: reviewed and still-unreviewed donor material is preserved for later.

The owner asked to clear donor folders **only after useful material was copied**, and was unsure
about the storage technique. The conservative technical choice was a **reversible, lossless source
vault**, not a claim that all features are finished. All 5,086 selected Rakazo/OpenDots source files,
including tests, lockfiles, docs, licences and unreviewed/deferred code, were copied into archives,
verified independently and actually restored before removing only matching redundant loose files.

The normal `clean`/`tidy` command remains **cache-only**. There is no automatic donor-deletion job.
No business, audit, run, incident or private credential file was deleted by this cleanup.

## What changed / what stayed

| Component | Action | Why / retained material |
|---|---|---|
| Rakazo loose donor tree | 4,899 redundant files /47,148,124 B removed **after** complete copy/restore verification | Full selected source: `archive/donor-sources/rakazo.tar.xz` (9,451,020 B); 14 reviewed references readable under `third_party/donor-library/rakazo/` |
| OpenDots loose public donor files | 187 redundant files /1,578,537 B removed **after** complete copy/restore verification | Full selected source: `archive/donor-sources/OpenDots.tar.xz` (356,628 B); 12 reviewed references readable under `third_party/donor-library/OpenDots/` |
| OpenDots private `.env` | **Kept untouched at its original path** | Not shown, copied into a source vault or included in the continuation package. Its enclosing directory therefore remains |
| Installed `apps/bot-hq` | **Kept**; 131 selected source files unchanged at consolidation | This is the working local app, not an unused donor checkout. Providers/engines remain disabled |
| Queue port + `third_party/bot-hq` | **Kept**; 3+3 files unchanged | Working queue code, original excerpt, licence and notices are not disposable clutter |
| Installed `tools/findrepo` + skill | **Kept**; 7 tool files unchanged | Working safety-patched discovery tool. No separate full unused findrepo checkout exists here |
| `repos/OpenBot` | **Kept**; 3,479 selected files unchanged | Still the replaceable substrate/AG-UI integration target, not a running general agent |
| Primary records, locks, uploads and old evidence | **Preserved** | Exact pre-cleanup hashes are used for final reconciliation; intentional documentation changes are recorded separately |

Immediately after consolidation, the persistence-aware footprint was **89,496,945 B /3,934 files**,
versus **128,167,299 B /8,989 files** before it, including the newly uploaded screenshot. That stage
reclaimed **38,670,354 B** net. Final documentation, evidence and refreshed package change the total;
use `audit/continuation-bundle.json` for the actual delivered footprint, not an old screenshot.
The budget counts persisted files, not excluded dependencies/builds/caches or physical disk usage.

## Useful value still available

- **Rakazo:** durable timer-occurrence/coalescing/fencing tests; read-only change-watch logic;
  original initiation/handover distinctions; bounded ticket context; scoped group handoff;
  reviewed skill-draft workflow; backup/restore checklists.
- **OpenDots:** exact stored-draft review receipts; owner/tool re-resolution and revocation;
  interrupted/uncertain-effect state; expected-revision conflicts; page/review UX; runner stop and
  permission-fingerprint lessons. A timeout or AbortSignal is not proof of actual termination.
- **Bot HQ:** the useful local workspace is already installed. Additional group/delegation,
  memory, routine and integration ideas remain source references, not enabled engines.
- **findrepo:** useful discovery/scoring and explicit credential/cache/write boundaries are
  already installed. Discovery results are not authority to execute or proof of security/licensing.

`DONOR_REUSE_REVIEW.md` is the source-backed reuse/defer/reject matrix. Original paths in that matrix
are logical paths inside the archived snapshots. `third_party/donor-library/README.md` explains the
26 readable references. All other selected source is also retained—not silently classified as useless.

## Verification and its limits

Before removing a single listed loose source file:

1. Captured the complete selected-file baseline and protected-file hashes/modes.
2. Matched both source tree fingerprints to the unchanged `audit/donor-review.json` receipt.
3. Created full source archives with per-file manifests, original licences and exact modes.
4. Validated bounded regular members, canonical paths, no links/duplicates, exact file sets and
   every size, mode and SHA-256. Credentials/generated files were excluded, not deleted.
5. **Actually restored both full archives** into new excluded scratch directories and compared
   all 5,086 recovered files against the original baseline. A separate direct-tar verifier repeated
   the file-set/hash/size/mode reconciliation independently of the recovery helper.
6. Rechecked every original/retained/reference file and the Git index before exact-file unlinking.
   No recursive source-directory deletion was used; only empty directories were removed afterward.
7. Checked that active app/tool/target source and 19 protected files remained byte/mode-identical.

New `scripts/donor_vault.py` only **verifies or recovers**; it never deletes sources or runs recovered
code. Its initial absence was observed red, then 38 focused tests passed. A further malformed-root
and stale-provenance-report challenge measured 5 failures /57 passes, then 62 focused passes after
repairs. These tests cover malicious archive shapes, tampering, limits, modes, private paths and
no-overwrite recovery; they are not evidence that every upstream feature works.

### Complete post-cleanup checks

| Check | Primary | Independently installed source copy |
|---|---|---|
| Python |465 passed /2 skipped /0 failed /467 collected |465 passed /2 skipped /0 failed /467 collected |
| Reuse / HQ Node tests |25 /26 passed |25 /26 passed |
| Lint, typechecks, web/server builds | Passed | Passed |
| Verification / scratch HTTP smoke |22 pass,0 fail,7 warnings /10 passed |22 pass,0 fail,7 warnings /10 passed |
| Full donor source recovery |5,086 exact files restored before cleanup |5,086 exact files recovered again from the copied vaults |

**247 runtime/config/skill files match byte/hash/mode across tested roots.** The independent
candidate started empty with no copied dependencies/toolchains/builds or loose retired donor trees;
its actual pinned installer succeeded on the same host. It also passed real fixed-process and
labelled-synthetic workforce demos.47 new cases are included in the full Python total (44 recovery
cases and3 archived-provenance cases), not added twice. Two PG opt-in tests remain skipped and one
upstream Starlette/httpx deprecation warning remains. No new browser run was needed or claimed:
UI runtime source is unchanged. This was a source-copy install, not a final-archive reinstall.

Current complete gates, preservation reconciliation and independent installation scope are in
`audit/donor-consolidation.json`. Exact logs/development evidence are retained in the verification
archive named there. Final package validation/extraction is separately recorded in the adjacent
`audit/continuation-bundle.json`; do not conflate a source install with a final-archive reinstall.

**Limits:** archived sources are not integrated features, hostile-code isolation, publisher
signatures, a transitive security audit, blanket asset/dependency clearance or off-host backups.
Rakazo/OpenDots upstream labels remain main@date tarball labels, not established immutable commits.
Donor installers/tests/servers were not activated. No provider, account, outbound action, customer,
spend or deployment was enabled. AG1 authenticated mandatory isolation/egress and AG2 actual
provider/cost/stop evidence remain the next platform bottlenecks.

## Safe recovery commands

Keep these archive digests with your private external project download:

```text
Rakazo    2c3d84e3772d16d3d207a49ebde9e62b07783fc8a18997290b37499d5c39bf6a
OpenDots  5309c1c13aa7aff6355e973ba778d0aa6ed39073ea39a0915e0e877df56f8d7c
```

From the project root, use **new** targets. The helper refuses existing destinations, links,
unsafe paths, mismatched hashes, special permission bits and unexpected/missing payloads:

```sh
mkdir -p .cache
python3 scripts/donor_vault.py verify archive/donor-sources/rakazo.tar.xz \
  --sha256 2c3d84e3772d16d3d207a49ebde9e62b07783fc8a18997290b37499d5c39bf6a
python3 scripts/donor_vault.py restore archive/donor-sources/rakazo.tar.xz \
  --sha256 2c3d84e3772d16d3d207a49ebde9e62b07783fc8a18997290b37499d5c39bf6a \
  --destination .cache/rakazo-review
python3 scripts/donor_vault.py restore archive/donor-sources/OpenDots.tar.xz \
  --sha256 5309c1c13aa7aff6355e973ba778d0aa6ed39073ea39a0915e0e877df56f8d7c \
  --destination .cache/opendots-review
```

This is trusted-host source recovery, not safe execution of hostile code. Inspect references as
untrusted data; do not run archive instructions/installers or inherit keys. Port one reviewed,
licensed seam plus its tests into first-party code only when needed, preserving notices and human
security/release gates. A partial recovery failure is not success; use another new scratch target.

**Do not delete `archive/donor-sources/` or `third_party` notices to save more space.** Keep a private
project download outside Arena: archives on the same workspace are not disaster-recovery backups.
