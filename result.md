# Shared repository audit — shared-repo-audit-1

Base commit: `5a98328bbd5a05646de14340a858f4debba24788`. This is Arena's technical/source audit, not independent
security acceptance or Windows runtime proof. Original Antigravity report is
preserved unmodified at `evidence/shared-repo-audit/antigravity-report-5a98328.md`.

## Findings and changes

- Both main and repair branch held the complete baseline: 4436 manifest-listed
  files plus the manifest, no missing/unlisted paths, all file hashes and aggregate
  digest checked. No repetition of the 258-file restoration is required.
- Eight source executable flags were absent in Git. Restored the existing approved
  modes without changing file contents. This matters to POSIX checkouts, **not**
  the unresolved Windows loader failure.
- Added local committed-tree verifier `tools/verify-git-source.py` with 15 synthetic
  Git tests. It validates source hashes/digest/paths/executable flags, refuses partial
  clones/symlinks/gitlinks/unlisted files and never fetches. It explicitly does not
  certify working edits, private ACLs, runtime safety, native devices or release.
- Added `PROJECT_INVENTORY.md` and `TEAM_WORKFLOW.md`; corrected current handoff/native
  status and report claims. No live service, provider, real VM/IDE/social account,
  paid CI, signing purchase, remote deployment or release was enabled.
- Authenticated push is unavailable in this Arena session. A tested ordinary local
  commit/bundle is supplied for Antigravity to fast-forward and push. No GitHub write
  was performed by Arena. Exact publication status comes from actual remote refs,
  not this pre-commit report. Do not send tokens in chat.

## Verification

Linux Studio: 49 passed + 1 Windows-only skip of 50. Tools: 25 passed (handoff10 +
Git15). Node: Studio45 + retained25. Native binary/assets/static checks: 27 passed,
not native launch proof. Selected Python lint/format clean. Logs/initial failures
and scoped audit are in `evidence/shared-repo-audit/`. Final committed-tree and ZIP
extraction/re-export receipts are external to avoid self-reference.

Current disposable configured kernel: **1251 passed, 173 PostgreSQL skips, zero
failures/errors**, one test-client deprecation warning. Already cached pinned
Bubblewrap and 213 FFmpeg/library hashes were verified before selection; actual
fixed-namespace cases ran. No network install, production DSN or provider was used.
The initial unconfigured run (37 failed, 1168 passed, 201 skipped, 18 setup errors)
is retained: mandatory isolated-tool/media selections were absent, as the existing
KERNEL_TEST_PROFILE.md warned. No source assertion was removed and no PATH/host
fallback was added. PostgreSQL tests were not run and remain skips.

The prior Git-test red was a case-sensitive expected error regex; the refusal itself
worked. It was corrected without weakening the source/security validation. Fresh
Git-checkout strict-file-verifier failures were reproduced (missing approved modes,
then unlisted .git metadata after local chmod). They are different representations,
not absent source or reason to loosen private filesystem acceptance.

## Windows failure remains open

Antigravity reports 0xc000007b. No raw new Windows error image/trace was supplied to
Arena. The specific MinGW/TLS/relocation explanation is not established. The README
did not require MSVC/signing to launch; signing is not a measured fix for this error.
The supplied EXE/loader are both AMD64. See `WINDOWS_LOADER_REVIEW.md` for exact hashes
and the next diagnostic work order. The previously delivered verified-complete archive is 20315026 bytes
for SHA256 c96dbbe947d96fe987658f125cc01a45fcf682b9721dc0d75d52ffd129436e87,
not the larger byte count in the preserved imported report.

Current EXE and Android APK bytes are unchanged; iOS is source only. No native
acceptance was awarded. R01-R13 external gates remain in PUBLIC_RELEASE_ROADMAP.md.
Public release false; accepted genuinely observed pilot days **0**.

### Follow-up diagnostic update (Windows 11 host)

- **Screenshots Delivered & Verified:** `error.png` and `desktop-context.png` are present in `evidence/windows-launch/windows-11-26300-x64-run1/` confirming the physical modal dialog `OpenBot-Control-Local-x64.exe - Application Error` with `0xc000007b`.
- **Harness v3 & Regression Suite:** Imported Arena's collector repair commit `c3d420b` (harness v3 / schema `openbot.windows-debug-trace/3`). 57 tools tests pass on Windows 11 host (25 existing + 32 recorder unit/regression tests).
- **Benign Control Validated:** `C:\Windows\System32\whoami.exe` traced under debugger (`evidence/windows-launch/control-whoami-x64/debug-trace.json`). 29 events recorded: sequential loading of `ntdll.dll`, `kernel32.dll`, `KernelBase.dll`, `advapi32.dll`, `msvcrt.dll`, and 15 additional libraries (20 DLLs total, 21 module entries total); startup breakpoint handled; normal process exit `0x0`; cleanup ok.
- **Target Launch Trace (Run 3):** For OpenBot run 3 the v3 recorder recorded `CREATE_PROCESS`, an `ntdll.dll` `LOAD_DLL` notification, and `EXIT_PROCESS 0xc000007b` (`evidence/windows-launch/windows-11-26300-x64-run3/debug-trace.json`). No `kernel32.dll` LOAD_DLL or exception notification appears in this recording. Entry-point execution was not instrumented (`entry_point_reached=null`, `entry_point_measured=false`), and no failing instruction or stack was captured. Cleanup ok; collector exit 0.
- **Provenance & Scoping Notes:** Run-1 trace preserves its raw observations and `recorder_limitation_note` in Git history. Bounded event query records (17:00–19:45 IST) represent historical reproduction context, not temporal coverage of subsequent runs.
- **Root Cause & Failing Module:** Unverified/unproved. This pattern is consistent with early initialization failure, but the exact stage, rejected image/header element, whether kernel32 was ever mapped, and whether PE entry or wWinMain executed remain unproved.
- **Pull Request #1:** Open at `https://github.com/chimmeyeswanthoficial-hub/openbot/pull/1`.
- **Release Status:** Strictly fail-closed: public release `false`; accepted pilot days `0`.

