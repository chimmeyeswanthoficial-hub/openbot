# Antigravity — current OpenBot OS handoff

**Read this, not the historical “eight flag fixes” or repair-bundle instructions.**
This increment is an ordinary successor of
`cf2acb10530ab3c33c567bb9831c5d6dbe515349`. The full new SHA, bundle prerequisite and
final source/transport guards live outside this commit in
`deliverables/OPENBOT_OS_HISTORY_RECEIPT.json` in the complete private workspace.
If you only have this repository, request that receipt and the current full SHA.
The source of truth for implementation is `OPENBOT_OS.md`; work ownership/exit
criteria are in `docs/openbot-os/WORK_ORDERS.md`.

## What Arena actually completed

- Opt-in **signed-device human history API** through the existing governed gateway,
  with dedicated SQLite persistence, server-derived gateway/venture/actor scope,
  explicit history capabilities, human-owner writes, content-free pre-access audit,
  revocation fencing and stable-ID reconciliation after uncertain completion.
- **58 new history cases**, included in **473 passed / 87 PostgreSQL skips** across
  the selected gateway+journal suite. One real synthetic-CA TLS socket case; most
  HTTP cases are ASGI. Not a whole-kernel, native or independent acceptance result.
- Actual reuse of the exact pinned MIT **AG-UI 1.0 schema/license** for offline
  CUSTOM-event tests. No full SDK/runner/live stream/provider integration claim.
- All four requested source families covered in the **40-feature reuse ledger**.
  Current reviewed Nightly code remains Noncommercial and excluded. Historical
  v0.1.11 has a verified Apache-2.0 LICENSE but no cleared/imported modules.
- Preserved the approved light UI, kernel, original history/recovery and old native
  diagnostic bytes. Fresh public-planner Chromium smoke: **21 grouped checks**.

The history API is **off by default**, not connected to Studio chat and not a live
agent. No model, VM, IDE, official social account, bank or real user was connected.
First-party MIT does not clear every dependency/service/binary/brand.

## 1. Safe intake/publication — first

1. Record the existing full HEAD, branch and `git status --short`; preserve local
   changes, refs, original source, private state and backups. **No folder deletion,
   reset/clean/forced update or file-by-file overlay.**
2. Verify the supplied full commit, parent, bundle hash and changed paths against
   the external receipt. Use the receiver instructions in `deliverables/README.md`.
   The current transport can include both the foundation and this successor from
   the reviewed `9f5600d…` ancestor; do not separately re-import c3/649 repairs.
3. Only fast-forward when a clean receiving branch is an ancestor of the expected
   head. If advanced/diverged, stop and return its full SHA; reconcile normally in
   a review branch without discarding either writer's work. Do not blindly cherry-pick.
4. Run the actual source/portable checks below on the actual platform. Publish only
   through existing authorized Git credentials to a review branch/PR; return full
   head/base SHA, PR URL, changed paths, clean status, raw logs/skips and blockers.
   A prepared bundle or pushed review head is not a merged/public product release.

Arena has no authenticated remote writer here. **Direct Antigravity connector
lookup returned unsupported**; this file is a prepared relay, not proof of delivery,
a running external team or progress after an active session ends. Do not put Git
credentials in chat or claim legal/release authority delegated by this document.

## 2. Parallel implementation streams

### Backend/frontend — W01/W03

Read `AUTHENTICATED_HISTORY.md` and inspect `conversation_api.py`, the locked
history admission in `control_api.py`, and their tests. Extend the existing API,
not an unauthenticated journal/demo endpoint or a second authority.

1. Connect actual Studio history UI with scope/expiry/revoke handling, plain-text
   rendering, bounded cache, pagination and loading/error/retry states. The old
   renderer deliberately does **not** yet accept history-capability pairings; add
   that support with explicit contract tests, not an allowlist bypass.
2. Compare a compatible pinned MIT CopilotKit runtime/local runner and implement
   one AG-UI adapter with one authoritative history/execution owner. Do not invent
   a duplicate agent loop or treat arbitrary client events as assistant/tool authority.
3. Prove run/message/tool correlation, disconnect/replay, cancellation, uncertain
   completion, revocation, cross-scope denial and no duplicated effects. The old
   owned-QA custom SSE fixture is not complete AG-UI 1.0.
4. Tombstones/lifecycle/old-cursor semantics, export/delete/backup retention, genuine
   organization tenancy and PG history remain separate reviewed changes. Deletion
   today is logical, not secure erasure. Never reuse deleted thread IDs.
5. A real provider requires an approved account/host, allowed data and explicit
   hard exposure/cost cap plus mandatory broker controls. Do not fabricate a live
   result, use production tokens as fixtures or silently enable billing.

### Native/host — W02/W04

- Preserve existing EXE/DLL/APK hashes and original Windows evidence. Windows
  `0xc000007b` root cause/startup is still unresolved. `LoadLibraryExW(EXE)` does
  not test static imports. No guessed DLL/TLS/MSVC/signing replacement.
- The debug-string probe is unbuilt/unrun source; schema-4 capture is fake-tested.
  Read `WINDOWS_DEBUG_TEXT.md`. **IFEO/loader-snaps/registry and tool installation
  are not approved**: the owner answered “I don't know.” Request specific bounded
  consent before a host change; no security bypass/random DLL downloads.
- Use an already approved actual Windows toolchain/device to obtain rejected-image/
  path/status/stage and genuine ANSI/Unicode byte-count/cleanup evidence. Return
  an honest blocker if that host/tool permission is absent.
- Then rebuild current shared HTML/native packages as separately hashed artifacts;
  verify actual light-UI launch/interactions, keyboard/DPI/accessibility/lifecycle.
  Android and iOS need actual approved devices/Mac/Xcode/signing/update/rollback.
  Old EXE/APK still embed the older UI and are not new OpenBot OS releases.
- Preserve real per-bot VM/microVM, Claude Code/Antigravity/T3Code and official
  X/Instagram/YouTube scope. Containers/folders/screenshots are not real PCs.
  Only authorized accounts/hosts/installs/spend/actions; secrets stay out of source.

## 3. Genuine real-world sequence — W05

Read `REAL_WORLD_ROLLOUT.md` and `REAL_WORLD_PILOT_STATUS.json`.

**Engineering + independent readiness → authorized private real-world launch →
first month with ≥30 consecutive genuinely observed days → independent review/
owner expansion approval → six additional calendar months → final review.**

Both phases are **unstarted; accepted days 0**. Unit tests/demos/idle dates do not
count. No launch date, real on-call, evaluator, users or unattended execution exists.
Retain all R01–R13 and exact human public-release/signing/account/cost/consent gates.

Existing `evaluation_controls.Assessment` v1 has a single frozen candidate/policy
and ≤180-day limit. Design/review a **versioned phase/build-transition, signed
reapproval and evidence-continuity extension** before using it for this sequence.
Do not silently raise limits, flip fixture mode, pool changed builds as one frozen
cohort, treat 180 days as six calendar months or self-award observed days.

Freeze ≥20 independent held-out representative tasks, baselines, criteria, caps
and stop rules outside bot-writable source. Upgrade one bounded area at a time,
rerun affected checks, canary/rollback and retain actual incidents/cost/outcomes.
Independent qualified reviewers and a real consenting on-call must accept their
roles. Nothing here establishes “better than upstream” without that comparison.

## Checks and return format

```sh
python tools/verify-git-source.py --ref HEAD
python -m unittest discover -s tools/tests -p 'test*.py' -v
python -m unittest discover -s studio/tests -p 'test*.py' -v
node --test studio/tests/*.test.cjs work/packages/bot-hq-queue/serial-queue.test.mjs work/tools/findrepo/test/*.test.mjs
```

Fresh Arena Linux portable outcomes: **77 tools; 51 Studio +1 Windows-only skip;
70 Node**. Actual Windows outcomes/skips must be returned, not copied. Scope all
claims to the logs in `evidence/openbot-os-history/VERIFICATION.md`.

Kernel/history: NEW disposable **whole source layout**, `control/` beside `work/`,
explicit synthetic state, reviewed handoff/control locks plus optional
`work/requirements.agui-test.lock.txt`. Read `tools/KERNEL_TEST_PROFILE.md` and
`AUTHENTICATED_HISTORY.md` first. No production DSN, private runtime restoration,
automatic install, fake tool binary or weakened hash/TLS/source guard. The current
Linux x86_64/Python 3.13 schema-tool wheel lock is not Windows portability proof.
Full-kernel media setup failed on missing host libraries; preserve that failure,
do not pretend the complete profile ran or install host packages speculatively.

One writer owns the final manifest refresh. Return one ordinary successor commit,
source guard, actual test commands/environment/counts/skips/raw evidence hashes,
changed paths, remaining blockers and permissions used. Whole-workspace delivery
is private; a source-only export or commit bundle is not a private-state backup.
No public release, native acceptance or real observed pilot is self-approved here.
