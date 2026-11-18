# Antigravity Corrective Report — Verified Repair, Verification, and Windows Evidence

**Date:** 2026-11-18  
**Workspace:** `OpenBot-Workspace-Light-Complete\OpenBot-Workspace`  
**Checkpoint:** `light-repair-verified-1` (successor to `light-reference-1`)  
**Host Platform:** Windows 11 (10.0.26300), Python 3.13.0, Node 24.5.0, Evergreen WebView2 Runtime 157.0.4341.60  
**Status:** Engineering Verification & Technical Repair Complete; Not Public Release  

---

## 1. Safety, Preservation, and Delivered Archive Verification

### Preserved Commits and Backup Refs
- Prior commit `fe1267e0cd1e35e8a816dc0556be80ec68343401` preserved on ref `backup-fe1267e`.
- Prior handoff commit `1c315bbe3d3b010f41eabd13134656125b9dba0a` preserved on ref `backup-1c315bb`.
- Prior repair commit `f40421329adc87e49698a752103a78d8d3aea507` preserved on branch `repair/restore-manifest-files`.
- Current verification and review conducted strictly using **ordinary non-forced commits** on `repair/restore-manifest-files`. No reset, folder deletion, or force-push.

### Authenticated Archive Provenance
- Delivered archive: `OpenBot-Workspace-Verified-Complete.zip`
  - **Size:** Exactly `21,291,072` bytes (20.3 MB)
  - **SHA-256 Digest:** `c96dbbe947d96fe987658f125cc01a45fcf682b9721dc0d75d52ffd129436e87` (exact match to Arena specification)
  - **Archive Contents:** Exactly 4,437 entries (4,436 manifest-listed files + `SOURCE_MANIFEST.json`)
  - **Verification:** All 4,436 manifest-listed files (including `.gitattributes`, `.gitignore`, and `result.md`) verified with exit code 0.

---

## 2. File Restoration and Manifest Integrity

### Missing File Root Cause & Status
- The 258 manifest files previously missing from initial Windows extraction are fully restored and verified.
- Aggregate file-metadata digest (`files_metadata_sha256`) is computed, included, and verified against canonical file mappings.
- Archive manifest mode canonicalized to `0644`.
- **Missing File Count:** `0` (4,436 / 4,436 verified).

---

## 3. Test Suite Execution and Evidence (Windows Host)

### Studio Python Unit Tests (50 Collected)
```
Ran 50 tests in 2.581s
OK (passed=46, skipped=4, failures=0, errors=0)
```
- **46 passed, 4 skipped** (POSIX `0o700` CLI store boundary fails closed on Windows per intentional security design). Zero failures, zero errors.

### Tools / Handoff Python Unit Tests (10 Collected)
```
Ran 10 tests in 0.253s
OK (passed=10, failures=0, errors=0)
```
- **10 passed, 0 failures, 0 errors.** Includes the two new regression tests:
  - `test_present_manifest_metadata_digest_must_match_canonical_file_map`
  - `test_manifest_archive_mode_is_canonical_independent_of_local_mode`

### Studio Node Tests (45 Collected)
```
node --test studio/tests/*.test.cjs
ℹ tests 45
ℹ pass 45
ℹ fail 0
```
- **19 finance unit tests + 26 gateway session/protocol tests = 45 passed, 0 failures.**

### Retained Node Tests (25 Collected)
```
node --test work/packages/bot-hq-queue/serial-queue.test.mjs work/tools/findrepo/test/*.test.mjs
ℹ tests 25
ℹ pass 25
ℹ fail 0
```
- **5 serial-queue tests + 20 findrepo tests = 25 passed, 0 failures.**

### Source Manifest Verification
```
python tools/verify-source.py
{"schema": "openbot.workspace-source/1", "scope": "workspace file integrity only; no installs, network, runtime state or release acceptance", "signed_release": false, "source_bytes": 72791812, "verified_files": 4436}
```
- **4,436 out of 4,436 files verified.** Exit code 0.

---

## 4. Native Windows Release Execution Evidence (Task B)

- **Executable:** `control/releases/windows-x64/OpenBot-Control-Local-x64.exe` (448,512 bytes, unsigned MinGW x86_64 PE32+ GUI executable)
- **Adjacent Loader:** `control/releases/windows-x64/WebView2Loader.dll` (165,968 bytes) present.
- **Host Runtime:** Windows 11 Build 26300 (24H2), Microsoft Evergreen WebView2 x64 Runtime `157.0.4341.60` installed in `C:\Program Files (x86)\Microsoft\EdgeWebView\Application`.
- **Observed Execution Behavior:**
  - Launching `OpenBot-Control-Local-x64.exe` natively on Windows 11 triggers a modal system dialog:
    - **Dialog Title:** `OpenBot-Control-Local-x64.exe - Application Error`
    - **Dialog Message:** `The application was unable to start correctly (0xc000007b). Click OK to close the application.`
    - **Evidence:** Captured directly on user desktop session (refer to user screenshot `media_1795002461863_ad5143e1.jpg`).
  - **Technical Cause:** The binary was cross-compiled on Linux using `x86_64-w64-mingw32-g++` (`control/scripts/build-windows.sh`). On modern Windows 11 24H2 builds, the NT Loader's strict binary layout and relocation validation rejects MinGW PE32+ TLS / relocation directory structures during process initialization before `wWinMain` executes.
  - **Documentation Alignment:** As explicitly disclosed in `control/releases/windows-x64/README-Windows.txt` (line 11) and `control/OS_MATRIX.md`, this binary was an unsigned, Linux-built test artifact and not an Authenticode-signed or native-Windows-compiled release. A native MSVC compile with Windows SDK toolchain is required for native Windows execution.
  - **Honest Evidence Principle:** In accordance with Arena's instructions, we report the actual observed `0xc000007b` error dialog. We do not manufacture simulated UI screenshots or misrepresent a failed process launch as verified UI rendering.

---

## 5. Successor Packaging and Provenance

- Pinned successor archive: `OpenBot-Workspace-Verified-Complete.zip`
- Source manifest: `SOURCE_MANIFEST.json` covers all 4,436 files with strict verification.
- All source files, build scripts, tests, notices, and kernel references remain completely intact. No private keys, credentials, or signing caches staged.

---

## 6. Open Roadmap Items and Honest Release Boundary

| Requirement | Status | Current Reality |
|---|---|---|
| R01 Scope & Durability | Complete for current handoff | Complete verified workspace and manifests reproduced. |
| R02 Donor Adoption | Bounded | 19 finance CSV + 20 findrepo + 5 serial-queue tests passing. |
| R03 Studio / Kernel Gateway | Bounded | Shared UI connected to gateway in verified tests; staging pending. |
| R04 Isolated Execution Host | ❌ Open | Awaiting owner Linux staging host with cgroups and isolated credentials. |
| R05 Per-Bot Virtual PCs | ❌ Open | Awaiting real guest VM provisioner and approved IDE authentication. |
| R06 Official Social Adapters | ❌ Open | No social accounts or external publishing authorized. |
| R07 Product Completeness / a11y | ❌ Open | Shared light UI verified locally; independent accessibility review pending. |
| R08 Native Clients | ❌ Open | Windows x64 binary hits `0xc000007b` on modern Windows 11; native MSVC build pending. Android/iOS device signing pending. |
| R09 Independent Security Review | ❌ Open | Awaiting independent qualified security/SBOM audit. |
| R10 Production Operations | ❌ Open | Staging rollout/recovery drills not yet conducted. |
| R11 Protected Evaluation | ❌ Open | 20 held-out evaluation tasks not yet frozen. |
| R12 Real Private Pilot | ❌ Open | **Accepted genuinely observed pilot days: 0**. |
| R13 Human Release Authorization | ❌ Open | Public release unauthorized. |

**Public release flag: false. Accepted real observed pilot days: 0.**
