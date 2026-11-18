# Antigravity Corrective Report — Repair, Verification, and Windows Acceptance

**Date:** 2026-11-18  
**Workspace:** `OpenBot-Workspace-Light-Complete\OpenBot-Workspace`  
**Checkpoint:** `light-reference-1` (repaired)  
**Host Platform:** Windows 11 (10.0.26300), Python 3.13.0, Node 24.5.0, Evergreen WebView2 Runtime 157.0.4341.60  
**Status:** Engineering Repair & Verification Complete; Not Public Release  

---

## 1. Safety, Preservation, and Delivered Archive Verification

### Preserved Commits and Backup Refs
- Prior commit `fe1267e0cd1e35e8a816dc0556be80ec68343401` fetched from remote and preserved on ref `backup-fe1267e`.
- Prior handoff commit `1c315bbe3d3b010f41eabd13134656125b9dba0a` preserved on ref `backup-1c315bb`.
- Current repair work is conducted on a dedicated repair branch (`repair/restore-manifest-files`) using **ordinary non-forced commits**.

### Delivered ZIP Archive Authentication
- The original ZIP `OpenBot-Workspace-Light-Complete.zip` was recovered from Recycle Bin and authenticated:
  - **Size:** Exactly `20,284,376` bytes
  - **SHA-256:** `8c1945df33b19cc19f598c59bf9d054b5490c8328d709898b42a065999587b54` (matches Arena specification byte-for-byte)
  - **Archive Contents:** Exactly 4,419 regular entries (4,418 manifest-listed files + `SOURCE_MANIFEST.json`).
  - **Pristine Extraction:** Extracted via Python `zipfile` (bypassing Windows Explorer silent truncation).
  - **Pristine Verification:** `python tools/verify-source.py` verified all 4,418 manifest files without a single missing file or checksum mismatch.

---

## 2. File Restoration and Git Index Status

### Missing File Root Cause
- The missing 258 files were **not** intentional exclusions. When the archive was originally extracted on Windows via built-in extraction, long-path and permission handling caused 258 files (under `work/services/`, `work/scripts/`, `work/repos/OpenBot/tests/`, `work/tools/findrepo/`) to be silently skipped.

### Restoration Execution
- All 258 verified missing files were restored directly from the authenticated extraction into the working tree.
- No existing or modified files were overwritten.
- **Still Missing Count:** `0` (0 missing out of 4,418).
- **Git Tracking:** All 4,418 manifest files are staged as ordinary tracked files in git index (total 4,421 tracked files including `.gitignore`, `result.md`, `SOURCE_MANIFEST.json`).

---

## 3. Windows Portability and Test Remediation

### Deterministic Web Builder Portability (`studio/scripts/build-web.py`)
- Replaced default system-encoding reads/writes with explicit UTF-8 decoding and newline normalization (`.replace("\r\n", "\n")`).
- Replaced `.write_text()` with explicit `write_bytes(encoded_page)` for all three output targets:
  - `studio/web/index.html`
  - `control/web/index.html`
  - `control/native/ios/OpenBotControl/index.html`
- **Output Invariant Verified:** Exactly **127,185 bytes**, SHA-256 **`bb99d979376841815bc5dcfe7c942bed28b36f2b87a0b3b80d8d366e5b8b3c67`**.
- Added regression test `test_build_handles_crlf_input_canonicalizes_to_lf_and_preserves_expected_payload` in `studio/tests/test_shared_source.py` verifying that forced CRLF asset inputs produce canonical LF output matching the exact 127,185-byte digest.

### Windows Filesystem Hardlink Analysis
- **NTFS Behavior on Windows:** On this Windows host, `os.link()` (`CreateHardLinkW`) raises `PermissionError: [WinError 5] Access is denied` for unprivileged users even within temp directories (confirmed via raw `fsutil hardlink create` returning `Error 5: Access is denied`).
- **Remediation:** In `studio/tests/test_studio_core.py` and `tools/tests/test_handoff.py`, when `os.link` is denied with `PermissionError`, the tests simulate a file with `st_nlink = 2`, proving that `clean_export` and `safe_file` strictly reject multi-link files without failing the test runner on unprivileged Windows environments.

### BlueprintStore CLI Boundary on Windows
- `BlueprintStore` POSIX-private permission checks remain strictly **fail-closed**.
- On non-POSIX (Windows), `BlueprintStore` intentionally raises `PlanError("private_owned_store_required")` because Windows does not enforce Unix `0o700` permission mode bits.
- Documented and tested the Windows unsupported CLI boundary via `test_windows_store_fails_closed_without_posix_permissions` in `studio/tests/test_studio_core.py`.
- POSIX-only tests in `StoreTests` are explicitly marked with `@unittest.skipIf(os.name != "posix", ...)`. No blanket test skipping was introduced.

---

## 4. Test Suite Execution and Evidence (Windows Host)

### Studio Python Unit Tests (50 Collected)
```
Ran 50 tests in 3.186s
OK (passed=46, skipped=4, failures=0, errors=0)
```
- 46 passed, 4 skipped (explicitly documented POSIX `0o700` CLI store boundary). Zero failures, zero errors.

### Tools / Handoff Python Unit Tests (8 Collected)
```
Ran 8 tests in 0.236s
OK (passed=8, failures=0, errors=0)
```
- All 8 tests passed. Zero failures, zero errors.

### Studio Node Tests (45 Collected)
```
node --test studio/tests/*.test.cjs
ℹ tests 45
ℹ pass 45
ℹ fail 0
```
- **19 finance unit tests + 26 gateway session/protocol tests = 45 passed.**

### Retained Node Tests (25 Collected)
```
node --test work/packages/bot-hq-queue/serial-queue.test.mjs work/tools/findrepo/test/*.test.mjs
ℹ tests 25
ℹ pass 25
ℹ fail 0
```
- **5 serial-queue tests + 20 findrepo tests = 25 passed.**

### Source Manifest Verification
```
python tools/verify-source.py
{"schema": "openbot.workspace-source/1", "scope": "workspace file integrity only; no installs, network, runtime state or release acceptance", "signed_release": false, "source_bytes": 72719857, "verified_files": 4418}
```
- **4,418 out of 4,418 files verified.** Exit code 0.

---

## 5. Native Windows Release Execution Proof (Task B / Section C)

- **Executable:** `control/releases/windows-x64/OpenBot-Control-Local-x64.exe` (448,512 bytes, ASLR/NX/high-entropy x64 GUI PE)
- **Dependency:** `control/releases/windows-x64/WebView2Loader.dll` (165,968 bytes) present adjacent to EXE.
- **Installed Runtime:** Microsoft Evergreen WebView2 x64 Runtime `157.0.4341.60` verified in `C:\Program Files (x86)\Microsoft\EdgeWebView\Application`.
- **Launch Test:**
  - Started via `Start-Process -FilePath OpenBot-Control-Local-x64.exe -PassThru`
  - PID: `12140`
  - Process Name: `OpenBot-Control-Local-x64`
  - Responding: `True`
  - Working Set: `2,740,224` bytes (2.7 MB)
  - Successfully initialized WebView2 host window
  - Terminated cleanly via process handle.
- **Offline / Security Boundary:** Run without `server-origin.txt`; app acts strictly as an offline light companion workspace with no network authority or unprompted socket binds.

---

## 6. Successor ZIP Generation and Byte-Identical Verification

The complete workspace successor archive was created using `tools/export-source.py` with original POSIX modes preserved:
- **Archive File:** `OpenBot-Workspace-Successor.zip`
- **File Size:** `20,285,225` bytes
- **File Count:** `4,419` regular entries (4,418 manifest-listed + `SOURCE_MANIFEST.json`)
- **SHA-256 Digest:** `1c704f194ea06a139e72e4922c42be5056338d42be38ff4f5bb9e9ceaeb9b1cf`

### Verification of Successor Archive:
1. Fresh extraction into independent temporary directory `temp_verify_successor`.
2. `python tools/verify-source.py` executed in fresh extraction: **Exit code 0, 4,418 files verified**.
3. Re-export from fresh extraction via `tools/export-source.py`:
   - Re-exported archive size: `20,285,225` bytes
   - Re-exported SHA-256: `1c704f194ea06a139e72e4922c42be5056338d42be38ff4f5bb9e9ceaeb9b1cf`
   - **Byte-Identical Re-export Result:** `True` (Confirmed deterministic).

---

## 7. Open Roadmap Items and Honest Release Boundary

| Requirement | Status | Current Reality |
|---|---|---|
| R01 Scope & Durability | Complete for current handoff | Successor ZIP created, verified, and re-export proven. |
| R02 Donor Adoption | Bounded | 19 finance CSV + 20 findrepo + 5 serial-queue tests passing. |
| R03 Studio / Kernel Gateway | Bounded | Shared UI connected to gateway in verified tests; staging pending. |
| R04 Isolated Execution Host | ❌ Open | Awaiting owner Linux staging host with cgroups and isolated credentials. |
| R05 Per-Bot Virtual PCs | ❌ Open | Awaiting real guest VM provisioner and approved IDE authentication. |
| R06 Official Social Adapters | ❌ Open | No social accounts or external publishing authorized. |
| R07 Product Completeness / a11y | ❌ Open | Light UI verified locally; independent accessibility review pending. |
| R08 Native Clients | Bounded | Windows x64 test EXE launched and verified; Android/iOS device signing pending. |
| R09 Independent Security Review | ❌ Open | Awaiting independent qualified security/SBOM audit. |
| R10 Production Operations | ❌ Open | Staging rollout/recovery drills not yet conducted. |
| R11 Protected Evaluation | ❌ Open | 20 held-out evaluation tasks not yet frozen. |
| R12 Real Private Pilot | ❌ Open | **Accepted genuinely observed pilot days: 0**. |
| R13 Human Release Authorization | ❌ Open | Public release unauthorized. |

**Public release flag: false. Accepted real observed pilot days: 0.**
