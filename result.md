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
- **Committed Debugger Trace:** Win32 debugger harness `tools/windows-debug-trace.py` was executed and committed alongside raw trace `debug-trace.json`. The trace confirms process creation at base `0x7ff6c6d50000`, `ntdll.dll` mapping at `0x7ffbc5550000`, and immediate exit code `0xc000007b` before `kernel32.dll` maps or `PE AddressOfEntryPoint RVA 0x13d0` is reached.
- **Root Cause & Failing Module:** Unverified/unproved. The debugger trace establishes that failure occurs in early NT loader initialization, but does not identify the specific rejected module or header defect.
- **Pull Request #1:** Pull Request #1 into `main` is created and open at `https://github.com/chimmeyeswanthoficial-hub/openbot/pull/1`.
- **Release Status:** Retained strictly fail-closed: public release `false`; accepted pilot days `0`.

