# Collector repair after PR #1 at 89e9472

**This is a local collector correction, not a Windows application fix or native acceptance.**

Published PR reviewed: https://github.com/chimmeyeswanthoficial-hub/openbot/pull/1
Published head / repair base: `89e9472a460e4f674c4c587c012082f2d0b693f9`
Local candidate branch: `arena/recorder-repair-89e9472`

The external Arena review/receipt gives the candidate's full child SHA and transport checksum; a commit cannot embed its own identity. Arena has not pushed, merged, submitted a formal GitHub review, run Windows, or replaced any laptop folder. Import/publish only after reviewing the exact child commit and confirming that the PR branch has not advanced.

## What the review actually found

The published head genuinely fixes the old unmeasured entry Boolean: `entry_point_measured=false`, `entry_point_reached=null`. It adds API declarations, image/DLL file-handle cleanup, an event cap, attempted detach, a collection status, tests and a new trace. These are real improvements.

However, independent fake-only replay reproduces these v2 defects:

1. Failed `ContinueDebugEvent` on EXIT_PROCESS still sets `collection_status=complete`, skips detach and allows CLI exit 0. Non-exit continuation failure is also logged without stopping the loop. Existing T09 checks only for a log record, not failure propagation.
2. Every first-chance STATUS_BREAKPOINT is labeled initial and swallowed. A later application breakpoint receives DBG_CONTINUE too.
3. `CloseHandle` and `DebugActiveProcessStop` results are ignored. A failed close can still return complete/CLI 0; failed detach is not visible in the result.
4. The new tests mutate global `os.name`. On Linux this changes pathlib's platform selection: the exact published tools suite runs **41 tests with 13 errors and 1 failure**, exit 1. This does not refute a reported Windows pass, but the tests were not platform-independent as claimed.

The generic v2 diagnostic string also makes run-2-specific no-exception assertions for other traces. Bounds lack a monotonic total collection budget and bounded input validation. Existing output filenames could be overwritten.

## Changes in this candidate

Only the collector, its tests, this handoff and the manifest are changed. **All application/kernel/native binary/UI files and all original native evidence bytes remain unchanged from 89e9472.** No build/tool installation, provider access or security-policy change is included.

- Schema/harness version **3**, leaving v1/v2 recordings untouched. Entry execution remains unknown/unmeasured; no breakpoint is installed at PE entry or wWinMain.
- One continuation path: continuation failure stops collection with `continue_failed`, gives CLI 2, and attempts checked detach of the created target. Only successfully continued EXIT_PROCESS plus successful owned-handle cleanup can return complete/CLI 0.
- Cleanup results/exceptions are recorded, and later owned-resource cleanup is attempted even after an earlier failure. `event_collection_status`, `cleanup_status`, `cleanup_errors` and `debugger_detached` separate the outcomes.
- At most the **first** first-chance breakpoint is assumed to be debugger startup; subsequent breakpoints, second-chance exceptions and other exceptions are forwarded. Bootstrap identity is **not address-validated**. This assumption still needs a real native control and is not an entry probe.
- A 30-second default monotonic event-collection deadline complements the event cap and per-wait timeout. Waits are clipped to remaining time. Bounds are validated before process creation. These are event-loop/native-wait bounds, **not a hard deadline on every native API or a workload stop/reap guarantee**.
- Incomplete sessions attempt a checked detach, not termination. **A successfully detached target may continue running**. Failed detach leaves target/debugger cleanup uncertain; there is no process-tree sandbox/containment guarantee.
- 64-bit Windows pointer/DWORD/structure-layout checks reject unsupported interpreter ABI before binding. Target ISA is not independently inspected; the intended native workflow remains x64. Native WinDLL binding preserves last-error state. Oversize path-resolution results are treated as unresolved, not as valid truncated paths.
- Generic limitations describe the current recorder's capabilities rather than asserting historical run-2 events. CLI output uses exclusive creation and refuses existing files before launch. Use a new run identifier and filename.
- Tests replace the module-local OS reference rather than changing global os.name. T02/T03 now assert actual continuation arguments. T09 asserts incomplete status and detach. Sixteen additional counter-tests cover failed continuations, failed/raising cleanup, later/second-chance breakpoints, deadline, invalid bounds, wait API error, dynamic exception content, evidence overwrite refusal, ABI refusal, and collection-versus-target exit status.

## Checks actually run in Arena

| Tree / scope | Observed result |
|---|---|
| Exact published 89e9472 | Both source verifiers pass; 4,474 listed files, 4,475 blobs, 74,077,426 source bytes |
| Exact published 89e9472 tools, Linux | **41 run; 13 errors, 1 failure; exit 1**, independently repeated |
| Exact published 89e9472 Studio, Linux | 49 passed / 1 Windows-only skip, of 50 |
| Exact published 89e9472 Node | 70 passed |
| Local repaired tools, Linux | **57 passed** = 25 existing source/export tools + 32 recorder tests |
| Local repaired Studio, Linux | 49 passed / 1 Windows-only skip, of 50 |
| Local repaired Node | 45 Studio + 25 retained = 70 passed |
| Changed Python files | Ruff check and format pass |

The external receipt records final source verification and transport checks after the manifest/commit is frozen. Neither these fake tests nor the independent fake replay are Windows ABI/loader execution evidence. The relayed Windows tools 41 / Studio 50 / Node 70 results concern the **published v2 head**, not this v3 candidate. Run the candidate's checks on Windows and report actual outcomes; do not copy Linux counts as a Windows rerun.

## Artifact/report corrections still needed on the Windows side

- Keep run-1 and run-2 raw artifacts. At 89e9472 run-1 received a new `recorder_limitation_note`: all earlier parsed field values remain, but it is **not byte-for-byte unmodified**. Correct the report's “preserved as-is” wording in a new explanatory report/addendum rather than rewriting raw observations again.
- Run-2 is labeled `2026-11-18T20:29:25+05:30`; the reused event-query window is 17:00–19:45 that day. Those negative queries are historical context, **not run-2 coverage**. Collect an appropriately scoped window, including query errors/channel status, or explicitly label the old window. Arena has not independently validated the Windows host's wall clock.
- The three-event run-2 records CREATE_PROCESS, an ntdll LOAD_DLL notification, and exit 0xc000007b. It has no exception or kernel32 load notification. It does not identify the rejected image/header, exact failing instruction or whether entry executed. A successful collector exit 0 is not a successful application launch.

## Antigravity: next action

1. Keep PR #1 and all local work/backups. Confirm a clean working tree and exact current head 89e9472 before importing the accompanying ordinary child commit. **Stop on any divergence or uncommitted work**; do not reset, clean, force-push, delete folders, or copy changed files over a newer checkout.
2. Verify the bundle and candidate SHA against the external receipt. Inspect the four changed paths and use a **fast-forward-only** merge into `repair/restore-manifest-files` if it is still exactly based at 89e9472. The bundle is Git commit transport into the existing complete workspace, not a replacement codebase or source ZIP.
3. Run both source guards, tools, Studio and Node checks on Windows. Use the repo workflow commands. Confirm native API/handle behavior with an already approved benign x64 control, then the existing failing executable, under **new** run IDs/output filenames. Explicitly report collector status, CLI exit, target exit, cleanup/detach status, architecture, hashes and event times separately. A fake pass cannot accept native behavior.
4. Correct the report/provenance/time-window wording in a new explanatory record. If further evidence needs an installed diagnostic or build tool, request the owner's specific host/setup approval first. No guessed MinGW/TLS/MSVC/signing fix, arbitrary DLL replacement or disabled security controls.
5. Regenerate the manifest after any additional reviewed files, retain approved modes, run guards last, and push normally to the existing PR branch. Return the **new full head SHA**, changed paths and actual test/native-control results. Do not claim the Arena-only candidate was already published.

## Owner and Arena

**Owner:** relay the review and commit transport; retain the current complete workspace/backups. No new folder replacement, credentials, signing purchase, paid infrastructure or new ZIP is required for this diagnostic step. The final delivery goal remains one complete clean workspace/codebase, not a manual patch chain.

**Arena:** review the returned published SHA and new native artifacts. The independent review applies to 89e9472; this implementation is a separately identified local candidate and is not independent acceptance of its own native behavior. There is no background sync or direct Antigravity message.

The requested light Windows/Android/iOS companion and R01–R13 remain in scope, including real provider/PC/IDE/official-social work and independent security, operations, protected evaluation, genuine pilot and human release gates. **Windows/native acceptance remains blocked; public release false; accepted genuinely observed pilot days 0.**
