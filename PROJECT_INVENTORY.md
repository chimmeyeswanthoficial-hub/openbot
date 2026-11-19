# Project source inventory — shared-repo-audit-1

> **OpenBot OS foundation supersedes the old “publish the eight flag fixes” task.**
> Start with `OPENBOT_OS.md` and `docs/openbot-os/WORK_ORDERS.md`. Base review is
> `9f5600d1fd285e79922fbf69a2abce5243cb9291`; historical c3/649/9f work is already
> incorporated. Do not re-import an old repair bundle or replace the laptop folder.
> Counts/receipts and role assignments below describe earlier checkpoints unless
> explicitly revalidated in `evidence/openbot-os-foundation/VERIFICATION.md`.
> The new journal is standalone, registry unchanged, EXE/APK not rebuilt, release false.


## Direct answer: is the current project code on GitHub?

At audited commit `5a98328bbd5a05646de14340a858f4debba24788`, **yes, all files in the verified shared source baseline
are present on both main and repair/restore-manifest-files**. Both branches point to
the same commit. The earlier 258-file omission is resolved. Independent file-content
checks found 4436 manifest-listed files plus the manifest, no missing/unlisted paths,
and a valid aggregate digest. This does not establish the existence of unshared or
uncommitted laptop files, private runtime backups, or every future requested feature.

The audit found **eight lost executable flags**, not missing files. This change
restores those Git index modes to the existing approved source manifest. It does
not change EXE bytes or fix Windows error 0xc000007b. Git cannot represent the 0600
permissions of 46 selected source files: that is why committed-tree verification
and private runtime/filesystem acceptance must be kept separate.

## Baseline file counts (before this new audit commit)

| Top-level group | Manifest-listed files |
|---|---:|
| `(root files)` | 13 |
| `control` | 45 |
| `evidence` | 186 |
| `studio` | 36 |
| `tools` | 7 |
| `work` | 4,149 |

`SOURCE_MANIFEST.json` is the complete current per-file inventory; this table is a
pinned baseline snapshot, not a count to update by guesswork. New helper/docs/evidence
in this successor are added explicitly at the final manifest freeze.

## Structure and actual role

```text
OpenBot-Workspace/
  studio/                  shared light interface, pure planner/server, original tests
  control/                 Windows/Android/iOS shells, SDK build scripts, test artifacts
  work/
    services/              preserved gateway, ledger, worker, sentinel, media code
    apps/                  retained local console/source
    packages/              bounded adopted modules, including local serial queue
    scripts/               isolation/media/work/operations/bootstrap and tests
    tools/                 retained findrepo and scoped tools
    .openbot/              selected declarative routines/venture only, not live state
    third_party/           scoped donor sources/notices/provenance
    repos/OpenBot/         all 3475 optional upstream source files; not auto-integrated
    audit/ docs/ company/  contracts, locks, source reviews and engineering records
  tools/                   source/ZIP/Git identity checks and synthetic test preparation
  evidence/                scoped synthetic/local receipts and attributed external reports
  TEAM_WORKFLOW.md          source-of-truth/branch/commit and role handoff
  ANTIGRAVITY_NEXT.md       exact current Windows/operator work order
  PUBLIC_RELEASE_ROADMAP.md all R01-R13 requirements and remaining external gates
```

## Audit coverage and limits

The name/content/size/mode inventory covers every manifest-listed file. The active
source boundaries inspected include the public stateless Studio handler, scoped
P-256 pairing/nonce/one-use exact approval bridge, fixed-owned no-provider effect
path, native navigation/host-object controls and manifest/export/build tooling.
Current tests exercise the preserved service/script suites and bounded donor units.
The 3475 optional upstream files are byte-preserved, not newly certified line by
line or fully integrated; their own complete build/test suites were not run.
This is not a comprehensive independent security/license/feature certification.

A fresh disposable whole-tree kernel run, using already cached and hash-verified
mode-0755 Bubblewrap plus the reviewed 213-file real FFmpeg/library lock, returned
**1251 passed, 173 explicit PostgreSQL skips, zero failures/errors**, with one test
client deprecation warning. No network install, real provider or production DSN
was used. The initial unconfigured run's 37 failures/18 errors are preserved and
explained by the absent mandatory pinned tool/media selection, not hidden or fixed
with a host fallback. See tools/KERNEL_TEST_PROFILE.md before reproducing.

## What is not missing source versus not finished functionality

| Area | Actual current boundary |
|---|---|
| Shared UI | Same light desktop/sidebar/chat/computer-routines and mobile list-to-chat payload. Local human briefs are not live AI replies. |
| Kernel path | Authenticated fixed-owned invoice-QA fixtures with exact approval/execution/artifact read-back. Not arbitrary companion execution or production staging. |
| Reuse | Attributed bounded OpenMuse CSV port and preserved queue/findrepo modules; other optional source availability does not mean integration. |
| Windows | Source and unchanged unsigned test PE present. Reported real 0xc000007b startup failure is **unresolved**; native rendering/device acceptance absent. |
| Android / iOS | Demo Android APK without device acceptance; iOS source only, no Mac/Xcode build/IPA. |
| Real providers / PCs / IDEs | Not operational: actual provider cost evidence, guest VM provisioner, eligible installed/authenticated IDE sessions and independent host controls remain. |
| Official social | Draft review/checklists only; approved official OAuth/publish/read-back/stop integrations remain. |
| Release | Independent reviews, real operations/evaluation/pilot/signing and exact human release remain. Accepted real observed pilot days 0. |

Private operating databases, tokens, signing keys, SDK/dependency caches, uploads and
unique recovery archives are intentionally **not** pushed as source. Their exclusion
is not permission to delete them or a claim that this repository backs them up. No
source omission was repaired by importing old secrets/state or merging an old UI.
