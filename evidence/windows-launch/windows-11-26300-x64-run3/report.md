# Windows Native Launch Diagnostic Report — Run 3

**Run Identifier:** `windows-11-26300-x64-run3`  
**Host Platform:** Windows 10 Home Single Language (Windows 11 Build `26300.9974`, DisplayVersion `26H2`, Architecture `X64`)  
**Target Executable:** `control/releases/windows-x64/OpenBot-Control-Local-x64.exe`  
**Target Digest:** SHA-256 `ebcf4927302840f5b73f85e674590538569a0150703f55393d850f149be7bcdc` (448,512 bytes, AMD64 PE32+)  
**Status:** Native launch blocked by `0xc000007b`; root cause unproved; failing module and header element unidentified  
**Harness Version:** 3 (`tools/windows-debug-trace.py`, schema `openbot.windows-debug-trace/3`)  
**Harness Suite:** 32 unit/regression tests in `tools/tests/test_windows_debug_trace.py` (57 total tools tests passing)  

---

## 1. Native Debugger Harness Validation (Positive Control vs Failing Target)

### Positive Control: Benign Native AMD64 Executable (`whoami.exe`)
To establish that the v3 harness correctly handles native process creation, DLL mapping notifications, thread events, startup breakpoints, handle cleanup, and normal process exit on this Windows 11 host:
- **Binary:** `C:\Windows\System32\whoami.exe` (AMD64 0x8664)
- **Artifact:** `evidence/windows-launch/control-whoami-x64/debug-trace.json`
- **Execution Timestamp:** `2026-11-18T22:12:38+05:30`
- **Observed Trace:**
  - `CREATE_PROCESS`: Image base `0x7ff7f58b0000`, start address `0x7ff7f58b1cb0`.
  - Sequential DLL mapping notifications: `ntdll.dll` (`0x7ffbc5550000`), `kernel32.dll` (`0x7ffbc44d0000`), `KernelBase.dll` (`0x7ffbc2e00000`), `advapi32.dll`, `msvcrt.dll`, and 19 additional system libraries.
  - Initial startup breakpoint received and continued with `DBG_CONTINUE`.
  - Normal process termination: `EXIT_PROCESS` with exit code `0x0`.
- **Harness Outcome:** `collection_status: "complete"`, `cleanup_status: "ok"`, `cleanup_errors: []`, `module_paths_resolved: true`, CLI exit code `0`.

### Target Execution: `OpenBot-Control-Local-x64.exe` (Run 3)
- **Binary:** `control/releases/windows-x64/OpenBot-Control-Local-x64.exe`
- **Artifact:** `evidence/windows-launch/windows-11-26300-x64-run3/debug-trace.json`
- **Execution Timestamp:** `2026-11-18T22:13:05+05:30`
- **Observed Trace:**
  - Sequence 1 (`CREATE_PROCESS`): Image base `0x7ff688b90000`, reported start address `0x7ff688b913d0` (PID 6024, TID 11396).
  - Sequence 2 (`LOAD_DLL`): `C:\Windows\System32\ntdll.dll` mapped at base `0x7ffbc5550000`.
  - Sequence 3 (`EXIT_PROCESS`): Immediate process termination with exit code `0xc000007b` (`STATUS_INVALID_IMAGE_FORMAT`).
  - No `kernel32.dll` load notification was received.
  - No thread creation, user-mode execution, or `EXCEPTION_DEBUG_EVENT` was received.
- **Harness Outcome:** `collection_status: "complete"`, `cleanup_status: "ok"`, `cleanup_errors: []`, `module_paths_resolved: true`, CLI exit code `0`.

---

## 2. Explicit Provenance and Diagnostic Scope Clarifications

1. **Run-1 Raw Artifact Preservation:**
   - The original raw trace in `evidence/windows-launch/windows-11-26300-x64-run1/debug-trace.json` retains all originally collected field values alongside the `recorder_limitation_note` added at commit `89e9472`. Both the pre-annotation blob and the annotated version remain preserved in Git history. It is an annotated record of the historical run-1 collector, not an assertion of byte-identical unedited text.
2. **Historical Event-Query Scope:**
   - The query outputs in `event-log-application.json` and `event-log-codeintegrity.json` cover the bounded historical window `17:00:00` to `19:45:00` on 2026-11-18. They provide historical context for the initial interactive PowerShell reproduction (~17:17 IST), not temporal coverage of subsequent runs (run-2 at 20:29 IST or run-3 at 22:13 IST).
3. **Entry-Point Measurement Semantics:**
   - `entry_point_measured` is explicitly `false`; `entry_point_reached` is explicitly `null`.
   - The field `pe_entry_crt_address` records the reported start address from `CREATE_PROCESS_DEBUG_INFO.lpStartAddress` (CRT startup wrapper address). Source-level `wWinMain` is a distinct later stage. Neither address was probed or measured as reached.
4. **Causal Scope of Findings:**
   - The observation that only `ntdll.dll` was mapped before process exit `0xc000007b` proves that failure occurred during early NT loader initialization before `kernel32.dll` was mapped.
   - It does **not** identify the specific rejected imported module, PE header structure, relocation entry, or TLS directory attribute.

---

## 3. Established Facts vs Unproved Hypotheses

Per `WINDOWS_LOADER_REVIEW.md`:

**Established Facts:**
1. The native x64 executable fails process initialization on Windows 11 Build 26300 with `0xc000007b` / `STATUS_INVALID_IMAGE_FORMAT`.
2. The failure occurs in `ntdll.dll` before `kernel32.dll` is mapped and before CRT entry or `wWinMain` is executed.
3. The v3 Win32 debugger harness executes reliably and cleans up completely on this host, as verified by the 29-event benign control (`whoami.exe`) and 32 regression tests.

**Unproved Hypotheses (Not Asserted as Facts):**
1. Whether MinGW-w64 PE32+ relocation/TLS directory layout, CET, or CRT static linkage is the root cause.
2. Whether an MSVC toolchain build will resolve the failure (MSVC compilation is an experimental diagnostic comparison, not an established requirement).
3. Whether Authenticode signing is required (signing is an independent release gate, not an established fix for `0xc000007b`).

**Safety & Guardrails:**
- No security controls (Windows Defender, SmartScreen, Memory Integrity) were disabled.
- No third-party DLLs were downloaded or substituted.
- No registry IFEO overrides were applied.

---

## 4. Release Boundary

* **R08 Native Clients:** Blocked pending identification of root cause and genuine light-UI interaction evidence.
* **Public Release Flag:** `false`
* **Accepted Real Observed Pilot Days:** `0`
