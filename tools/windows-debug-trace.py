#!/usr/bin/env python3
"""Windows Native Loader Debugger Trace Harness.

Attaches a Win32 debugging loop (DEBUG_ONLY_THIS_PROCESS) to observe
early process initialization, DLL loading events, exceptions, and exit status.

Design constraints
------------------
- Entry-point execution is NOT instrumented in this harness.
  `entry_point_measured` is therefore always False, and `entry_point_reached`
  is always null (None/JSON null).  Do not interpret either field as proving
  entry was or was not reached.
- The initial debugger breakpoint (STATUS_BREAKPOINT 0x80000003) raised when
  the new process first suspends is handled with DBG_CONTINUE so the target
  can continue normally.  Genuine application exceptions are forwarded with
  DBG_EXCEPTION_NOT_HANDLED.
- File handles supplied in CREATE_PROCESS_DEBUG_INFO.hFile and
  LOAD_DLL_DEBUG_INFO.hFile are owned by the caller (this debugger) and are
  closed explicitly after path resolution (see Microsoft WaitForDebugEvent docs).
- A total event-count cap (max_events) prevents unbounded loops.
- ContinueDebugEvent and all cleanup paths are checked; non-zero exit status
  is returned on collection or setup errors.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import datetime
import json
import os
from pathlib import Path
import sys

# ---------------------------------------------------------------------------
# Win32 constants
# ---------------------------------------------------------------------------
DEBUG_ONLY_THIS_PROCESS = 0x00000002
DBG_CONTINUE = 0x00010002
DBG_EXCEPTION_NOT_HANDLED = 0x80010001

# Exception codes
STATUS_BREAKPOINT = 0x80000003          # Normal initial debugger breakpoint
STATUS_INVALID_IMAGE_FORMAT = 0xC000007B

EXCEPTION_DEBUG_EVENT = 1
CREATE_THREAD_DEBUG_EVENT = 2
CREATE_PROCESS_DEBUG_EVENT = 3
EXIT_THREAD_DEBUG_EVENT = 4
EXIT_PROCESS_DEBUG_EVENT = 5
LOAD_DLL_DEBUG_EVENT = 6
UNLOAD_DLL_DEBUG_EVENT = 7
OUTPUT_DEBUG_STRING_EVENT = 8
RIP_EVENT = 9

EVENT_NAMES = {
    1: "EXCEPTION_DEBUG_EVENT",
    2: "CREATE_THREAD_DEBUG_EVENT",
    3: "CREATE_PROCESS_DEBUG_EVENT",
    4: "EXIT_THREAD_DEBUG_EVENT",
    5: "EXIT_PROCESS_DEBUG_EVENT",
    6: "LOAD_DLL_DEBUG_EVENT",
    7: "UNLOAD_DLL_DEBUG_EVENT",
    8: "OUTPUT_DEBUG_STRING_EVENT",
    9: "RIP_EVENT",
}

# ---------------------------------------------------------------------------
# Win32 structures
# ---------------------------------------------------------------------------

class EXCEPTION_RECORD(ctypes.Structure):
    pass

EXCEPTION_RECORD._fields_ = [
    ("ExceptionCode", wintypes.DWORD),
    ("ExceptionFlags", wintypes.DWORD),
    ("ExceptionRecord", ctypes.POINTER(EXCEPTION_RECORD)),
    ("ExceptionAddress", ctypes.c_void_p),
    ("NumberParameters", wintypes.DWORD),
    ("ExceptionInformation", ctypes.c_ulonglong * 15),
]


class EXCEPTION_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ("ExceptionRecord", EXCEPTION_RECORD),
        ("dwFirstChance", wintypes.DWORD),
    ]


class CREATE_THREAD_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ("hThread", wintypes.HANDLE),
        ("lpThreadLocalBase", ctypes.c_void_p),
        ("lpStartAddress", ctypes.c_void_p),
    ]


class CREATE_PROCESS_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ("hFile", wintypes.HANDLE),
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("lpBaseOfImage", ctypes.c_void_p),
        ("dwDebugInfoFileOffset", wintypes.DWORD),
        ("nDebugInfoSize", wintypes.DWORD),
        ("lpThreadLocalBase", ctypes.c_void_p),
        ("lpStartAddress", ctypes.c_void_p),
        ("lpImageName", ctypes.c_void_p),
        ("fUnicode", wintypes.WORD),
    ]


class EXIT_THREAD_DEBUG_INFO(ctypes.Structure):
    _fields_ = [("dwExitCode", wintypes.DWORD)]


class EXIT_PROCESS_DEBUG_INFO(ctypes.Structure):
    _fields_ = [("dwExitCode", wintypes.DWORD)]


class LOAD_DLL_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ("hFile", wintypes.HANDLE),
        ("lpBaseOfDll", ctypes.c_void_p),
        ("dwDebugInfoFileOffset", wintypes.DWORD),
        ("nDebugInfoSize", wintypes.DWORD),
        ("lpImageName", ctypes.c_void_p),
        ("fUnicode", wintypes.WORD),
    ]


class UNLOAD_DLL_DEBUG_INFO(ctypes.Structure):
    _fields_ = [("lpBaseOfDll", ctypes.c_void_p)]


class OUTPUT_DEBUG_STRING_INFO(ctypes.Structure):
    _fields_ = [
        ("lpDebugStringData", ctypes.c_void_p),
        ("fUnicode", wintypes.WORD),
        ("nDebugStringLength", wintypes.WORD),
    ]


class RIP_INFO(ctypes.Structure):
    _fields_ = [
        ("dwError", wintypes.DWORD),
        ("dwType", wintypes.DWORD),
    ]


class DEBUG_EVENT_UNION(ctypes.Union):
    _fields_ = [
        ("Exception", EXCEPTION_DEBUG_INFO),
        ("CreateThread", CREATE_THREAD_DEBUG_INFO),
        ("CreateProcessInfo", CREATE_PROCESS_DEBUG_INFO),
        ("ExitThread", EXIT_THREAD_DEBUG_INFO),
        ("ExitProcess", EXIT_PROCESS_DEBUG_INFO),
        ("LoadDll", LOAD_DLL_DEBUG_INFO),
        ("UnloadDll", UNLOAD_DLL_DEBUG_INFO),
        ("DebugString", OUTPUT_DEBUG_STRING_INFO),
        ("RipInfo", RIP_INFO),
    ]


class DEBUG_EVENT(ctypes.Structure):
    _fields_ = [
        ("dwDebugEventCode", wintypes.DWORD),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
        ("u", DEBUG_EVENT_UNION),
    ]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.c_char_p),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


# ---------------------------------------------------------------------------
# API declarations (argtypes / restype)
# ---------------------------------------------------------------------------

def _declare_win32_apis() -> ctypes.WinDLL:
    """Declare ctypes argtypes and restype for every Win32 call we make."""
    if os.name != "nt":
        return None
    k32 = ctypes.windll.kernel32

    k32.CreateProcessW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.BOOL,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.LPCWSTR,
        ctypes.POINTER(STARTUPINFOW),
        ctypes.POINTER(PROCESS_INFORMATION),
    ]
    k32.CreateProcessW.restype = wintypes.BOOL

    k32.WaitForDebugEvent.argtypes = [ctypes.POINTER(DEBUG_EVENT), wintypes.DWORD]
    k32.WaitForDebugEvent.restype = wintypes.BOOL

    k32.ContinueDebugEvent.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD]
    k32.ContinueDebugEvent.restype = wintypes.BOOL

    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    k32.CloseHandle.restype = wintypes.BOOL

    k32.GetFinalPathNameByHandleW.argtypes = [
        wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD
    ]
    k32.GetFinalPathNameByHandleW.restype = wintypes.DWORD

    k32.GetLastError.argtypes = []
    k32.GetLastError.restype = wintypes.DWORD

    k32.DebugActiveProcessStop.argtypes = [wintypes.DWORD]
    k32.DebugActiveProcessStop.restype = wintypes.BOOL

    return k32


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_path_from_handle(k32: ctypes.WinDLL, h_file) -> str | None:
    """Resolve a Win32 file handle to a path string; returns None on failure."""
    if not h_file:
        return None
    buf = ctypes.create_unicode_buffer(1024)
    res = k32.GetFinalPathNameByHandleW(h_file, buf, 1024, 0)
    if res > 0:
        val = buf.value
        if val.startswith("\\\\?\\"):
            val = val[4:]
        return val
    return None


def _close_handle(k32: ctypes.WinDLL, h) -> None:
    """Close a Win32 handle; ignore null/zero handles."""
    if h:
        k32.CloseHandle(h)


def _sanitize_path(p: str | None) -> str | None:
    """Replace USERPROFILE prefix with a placeholder for privacy."""
    if not p:
        return None
    userprofile = os.environ.get("USERPROFILE", "")
    if userprofile and userprofile in p:
        p = p.replace(userprofile, "<USERPROFILE>")
    return p.replace("\\", "/")


# ---------------------------------------------------------------------------
# Main tracer
# ---------------------------------------------------------------------------

def trace_native_launch(
    exe_path: str,
    *,
    timeout_ms: int = 10000,
    max_events: int = 500,
) -> dict:
    """Launch *exe_path* under DEBUG_ONLY_THIS_PROCESS and collect debug events.

    Returns a dict suitable for JSON serialisation.  The dict includes a
    ``collection_status`` field: ``"complete"`` when EXIT_PROCESS was observed,
    ``"timeout"`` when the per-event wait expired before EXIT_PROCESS, or
    ``"event_cap"`` when ``max_events`` was reached.

    ``entry_point_measured`` is always ``False`` and ``entry_point_reached`` is
    always ``None`` because this harness installs no entry-point probe.
    """
    if os.name != "nt":
        raise RuntimeError("Windows native debugger harness requires Windows (os.name == 'nt')")

    k32 = _declare_win32_apis()
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(STARTUPINFOW)
    pi = PROCESS_INFORMATION()

    abs_exe = str(Path(exe_path).resolve())
    work_dir = str(Path(abs_exe).parent)
    start_time = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()

    ok = k32.CreateProcessW(
        abs_exe,
        None,
        None,
        None,
        False,
        DEBUG_ONLY_THIS_PROCESS,
        None,
        work_dir,
        ctypes.byref(si),
        ctypes.byref(pi),
    )
    if not ok:
        err = k32.GetLastError()
        return {
            "schema": "openbot.windows-debug-trace/2",
            "collection_status": "creation_failed",
            "collection_error": f"CreateProcessW failed: error {err} (0x{err:08x})",
            "executable": _sanitize_path(abs_exe),
            "harness": "tools/windows-debug-trace.py",
            "start_time": start_time,
            "end_time": datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(),
            "entry_point_measured": False,
            "entry_point_reached": None,
        }

    h_process = pi.hProcess
    h_thread = pi.hThread
    target_pid = pi.dwProcessId

    events: list[dict] = []
    debug_event = DEBUG_EVENT()
    process_exit_code: str | None = None
    collection_status = "incomplete"
    entry_point_crt_address: str | None = None
    loaded_modules: list[dict] = []

    # Tracks open image/DLL file handles so we can close them (debugger owns them).
    open_image_handles: list = []

    try:
        while len(events) < max_events:
            if not k32.WaitForDebugEvent(ctypes.byref(debug_event), timeout_ms):
                err = k32.GetLastError()
                events.append({
                    "sequence": len(events) + 1,
                    "event_name": "WAIT_TIMEOUT_OR_ERROR",
                    "win32_last_error": err,
                })
                collection_status = "timeout"
                break

            code = debug_event.dwDebugEventCode
            pid = debug_event.dwProcessId
            tid = debug_event.dwThreadId
            event_name = EVENT_NAMES.get(code, f"UNKNOWN_{code}")

            rec: dict = {
                "sequence": len(events) + 1,
                "event_code": code,
                "event_name": event_name,
                "pid": pid,
                "tid": tid,
            }

            # Default: continue normally.
            continue_status = DBG_CONTINUE

            if code == CREATE_PROCESS_DEBUG_EVENT:
                info = debug_event.u.CreateProcessInfo
                base = info.lpBaseOfImage
                start_addr = info.lpStartAddress
                entry_point_crt_address = hex(start_addr) if start_addr else None
                raw_path = _get_path_from_handle(k32, info.hFile)
                # hFile is owned by this debugger; close it after resolving path.
                if info.hFile:
                    open_image_handles.append(info.hFile)
                rec.update({
                    "image_base": hex(base) if base else None,
                    "pe_entry_crt_address": entry_point_crt_address,
                    "pe_entry_note": (
                        "lpStartAddress from CREATE_PROCESS_DEBUG_INFO is the CRT startup "
                        "address derived from PE AddressOfEntryPoint + load-delta.  "
                        "Source-level application entry (e.g. wWinMain) is a distinct later "
                        "stage not instrumented here."
                    ),
                    "image_path": _sanitize_path(raw_path),
                })
                loaded_modules.append({
                    "type": "main_executable",
                    "base": hex(base) if base else None,
                    "path": _sanitize_path(raw_path),
                })

            elif code == LOAD_DLL_DEBUG_EVENT:
                info = debug_event.u.LoadDll
                base = info.lpBaseOfDll
                raw_path = _get_path_from_handle(k32, info.hFile)
                # hFile is owned by this debugger; close it after resolving path.
                if info.hFile:
                    open_image_handles.append(info.hFile)
                rec.update({
                    "dll_base": hex(base) if base else None,
                    "dll_path": _sanitize_path(raw_path),
                })
                loaded_modules.append({
                    "type": "dll",
                    "base": hex(base) if base else None,
                    "path": _sanitize_path(raw_path),
                })

            elif code == UNLOAD_DLL_DEBUG_EVENT:
                info = debug_event.u.UnloadDll
                rec["dll_base"] = hex(info.lpBaseOfDll) if info.lpBaseOfDll else None

            elif code == CREATE_THREAD_DEBUG_EVENT:
                info = debug_event.u.CreateThread
                rec["start_address"] = hex(info.lpStartAddress) if info.lpStartAddress else None

            elif code == EXCEPTION_DEBUG_EVENT:
                info = debug_event.u.Exception
                exc = info.ExceptionRecord
                exc_code = exc.ExceptionCode & 0xFFFFFFFF  # keep unsigned
                exc_addr = exc.ExceptionAddress
                first_chance = bool(info.dwFirstChance)
                rec.update({
                    "exception_code": hex(exc_code),
                    "exception_address": hex(exc_addr) if exc_addr else None,
                    "first_chance": first_chance,
                })
                if exc_code == STATUS_BREAKPOINT and first_chance:
                    # Normal initial debugger breakpoint — continue so the target proceeds.
                    continue_status = DBG_CONTINUE
                    rec["exception_disposition"] = "DBG_CONTINUE (initial breakpoint)"
                else:
                    # Forward genuine application exceptions unhandled.
                    continue_status = DBG_EXCEPTION_NOT_HANDLED
                    rec["exception_disposition"] = "DBG_EXCEPTION_NOT_HANDLED"

            elif code == EXIT_THREAD_DEBUG_EVENT:
                info = debug_event.u.ExitThread
                rec["exit_code"] = hex(info.dwExitCode)

            elif code == EXIT_PROCESS_DEBUG_EVENT:
                info = debug_event.u.ExitProcess
                process_exit_code = hex(info.dwExitCode)
                rec["exit_code"] = process_exit_code
                events.append(rec)
                # Must ContinueDebugEvent before EXIT_PROCESS can fully complete.
                ok = k32.ContinueDebugEvent(pid, tid, DBG_CONTINUE)
                if not ok:
                    err = k32.GetLastError()
                    events.append({
                        "sequence": len(events) + 1,
                        "event_name": "CONTINUE_DEBUG_EVENT_FAILED",
                        "win32_last_error": err,
                    })
                collection_status = "complete"
                break

            events.append(rec)
            ok_cont = k32.ContinueDebugEvent(pid, tid, continue_status)
            if not ok_cont:
                err = k32.GetLastError()
                events.append({
                    "sequence": len(events) + 1,
                    "event_name": "CONTINUE_DEBUG_EVENT_FAILED",
                    "win32_last_error": err,
                })

        else:
            collection_status = "event_cap"

    finally:
        # Close image/DLL file handles owned by this debugger.
        for h in open_image_handles:
            _close_handle(k32, h)
        # Detach debugger if EXIT_PROCESS was not observed.
        if collection_status != "complete":
            k32.DebugActiveProcessStop(target_pid)
        # Close PROCESS_INFORMATION handles.
        _close_handle(k32, h_thread)
        _close_handle(k32, h_process)

    end_time = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()

    return {
        "schema": "openbot.windows-debug-trace/2",
        "harness": "tools/windows-debug-trace.py",
        "harness_version": 2,
        "executable": _sanitize_path(abs_exe),
        "start_time": start_time,
        "end_time": end_time,
        "collection_status": collection_status,
        # Entry-point measurement is not implemented in this harness.
        "entry_point_measured": False,
        "entry_point_reached": None,
        "pe_entry_crt_address": entry_point_crt_address,
        "process_exit_code": process_exit_code,
        "total_events_recorded": len(events),
        "loaded_modules_before_termination": loaded_modules,
        "diagnostic_limitations": (
            "1. Entry-point execution is not instrumented: entry_point_reached is "
            "null and entry_point_measured is false. The CRT startup address "
            "pe_entry_crt_address is the PE AddressOfEntryPoint + load-delta; "
            "source-level wWinMain is a distinct later stage. "
            "2. This harness records only modules successfully LOAD_DLL-notified "
            "by the NT loader before EXIT_PROCESS. Absence of a module's "
            "LOAD_DLL notification is consistent with loader failure before that "
            "module was mapped, but does not establish the exact failing instruction "
            "or header element. "
            "3. No exception address or stack was captured in the three-event run-2 "
            "recording; no EXCEPTION_DEBUG_EVENT was observed."
        ),
        "events": events,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", help="Path to Windows executable to trace")
    parser.add_argument("--output", help="Path to write JSON trace output")
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=10000,
        help="Per-event wait timeout in milliseconds (default 10000)",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=500,
        help="Maximum debug events to collect before stopping (default 500)",
    )
    args = parser.parse_args()

    try:
        result = trace_native_launch(
            args.exe,
            timeout_ms=args.timeout_ms,
            max_events=args.max_events,
        )
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(encoded, encoding="utf-8", newline="\n")
        print(f"Trace written to {out_path}")
    else:
        print(encoded, end="")

    # Non-zero exit if collection did not complete normally.
    status = result.get("collection_status", "")
    return 0 if status == "complete" else 2


if __name__ == "__main__":
    sys.exit(main())
