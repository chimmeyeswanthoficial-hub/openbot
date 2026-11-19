# Windows diagnostic text — capability prepared, registry permission NOT granted

**Permission state:** the owner answered “i don't know,” not approval. Registry
remains unchanged. No IFEO, loader-snaps flag, debugger/tool installation,
security-control change or new Windows execution was performed by Arena.

## What the existing evidence proves

At the reviewed base `9f5600d1fd285e79922fbf69a2abce5243cb9291`, the supplied
control records 29 events, **20 DLL notifications / 21 modules including the EXE**,
exit 0 and no reported cleanup errors. The supplied target run records
CREATE_PROCESS, ntdll LOAD_DLL and EXIT_PROCESS `0xc000007b`. Entry execution is
unmeasured; no failing instruction or stack was captured. The corrected report
properly treats this as consistent with early initialization failure, not proof of
an exact stage, unmapped kernel32, pre-entry nonexecution or a particular DLL/TLS fix.
These are supplied Windows traces independently inspected on Linux, not Arena
Windows runs. Collection success is not application launch acceptance.

**Important correction:** Microsoft specifies that LoadLibraryExW on an **EXE**
does not load static imports; it behaves as if DONT_RESOLVE_DLL_REFERENCES were
specified. Mapping that EXE successfully therefore does **not** prove its imports
resolved or that a new process can initialize. A separate inventory reporting
6 DLLs / 144 symbols / 0 missing is useful supplied evidence, not proof of startup.
Official reference:
[1](https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-loadlibraryexw).

## Implemented narrow extension — not a collector reliability rewrite

`tools/windows-debug-trace.py` now emits schema `openbot.windows-debug-trace/4`.
The default uses the prior wait path and does not read debug-string payloads.
With explicit `--debug-strings`, it calls WaitForDebugEventEx and one bounded
ReadProcessMemory for each reported payload, through its newly created target's
process handle. It never attaches to arbitrary existing processes, reads arbitrary
addresses supplied through CLI, writes target memory or enables loader snaps.

Limits and semantics:

- ≤16,384 bytes per event; ≤262,144 captured raw bytes per session, plus existing
  event and monotonic time caps. No unbounded terminator scan or retry loop.
- Microsoft describes `nDebugStringLength` as **the lower 16 bits of a byte count**,
  even for Unicode. No multiplication by two. UTF-16LE is decoded when `fUnicode`
  is set; ANSI is labeled a Latin-1 byte view, not a guessed system code page.
- `raw_base64` preserves captured bytes, including any terminator. Lower-16-bit
  lengths can wrap: “complete” means the **reported range**, not necessarily every
  byte emitted by the target. This limitation cannot be removed by scanning memory.
- Null pointer, read exception/failure, short read, bad count, decoding failure,
  truncation or exhausted budget is explicit. Requested incomplete payload capture
  gives `collection_status=diagnostic_incomplete` and CLI 2 after a complete event
  loop; normal checked event continuation/cleanup still runs. Event-loop failures
  retain their own status. Target failure can still be successfully collected.
- `--debug-strings` requires a **new output filename**; existing files/symlinks are
  refused. Use a private directory with suitable ACLs. Payloads may include paths,
  usernames, prompts or secrets; they are not sanitized by USERPROFILE replacement.
  Do not commit/upload raw payload traces without separate privacy review. Output
  ACL configuration/encryption is the operator's job, not guaranteed by this tool.
- New schema does not rewrite/relabel historical schema-3 recordings. Entry-point
  instrumentation, stack capture, target-ISA validation and stop/reap guarantees
  remain outside scope. The collection deadline cannot interrupt arbitrary blocked
  native API calls. Supported intended environment remains 64-bit Windows 10/11
  Python; actual Windows ABI behavior still needs measurement.

Official payload and Unicode wait semantics:
[2](https://learn.microsoft.com/en-us/windows/win32/api/minwinbase/ns-minwinbase-output_debug_string_info?redirectedfrom=MSDN),
[3](https://learn.microsoft.com/en-us/windows/win32/api/debugapi/nf-debugapi-waitfordebugeventex).
Twenty new pure-Python fake-backend tests cover these contracts; they are not
Windows ABI, native Unicode or loader-snaps evidence.

## Next: actual payload self-test WITHOUT registry changes

`tools/windows-debug-string-probe.c` is a source-only owned probe that calls
OutputDebugStringA with `OpenBot OS ANSI probe 0123456789` and OutputDebugStringW
with `OpenBot OS Unicode probe అ €`, then exits 0. Build it only with an **already
approved** compiler/toolchain, recording exact commands, version and SHA. If no
approved compiler exists, return that blocker; do not install one silently.

In an owner-approved private working directory on Windows, use the built probe:

```powershell
python .\tools\windows-debug-trace.py .\debug-string-probe.exe --debug-strings --output .\PRIVATE\probe-new.json --max-events 100 --session-timeout-ms 10000
```

Verify CLI status, both exact texts and decoded raw bytes against the known
messages, reported byte counts, target exit 0, event continuation and cleanup.
A failed/partial/Unicode-mismatched self-test blocks loader-snaps collection.
Do not merely return another unchanged three-event target trace and call it new
root-cause evidence. No self-test has been run on Windows by Arena.

## Optional IFEO proposal — ONLY after explicit owner approval

The proposal is limited to **loader-snaps bit `0x00000002`** on the 64-bit IFEO key:

`HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\OpenBot-Control-Local-x64.exe`

The actual Windows registry path uses **`Image File Execution Options`** (with
spaces). The flag is name-based: all newly started executables with this basename
may be affected, not just one full path. Confirm the registry view and no unrelated
same-name process before any approved change. Nothing is written merely by reading
this plan; an administrator must still verify the exact host and permission.

Exact bounded preserve/enable/restore protocol for a future approved tool:

1. Open only `Registry64`/LocalMachine. Read the exact key's existence, GlobalFlag
   value existence, **raw unexpanded value and registry kind**, and unrelated values/
   subkeys. Save these privately and export an existing key as an additional backup.
   Hash the backup. Do not publish sensitive registry contents. No backup = no change.
2. Accept only a clearly parseable unsigned 32-bit REG_SZ hex flag or REG_DWORD.
   Refuse unsupported kinds/malformed/oversized values; do not convert arbitrary
   values, replace the whole key, set `Debugger`, or touch global/system flags.
3. Let `old` be the parsed prior flag (zero if absent). If bit 2 is already set,
   record that fact; do not claim to have enabled it or later clear the owner's bit.
   Otherwise set **only GlobalFlag** to `old OR 0x00000002`, preserving the existing
   supported kind; a new value uses REG_SZ canonical eight-digit hexadecimal text.
   Read back and verify kind/value. Record the exact enabled state for race checks.
4. Perform one bounded recording of the **unchanged hashed target** into a new
   private file. Keep the original EXE/DLL/traces intact. No AV/SmartScreen/Memory
   Integrity changes, DLL replacement, signing purchase or repeated blind launches.
5. In a `finally`/recovery action, compare current GlobalFlag with the recorded
   enabled state. If anyone changed it concurrently, stop for three-way review,
   not an unconditional overwrite. Otherwise restore the exact original raw value
   **and kind**, or remove only the newly created value if originally absent.
6. Remove a newly created image key only if it is still empty and has no unrelated
   concurrent values/subkeys. Never delete a pre-existing key. Read back and prove
   original value/kind/presence; retain the private recovery backup until confirmed.
7. Require new target-specific text identifying the rejected image/path/status or
   another defensible stage fact. No text/ambiguous text means cause still unknown.

No registry writer is included or executed in this foundation. If this later
proposal is unnecessary or not explicitly approved, stay on non-mutating source/
PE review and an independently approved debugger experiment. Public release false.
