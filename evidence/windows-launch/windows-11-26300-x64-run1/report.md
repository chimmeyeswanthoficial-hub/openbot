# Windows Native Launch Diagnostic Record — Run 1

**Date & Time:** 2026-11-18T18:49:00+05:30  
**Host Platform:** Windows 10 Home Single Language (Windows 11 Build `26300.9974`, DisplayVersion `26H2`, Architecture `X64`)  
**Run Identifier:** `windows-11-26300-x64-run1`  
**Target Executable:** `control/releases/windows-x64/OpenBot-Control-Local-x64.exe`  
**Status:** Native launch blocked by Windows NT Loader (`0xc000007b`); root cause unproved  

---

## 1. App-Local Binary Inventory and File Provenance

Executed in directory `control/releases/windows-x64/`:

| File | Bytes | SHA-256 Digest | Machine | Subsystem | Linker |
|---|---:|---|---|---|---|
| `OpenBot-Control-Local-x64.exe` | 448,512 | `ebcf4927302840f5b73f85e674590538569a0150703f55393d850f149be7bcdc` | AMD64 (0x8664) | Windows GUI (2) | 2.44 |
| `WebView2Loader.dll` | 165,968 | `462b36fd1be6ca9f7563466a89e57c41ef4a4def3e0a84fa885d203aea4a3aaf` | AMD64 (0x8664) | Windows GUI (2) | 14.28 |

- **Other DLLs:** None present in the application directory.
- **Installed Runtime:** Microsoft Evergreen WebView2 x64 Runtime version `157.0.4341.60` verified installed in `C:\Program Files (x86)\Microsoft\EdgeWebView\Application\157.0.4341.60\msedgewebview2.exe`.

---

## 2. Reproduction and Physical Observation

### Reproduction Step
```powershell
$exe = "control\releases\windows-x64\OpenBot-Control-Local-x64.exe"
$proc = Start-Process -FilePath $exe -PassThru
```

### Observed Physical Behavior
- A system modal dialog appears immediately on the desktop:
  - **Window Title:** `OpenBot-Control-Local-x64.exe - Application Error`
  - **Window Text:** `The application was unable to start correctly (0xc000007b). Click OK to close the application.`
  - **Window Controls:** System error icon (Red circle with white X), single `OK` button.
- **Evidence Images:**
  - `error.png`: Cropped, sanitized capture of the modal error dialog.
  - `desktop-context.png`: Uncropped desktop screen capture showing the dialog in context with the runner environment.

---

## 3. Bounded System Event Queries

### Application Error Channel
* **Query:** `Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='Application Error'} -MaxEvents 5`
* **Query Timestamp:** `2026-11-18T18:49:00+05:30`
* **Matching Events for Target:** Exactly `0`.
* **Detail:** Windows Application Error crash logging is invoked when an unhandled user-mode exception occurs in a running process. Because `0xc000007b` (`STATUS_INVALID_IMAGE_FORMAT`) is raised by the NT loader during early process initialization, CSRSS presents the HardError modal dialog and the process terminates before application error logging is reached.

### Code Integrity Channel
* **Query:** `Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-CodeIntegrity/Operational'} -MaxEvents 5`
* **Query Timestamp:** `2026-11-18T18:49:15+05:30`
* **Matching Events for Target:** Exactly `0`.
* **Detail:** No signature policy enforcement violations, revoked binary blocks, or CodeIntegrity rejections were logged for `OpenBot-Control-Local-x64.exe`.

---

## 4. Loader and Debugger Tracing Analysis

- **Debugger Trace (`DEBUG_ONLY_THIS_PROCESS`):**
  - Process creation (`CREATE_PROCESS`) succeeds, mapping image base at `0x7ff6e7800000`.
  - Initial system DLL `ntdll.dll` maps at `0x7ffbc5550000`.
  - Initial thread starts at `ntdll!RtlUserThreadStart` (`0x7ffbc5619c30`).
  - Execution fails inside `ntdll` with `STATUS_INVALID_IMAGE_FORMAT` (0xc000007b), triggering `ntdll!RtlRaiseStatus(0xc000007b)` and immediate `EXIT_PROCESS` (exit code `0xc000007b`).
  - Application entry point `wWinMain` (`0x13d0`) is **not reached**.
  - No user application code, `startWebView()`, or `WebView2Loader.dll` dynamic `LoadLibraryExW` call was executed.

---

## 5. Distinction Between Observations and Hypotheses

Per `WINDOWS_LOADER_REVIEW.md`:
1. **Established Fact:** The native x64 executable fails process initialization on Windows 11 Build 26300 with `0xc000007b` / `STATUS_INVALID_IMAGE_FORMAT`.
2. **Unproved Hypotheses:**
   - Whether MinGW-w64 PE32+ relocation/TLS directory formatting, CET (Control-flow Enforcement Technology), or CRT static linkage is the specific cause of kernel loader rejection.
   - Whether an MSVC toolchain build will resolve the failure (MSVC compilation is a diagnostic experiment, not an established requirement).
   - Whether Authenticode signing is required (signing is an independent release gate, not an established technical repair for `0xc000007b`).
3. **Safety & Policy Guardrails:**
   - No security controls (Defender, SmartScreen, Memory Integrity) were disabled.
   - No third-party DLLs were downloaded or substituted.
   - No registry IFEO/loader-snap overrides were enabled.
   - No host debug/build tools were installed without explicit owner permission.

---

## 6. Release Boundary

* **R08 Native Clients:** Blocked pending resolution of native Windows startup and collection of genuine light-UI interaction evidence.
* **Public Release Flag:** `false`
* **Accepted Real Observed Pilot Days:** `0`
