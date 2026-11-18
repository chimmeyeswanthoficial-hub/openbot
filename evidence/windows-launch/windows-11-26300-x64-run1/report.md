# Windows Native Launch Diagnostic Record — Run 1

**Run Identifier:** `windows-11-26300-x64-run1`  
**Host Platform:** Windows 10 Home Single Language (Windows 11 Build `26300.9974`, DisplayVersion `26H2`, Architecture `X64`)  
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
- **Evidence Images & Provenance:**
  - `error.png`: Cropped capture of the modal error dialog.
  - `desktop-context.png`: Uncropped desktop screen capture showing the dialog in context with the runner environment.
  - **Capture Timing:** Screen captured at approximately `2026-11-18T17:17:00+05:30` when the binary was launched via PowerShell.

---

## 3. Bounded System Event Queries

Queries performed across the bounded time window surrounding the launch attempts:
* **Time Window:** `2026-11-18T17:00:00+05:30` to `2026-11-18T19:45:00+05:30`

### Application Channel
* **Channel Status:** Accessible; returned 179 total events across the host during this 2h45m window.
* **Filter:** `ProviderName='Application Error'` and keyword search `Message like '*OpenBot*'`.
* **Matching Records for Target:** Exactly `0`.
* **Qualification:** Standard user-mode crash reporting (`WerFault.exe` / `Application Error`) was not invoked. This is consistent with early loader failure where process initialization is aborted by `ntdll` before user-mode exception handling or crash reporting is established.

### Code Integrity Channel
* **Channel Status:** `Microsoft-Windows-CodeIntegrity/Operational` is enabled (`IsEnabled=true`, 1,465 lifetime records).
* **Events in Window:** Exactly `0` total events logged in this channel during the 2h45m window.
* **Qualification:** No signature policy enforcement violations, revoked driver/binary blocks, or integrity check failures were recorded for `OpenBot-Control-Local-x64.exe` during the launch window.

---

## 4. Loader and Debugger Tracing Analysis

### Harness & Execution
* **Debugger Harness:** `tools/windows-debug-trace.py` (committed Python script utilizing Win32 `DEBUG_ONLY_THIS_PROCESS` via `ctypes`).
* **Raw Trace Artifact:** `evidence/windows-launch/windows-11-26300-x64-run1/debug-trace.json`.
* **Execution Timestamp:** `2026-11-18T19:43:12+05:30`.

### Debugger Observations
1. **`CREATE_PROCESS_DEBUG_EVENT` (Event #1):**
   - Image base mapped at: `0x7ff6c6d50000` (ASLR base for this process run).
   - Expected Entry Point: `PE AddressOfEntryPoint RVA 0x13d0` (resolved virtual address: `0x7ff6c6d513d0`).
   - *Note on Entry Point Label:* `0x13d0` is the PE entry point RVA pointing to CRT startup code (`WinMainCRTStartup`). The source-level application function `wWinMain` is a distinct later stage and was not reached.
2. **`LOAD_DLL_DEBUG_EVENT` (Event #2):**
   - Mapped DLL: `C:\Windows\System32\ntdll.dll` at base `0x7ffbc5550000`.
3. **`EXIT_PROCESS_DEBUG_EVENT` (Event #3):**
   - Exit code: `0xc000007b` (`STATUS_INVALID_IMAGE_FORMAT`).
   - No `CREATE_THREAD_DEBUG_EVENT` or user-mode entry was observed.
   - Entry point arrived: `false`.

### Diagnostic Limitations
* The Win32 debugger trace captures only modules successfully mapped by the NT loader prior to termination.
* Observing that only `ntdll.dll` mapped (and not even `kernel32.dll`) narrows the failure to the earliest static dependency resolution or PE directory parsing phase in `ntdll.dll`.
* It does **not** pinpoint which specific imported module, PE header attribute, relocation table entry, or TLS directory structure caused `ntdll` to raise `STATUS_INVALID_IMAGE_FORMAT`.

---

## 5. Distinction Between Observations and Hypotheses

Per `WINDOWS_LOADER_REVIEW.md`:
1. **Established Facts:**
   - The native x64 executable fails process initialization on Windows 11 Build 26300 with `0xc000007b` / `STATUS_INVALID_IMAGE_FORMAT`.
   - The failure occurs inside `ntdll.dll` before `kernel32.dll` is mapped and before `PE AddressOfEntryPoint RVA 0x13d0` is reached.
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
