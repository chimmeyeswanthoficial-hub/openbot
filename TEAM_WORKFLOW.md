# Shared repository workflow — Arena + Antigravity + owner

> **Current OpenBot OS history/reuse increment supersedes old repair/audit tasks.**
> Parent `cf2acb10530ab3c33c567bb9831c5d6dbe515349`; current full SHA is in the
> external history handoff receipt. Read `ANTIGRAVITY_NEXT.md` and
> `docs/openbot-os/WORK_ORDERS.md`. All c3/649/9f repairs are already incorporated.
> Optional authenticated human history now exists: 58 new cases, included in
> 473 gateway/journal passes +87 PG skips. No live Studio chat/provider/VM.
> Registry unchanged; old EXE/APK not rebuilt; release false; real pilot days 0.
> Old numeric audit/remote-branch facts below are historical unless explicitly
> revalidated in `evidence/openbot-os-history/VERIFICATION.md`.


## One shared source, not repeated folder replacement

Repository: https://github.com/chimmeyeswanthoficial-hub/openbot
Audited base: `5a98328bbd5a05646de14340a858f4debba24788` (main and repair branch matched at audit time).
Working repair branch: `repair/restore-manifest-files`. Use normal reviewed commits /
PRs into main. Do not force-push, reset/clean someone else's work, delete folders,
overlay private operating data, or merge an old UI over the current shared light UI.

A pushed commit is what both agents can inspect. Each handoff names the **full SHA**,
branch and changed paths. Fetch/review the newest SHA at the start of the next active
session. There is no invisible shared local directory, automatic collaboration,
continuous monitoring, or background progress after a chat turn ends.

## Current writer limitation — important

Arena successfully read and cloned the public repository, but a non-mutating push
check failed for lack of authenticated GitHub credentials. No remote edits occurred.
Do not send passwords/tokens through chat. Antigravity previously reported Git authentication; it must confirm it still has
the owner-approved credentials before publishing the prepared ordinary commit.

Arena's Git bundle is **commit transport**, not a second codebase or a patch chain.
It contains the new commit based on the audited SHA; the recipient already has the
base. Import it with Git and a fast-forward-only merge; never copy changed files by
hand or replace the laptop repository. If either branch advanced, stop on divergence
and exchange the new head SHAs. Do not resolve by a forced update.

## Checks appropriate to each representation

**Committed Git tree** (Windows or POSIX, local objects only):

```sh
python tools/verify-git-source.py --ref HEAD
```

This checks the committed manifest/digest, every blob's bytes/hash, all paths and
Git executable flags. It rejects symlinks/gitlinks and unknown committed files;
partial/promisor configurations are refused rather than fetching. It does not
install, authenticate, contact a server, execute project code, inspect untracked
private files, verify working-tree edits, or certify private filesystem permissions.
Run `git status --short` separately and never mistake HEAD verification for a review
of uncommitted edits. This identity verifier does not prove signer or human approval.

**Clean complete ZIP extraction:**

```sh
python tools/verify-source.py --strict
```

Use a mode-preserving extractor on POSIX. Git stores an executable bit, not 0600 ACLs;
ZIP/private filesystem checks remain separate. Do not weaken private BlueprintStore
or TLS checks to make a Git clone look like an approved runtime.

**Portable regressions:**

```sh
python -m unittest discover -s studio/tests -p 'test*.py' -v
python -m unittest discover -s tools/tests -p 'test*.py' -v
node --test studio/tests/*.test.cjs
node --test work/packages/bot-hq-queue/serial-queue.test.mjs work/tools/findrepo/test/*.test.mjs
```

Current bounded Linux results: **77 tools**, **51 Studio pass / 1 Windows-only
skip**, **70 Node**. Selected disposable gateway+journal: **473 pass / 87 explicit
PostgreSQL skips**, including 58 new history cases. The previous 1,251-pass whole
kernel result is historical; a current broader-media setup failed on missing host
libraries and was not relabeled as a full run. See the current verification packet
and `tools/KERNEL_TEST_PROFILE.md`; no blind installs or production test state.
Antigravity must return actual Windows results/skips, not copy Linux outcomes.

## Roles and next handoff

| Participant | Do now / return |
|---|---|
| Arena assistant | Lead architecture, compatible OSS reuse, authenticated history/agent adapter and scoped regressions; verify the ordinary source commit and one complete private workspace handoff. Review returned native evidence against its exact SHA. No unobserved Windows or public-release claim. |
| Antigravity | Preserve current working changes. Verify/import the prepared commit, push normally on repair branch, review/PR into main. Diagnose Windows using WINDOWS_LOADER_REVIEW.md: exact local hashes, actual error PNG and bounded Application/CodeIntegrity/loader evidence; identify failing module. Use an approved MSVC comparison only as an experiment, not a guessed required fix. |
| Human owner | Keep backups. Relay the bundle/commit instructions and Antigravity's new SHA/report/screenshot. Owner retains device/host/account/install/spend/privacy/signing/release permissions. No keys/passwords in chat or source. No new host purchase is needed merely to sync code. |

Only one agent should edit a particular file at a time. Before editing, announce
base SHA + intended paths; at completion give new SHA + paths + actual tests/skips +
remaining blockers. Do not overwrite another agent's newer report or source manifest.
After final file edits regenerate the full reviewed manifest, preserving approved
POSIX modes; run checks **last**. Post-export hashes/commit-handoff receipts stay
outside their own archive/commit to avoid self-reference.

## Immediate priorities (do not repeat resolved work)

1. Safely integrate/publish the current ordinary history/reuse commit; confirm both readers see its full SHA.
2. Diagnose and fix actual Windows startup; require real rendered light UI and
   interaction evidence. Restored Git executable flags do not fix 0xc000007b.
3. Owner-approved Android device and real Mac/Xcode work, then real-host/provider/
   VM/IDE/social engineering in the roadmap's dependency order. Stop for actual access.
4. Independent review/operations/protected evaluation/real pilot/human release remain.

A complete source tree is not a finished product. Public release false; accepted
genuinely observed pilot days **0**. No automatic paid CI, provider or deployment was enabled.
