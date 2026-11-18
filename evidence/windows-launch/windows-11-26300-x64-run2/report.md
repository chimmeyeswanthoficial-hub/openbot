# Windows Native Launch Diagnostic Report — Run 2

**Run Identifier:** `windows-11-26300-x64-run2`  
**Host Platform:** Windows 10 Home Single Language (Windows 11 Build `26300.9974`, DisplayVersion `26H2`, Architecture `X64`)  
**Target Executable:** `control/releases/windows-x64/OpenBot-Control-Local-x64.exe`  
**Status:** Native launch blocked by `0xc000007b`; root cause unproved; failing module and header element unidentified  
**Harness Version:** 2 (`tools/windows-debug-trace.py` schema `openbot.windows-debug-trace/2`)  
**Supersedes:** Run 1 (`windows-11-26300-x64-run1`). Run-1 artifacts are preserved as-is; see run-1 `report.md` for original recording context and known recorder limitation note.

---

## 1. App-Local Binary Inventory and File Provenance

Executed in directory `control/releases/windows-x64/`:

| File | Bytes | SHA-256 Digest | Machine | Subsystem | Linker |
|---|---:|---|---|---|---|
| `OpenBot-Control-Local-x64.exe` | 448,512 | `ebcf4927302840f5b73f85e674590538569a0150703f55393d850f149be7bcdc` | AMD64 (0x8664) | Windows GUI (2) | 2.44 |
| `WebView2Loader.dll` | 165,968 | `462b36fd1be6ca9f7563466a89e57c41ef4a4def3e0a84fa885d203aea4a3aaf` | AMD64 (0x8664) | Windows GUI (2) | 14.28 |

- **Other DLLs:** None present in the application directory.
- **Installed Runtime:** Microsoft Evergreen WebView2 x64 Runtime `157.0.4341.60`.

---

## 2. Reproduction and Physical Observation

**Capture Time:** `~2026-11-18T17:17:00+05:30` (visible in desktop-context.png clock).  
**Diagnostic Trace Time:** `2026-11-18T20:29:25+05:30` (committed via corrected harness, run-2).

A system modal dialog appears immediately on desktop launch:
- **Window Title:** `OpenBot-Control-Local-x64.exe - Application Error`
- **Window Text:** `The application was unable to start correctly (0xc000007b). Click OK to close the application.`
- **Evidence Images** (committed in run-1 folder):
  - `../windows-11-26300-x64-run1/error.png` — cropped modal dialog capture.
  - `../windows-11-26300-x64-run1/desktop-context.png` — full desktop context showing dialog.

---

## 3. Win32 Debugger Trace (Run 2)

### Harness
- **Script:** `tools/windows-debug-trace.py` (schema `openbot.windows-debug-trace/2`, harness_version 2)
- **Regression Tests:** 16 tests in `tools/tests/test_windows_debug_trace.py` (all pass)
- **Raw Trace:** `evidence/windows-launch/windows-11-26300-x64-run2/debug-trace.json`

### Recorded Event Sequence

| Seq | Event | Detail |
|---|---|---|
| 1 | `CREATE_PROCESS_DEBUG_EVENT` | Image base `0x7ff7e4cd0000`; CRT startup address `0x7ff7e4cd13d0` |
| 2 | `LOAD_DLL_DEBUG_EVENT` | `C:\Windows\System32\ntdll.dll` at `0x7ffbc5550000` |
| 3 | `EXIT_PROCESS_DEBUG_EVENT` | Exit code `0xc000007b` |

**Collection status:** `complete` (EXIT_PROCESS observed; harness exited 0).

### Supported Conclusions

The committed harness recorded:
- Process creation for the executable at base `0x7ff7e4cd0000` with CRT startup address `0x7ff7e4cd13d0`.
- One DLL load notification for `ntdll.dll` at `0x7ffbc5550000`.
- Process exit `0xc000007b`.

No `kernel32.dll` load notification appears in this three-event recording. **Entry-point execution was not instrumented;** `entry_point_reached` is `null` and `entry_point_measured` is `false`. No exception address or stack was captured; no `EXCEPTION_DEBUG_EVENT` was observed.

> This sequence is **consistent with early initialization failure**, but the exact stage and rejected image/header element **remain unproved**.

### Diagnostic Limitations

1. Entry-point execution is not instrumented. `pe_entry_crt_address` is the PE `AddressOfEntryPoint` plus load-delta — the CRT startup wrapper address. Source-level `wWinMain` is a distinct, later stage. Neither is proven reached or not reached.
2. This harness records only modules successfully LOAD_DLL-notified by the NT loader before EXIT_PROCESS. Absence of a module's LOAD_DLL notification is consistent with loader failure before that module was mapped, but does not establish the exact failing instruction or header element.
3. No EXCEPTION_DEBUG_EVENT was observed in this run; no exception address or stack captured.

---

## 4. Bounded System Event Queries

Queries performed across a bounded time window (see `../windows-11-26300-x64-run1/event-log-application.json` and `event-log-codeintegrity.json`):

- **Application channel (179 total events, 2h45m window):** Zero events matched `ProviderName='Application Error'`; zero events mentioned `OpenBot`. This is **consistent** with early loader failure before user-mode crash reporting is established — it does not by itself prove WerFault never ran or explain why no Application Error event was logged.
- **CodeIntegrity channel (enabled, 1,465 lifetime records):** Zero events in the 2h45m window. No signature policy block, revocation event, or integrity rejection was recorded during the launch window.

---

## 5. Distinction Between Observations and Hypotheses

Per `WINDOWS_LOADER_REVIEW.md`:

**Established facts:**
- `OpenBot-Control-Local-x64.exe` exits with `0xc000007b` immediately when launched on Windows 11 Build 26300.
- Only `ntdll.dll` was LOAD_DLL-notified before EXIT_PROCESS. No `kernel32.dll` notification appeared in the three-event recording.

**Unproved — not asserted:**
- Whether MinGW-w64 PE32+ TLS/relocation directory formatting, CET, or CRT static linkage is the cause.
- Whether an MSVC toolchain rebuild will resolve the failure.
- Whether Authenticode signing is required (independent release gate, not an established technical fix).
- The exact failing instruction, loader code path, or which image element ntdll rejects.

**Safety guardrails:**
- No security controls (Defender, SmartScreen, Memory Integrity) disabled.
- No third-party DLLs downloaded or substituted.
- No registry IFEO/loader-snap overrides enabled.
- No host debug/build tools installed without explicit owner permission.

---

## 6. Release Boundary

- **R08 Native Clients:** Blocked pending identification of root cause and genuine light-UI interaction evidence.
- **Public Release Flag:** `false`
- **Accepted Real Observed Pilot Days:** `0`
