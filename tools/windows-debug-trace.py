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
- At most the first first-chance STATUS_BREAKPOINT is treated as the debugger
  startup breakpoint. Its bootstrap identity is assumed, not address-validated.
  Later breakpoints, all second-chance exceptions and other exceptions are
  forwarded with DBG_EXCEPTION_NOT_HANDLED. This is not an entry probe.
- File handles supplied in CREATE_PROCESS_DEBUG_INFO.hFile and
  LOAD_DLL_DEBUG_INFO.hFile are owned by the caller (this debugger) and are
  closed explicitly after path resolution (see Microsoft WaitForDebugEvent docs).
- Both an event-count cap and a monotonic collection deadline bound the event loop.
- Incomplete sessions explicitly detach only the newly created target; a detached
  target may continue running. This is not a workload kill/reap guarantee.
- Optional --debug-strings reads only OS-reported debug-string payloads from
  the newly created target: at most 16 KiB per event and 256 KiB in total.
  Partial/failed/truncated requested capture is explicit and gives CLI failure.
  Capture may contain sensitive text. This tool NEVER enables loader snaps,
  edits registry settings, installs tools or approves host changes.
- ContinueDebugEvent and all cleanup paths are checked; non-zero exit status
  is returned on collection or setup errors.
"""

from __future__ import annotations

import argparse
import base64
import ctypes
import datetime
import json
import os
import sys
import time
from ctypes import wintypes
from pathlib import Path

# ---------------------------------------------------------------------------
# Win32 constants
# ---------------------------------------------------------------------------
DEBUG_ONLY_THIS_PROCESS = 0x00000002
DBG_CONTINUE = 0x00010002
DBG_EXCEPTION_NOT_HANDLED = 0x80010001

# Exception codes
STATUS_BREAKPOINT = 0x80000003  # Normal initial debugger breakpoint
STATUS_INVALID_IMAGE_FORMAT = 0xC000007B
MAX_DEBUG_STRING_BYTES = 16384
DEBUG_STRING_BUDGET_BYTES = 262144

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
    if ctypes.sizeof(ctypes.c_void_p) != 8 or ctypes.sizeof(wintypes.DWORD) != 4:
        raise RuntimeError("This Win32 recorder requires a 64-bit Windows Python interpreter")
    if (
        ctypes.sizeof(DEBUG_EVENT),
        ctypes.sizeof(STARTUPINFOW),
        ctypes.sizeof(PROCESS_INFORMATION),
    ) != (176, 104, 24):
        raise RuntimeError("Unexpected native debugger structure layout; refusing launch")
    # Keep Windows' thread-local last-error value across ctypes/Python work.
    # GetLastError is obtained from this same use_last_error-enabled library.
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)

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

    # Ex opts into Unicode debug-string delivery on the supported Windows 10+ path.
    k32.WaitForDebugEventEx.argtypes = [ctypes.POINTER(DEBUG_EVENT), wintypes.DWORD]
    k32.WaitForDebugEventEx.restype = wintypes.BOOL
    k32.ReadProcessMemory.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    k32.ReadProcessMemory.restype = wintypes.BOOL

    k32.ContinueDebugEvent.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD]
    k32.ContinueDebugEvent.restype = wintypes.BOOL

    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    k32.CloseHandle.restype = wintypes.BOOL

    k32.GetFinalPathNameByHandleW.argtypes = [
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
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
    if 0 < res < len(buf):
        val = buf.value
        if val.startswith("\\\\?\\"):
            val = val[4:]
        return val
    return None


def _close_handle(k32: ctypes.WinDLL, h) -> bool:
    """Report cleanup failure rather than silently treating it as success."""
    return not h or bool(k32.CloseHandle(h))


def _capture_debug_string(k32, process_handle, info, remaining_bytes):
    """Read only this owned target's reported debug string, once and within caps.

    Raw bytes are retained for fidelity. Non-Unicode text is a Latin-1 byte view,
    not a claim about the target's active ANSI code page. Payloads can contain
    sensitive paths/data; capture is opt-in and is not a public-log sanitizer.
    """
    wide = bool(info.fUnicode)
    # Microsoft specifies low 16 bits of the BYTE length, including for Unicode.
    # Do not multiply by two or scan beyond that reported range for a terminator.
    declared = int(info.nDebugStringLength)
    result = {
        "status": "complete",
        "declared_bytes": declared,
        "bytes_read": 0,
        "reported_length_is_lower_16_bits": True,
        "encoding": "utf-16-le" if wide else "latin-1-byte-view",
        "text": "",
        "raw_base64": "",
    }
    if declared == 0:
        return result
    if not process_handle or not info.lpDebugStringData:
        result["status"] = "invalid_pointer_or_handle"
        return result
    size = min(declared, MAX_DEBUG_STRING_BYTES, max(0, remaining_bytes))
    if size == 0:
        result["status"] = "budget_exhausted"
        return result
    buffer = ctypes.create_string_buffer(size)
    count = ctypes.c_size_t()
    try:
        ok = bool(
            k32.ReadProcessMemory(
                process_handle, info.lpDebugStringData, buffer, size, ctypes.byref(count)
            )
        )
        error = int(k32.GetLastError()) if not ok else None
    except Exception as exc:
        result.update(status="reader_exception", error_type=type(exc).__name__)
        return result
    if count.value > size:
        result["status"] = "invalid_read_count"
        return result
    data = buffer.raw[: count.value]
    result["bytes_read"] = len(data)
    result["raw_base64"] = base64.b64encode(data).decode("ascii")
    text_bytes = data
    terminator = b"\x00\x00" if wide else b"\x00"
    if (not wide or len(text_bytes) % 2 == 0) and text_bytes.endswith(terminator):
        text_bytes = text_bytes[: -len(terminator)]
    encoding = "utf-16-le" if wide else "latin-1"
    try:
        result["text"] = text_bytes.decode(encoding, errors="strict")
        result["text_decode_had_errors"] = False
    except UnicodeDecodeError:
        result["text"] = text_bytes.decode(encoding, errors="replace")
        result["text_decode_had_errors"] = True
    if not ok:
        result.update(status="read_failed", win32_last_error=error)
    elif len(data) < size:
        result["status"] = "partial_read"
    elif result.get("text_decode_had_errors"):
        result["status"] = "invalid_encoding"
    elif size < declared:
        result["status"] = "truncated"
    return result


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
    session_timeout_ms: int = 30000,
    capture_debug_strings: bool = False,
) -> dict:
    """Observe debug notifications, never infer unmeasured entry execution.

    Per-wait timeout, total collection deadline and event cap are independent.
    Only a successfully continued EXIT_PROCESS plus successful cleanup is
    complete. Incomplete sessions attempt a checked detach of this target;
    detach is NOT termination and the target may continue running. Native API
    setup/cleanup and Windows execution still require a real Windows check.
    """
    if os.name != "nt":
        raise RuntimeError("Windows native debugger harness requires Windows")
    for name, value, maximum in (
        ("timeout_ms", timeout_ms, 60000),
        ("max_events", max_events, 10000),
        ("session_timeout_ms", session_timeout_ms, 120000),
    ):
        if type(value) is not int or not 1 <= value <= maximum:
            raise ValueError(f"{name} must be an integer between 1 and {maximum}")

    if type(capture_debug_strings) is not bool:
        raise ValueError("capture_debug_strings must be a Boolean")
    k32 = _declare_win32_apis()
    wait_for_event = k32.WaitForDebugEventEx if capture_debug_strings else k32.WaitForDebugEvent
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(STARTUPINFOW)
    pi = PROCESS_INFORMATION()
    abs_exe = str(Path(exe_path).resolve())
    start_time = datetime.datetime.now(datetime.UTC).astimezone().isoformat()
    ok = k32.CreateProcessW(
        abs_exe,
        None,
        None,
        None,
        False,
        DEBUG_ONLY_THIS_PROCESS,
        None,
        str(Path(abs_exe).parent),
        ctypes.byref(si),
        ctypes.byref(pi),
    )
    if not ok:
        err = k32.GetLastError()
        return {
            "schema": "openbot.windows-debug-trace/4",
            "harness_version": 4,
            "collection_status": "creation_failed",
            "collection_error": f"CreateProcessW failed: error {err} (0x{err:08x})",
            "executable": _sanitize_path(abs_exe),
            "harness": "tools/windows-debug-trace.py",
            "start_time": start_time,
            "end_time": datetime.datetime.now(datetime.UTC).astimezone().isoformat(),
            "entry_point_measured": False,
            "entry_point_reached": None,
            "cleanup_status": "not_needed",
            "debug_string_capture_requested": capture_debug_strings,
            "debug_string_capture_status": "not_started"
            if capture_debug_strings
            else "not_requested",
            "debug_string_bytes_captured": 0,
        }

    events: list[dict] = []
    loaded_modules: list[dict] = []
    open_image_handles: list = []
    cleanup_errors: list[dict] = []
    debug_string_bytes = 0
    debug_string_incomplete = False
    debug_event = DEBUG_EVENT()
    process_exit_code = None
    entry_point_crt_address = None
    collection_status = "incomplete"
    exit_event_continued = False
    first_breakpoint_consumed = False
    detached = None
    deadline = time.monotonic() + session_timeout_ms / 1000

    def record_error(name, **details):
        events.append({"sequence": len(events) + 1, "event_name": name, **details})

    try:
        while len(events) < max_events:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                record_error("COLLECTION_DEADLINE_REACHED")
                collection_status = "deadline"
                break
            wait_ms = min(timeout_ms, max(1, int(remaining * 1000)))
            if not wait_for_event(ctypes.byref(debug_event), wait_ms):
                err = k32.GetLastError()
                record_error("WAIT_TIMEOUT_OR_ERROR", win32_last_error=err)
                if time.monotonic() >= deadline:
                    collection_status = "deadline"
                else:
                    collection_status = "timeout" if err in (121, 258) else "wait_failed"
                break

            code = debug_event.dwDebugEventCode
            pid, tid = debug_event.dwProcessId, debug_event.dwThreadId
            rec = {
                "sequence": len(events) + 1,
                "event_code": code,
                "event_name": EVENT_NAMES.get(code, f"UNKNOWN_{code}"),
                "pid": pid,
                "tid": tid,
            }
            continue_status = DBG_CONTINUE
            if code == CREATE_PROCESS_DEBUG_EVENT:
                info = debug_event.u.CreateProcessInfo
                if info.hFile:
                    open_image_handles.append(info.hFile)
                raw_path = _get_path_from_handle(k32, info.hFile)
                entry_point_crt_address = hex(info.lpStartAddress) if info.lpStartAddress else None
                rec.update(
                    {
                        "image_base": hex(info.lpBaseOfImage) if info.lpBaseOfImage else None,
                        "pe_entry_crt_address": entry_point_crt_address,
                        "pe_entry_note": "Reported thread start address, not a measurement of execution; source-level wWinMain is distinct.",
                        "image_path": _sanitize_path(raw_path),
                    }
                )
                loaded_modules.append(
                    {
                        "type": "main_executable",
                        "base": rec["image_base"],
                        "path": rec["image_path"],
                    }
                )
            elif code == LOAD_DLL_DEBUG_EVENT:
                info = debug_event.u.LoadDll
                if info.hFile:
                    open_image_handles.append(info.hFile)
                raw_path = _get_path_from_handle(k32, info.hFile)
                rec.update(
                    {
                        "dll_base": hex(info.lpBaseOfDll) if info.lpBaseOfDll else None,
                        "dll_path": _sanitize_path(raw_path),
                    }
                )
                loaded_modules.append(
                    {
                        "type": "dll",
                        "base": rec["dll_base"],
                        "path": rec["dll_path"],
                    }
                )
            elif code == UNLOAD_DLL_DEBUG_EVENT:
                base = debug_event.u.UnloadDll.lpBaseOfDll
                rec["dll_base"] = hex(base) if base else None
            elif code == CREATE_THREAD_DEBUG_EVENT:
                addr = debug_event.u.CreateThread.lpStartAddress
                rec["start_address"] = hex(addr) if addr else None
            elif code == EXCEPTION_DEBUG_EVENT:
                info = debug_event.u.Exception
                exc_code = info.ExceptionRecord.ExceptionCode & 0xFFFFFFFF
                addr = info.ExceptionRecord.ExceptionAddress
                first_chance = bool(info.dwFirstChance)
                rec.update(
                    {
                        "exception_code": hex(exc_code),
                        "exception_address": hex(addr) if addr else None,
                        "first_chance": first_chance,
                    }
                )
                if exc_code == STATUS_BREAKPOINT and first_chance and not first_breakpoint_consumed:
                    first_breakpoint_consumed = True
                    rec["exception_disposition"] = (
                        "DBG_CONTINUE (first breakpoint assumed to be debugger startup)"
                    )
                else:
                    continue_status = DBG_EXCEPTION_NOT_HANDLED
                    rec["exception_disposition"] = "DBG_EXCEPTION_NOT_HANDLED"
            elif code == OUTPUT_DEBUG_STRING_EVENT:
                if capture_debug_strings:
                    captured = _capture_debug_string(
                        k32,
                        pi.hProcess,
                        debug_event.u.DebugString,
                        DEBUG_STRING_BUDGET_BYTES - debug_string_bytes,
                    )
                    debug_string_bytes += captured["bytes_read"]
                    debug_string_incomplete |= captured["status"] != "complete"
                    rec["debug_string"] = captured
                else:
                    rec["debug_string"] = {"status": "not_requested"}
            elif code == EXIT_THREAD_DEBUG_EVENT:
                rec["exit_code"] = hex(debug_event.u.ExitThread.dwExitCode)
            elif code == EXIT_PROCESS_DEBUG_EVENT:
                process_exit_code = hex(debug_event.u.ExitProcess.dwExitCode)
                rec["exit_code"] = process_exit_code

            events.append(rec)
            if not k32.ContinueDebugEvent(pid, tid, continue_status):
                err = k32.GetLastError()
                record_error("CONTINUE_DEBUG_EVENT_FAILED", win32_last_error=err)
                collection_status = "continue_failed"
                break
            if code == EXIT_PROCESS_DEBUG_EVENT:
                exit_event_continued = True
                collection_status = "complete"
                break
        else:
            collection_status = "event_cap"
    except Exception as exc:
        # Explicit failed collection, never a fabricated native target exception.
        record_error("COLLECTOR_EXCEPTION", error_type=type(exc).__name__)
        collection_status = "collector_exception"
    finally:
        # Cleanup must try all owned resources even if one cleanup operation fails.
        for label, handle in [("image_file", h) for h in open_image_handles]:
            try:
                if not _close_handle(k32, handle):
                    cleanup_errors.append(
                        {
                            "operation": "CloseHandle(" + label + ")",
                            "win32_last_error": k32.GetLastError(),
                        }
                    )
            except Exception as exc:
                cleanup_errors.append(
                    {"operation": "CloseHandle(" + label + ")", "error_type": type(exc).__name__}
                )
        if not exit_event_continued:
            try:
                detached = bool(k32.DebugActiveProcessStop(pi.dwProcessId))
                if not detached:
                    cleanup_errors.append(
                        {
                            "operation": "DebugActiveProcessStop",
                            "win32_last_error": k32.GetLastError(),
                        }
                    )
            except Exception as exc:
                detached = False
                cleanup_errors.append(
                    {"operation": "DebugActiveProcessStop", "error_type": type(exc).__name__}
                )
        for label, handle in (("thread", pi.hThread), ("process", pi.hProcess)):
            try:
                if not _close_handle(k32, handle):
                    cleanup_errors.append(
                        {
                            "operation": "CloseHandle(" + label + ")",
                            "win32_last_error": k32.GetLastError(),
                        }
                    )
            except Exception as exc:
                cleanup_errors.append(
                    {"operation": "CloseHandle(" + label + ")", "error_type": type(exc).__name__}
                )

    event_collection_status = collection_status
    if debug_string_incomplete and collection_status == "complete":
        collection_status = "diagnostic_incomplete"
    if cleanup_errors:
        record_error("CLEANUP_FAILED", operations=cleanup_errors)
        if collection_status == "complete":
            collection_status = "cleanup_failed"
    return {
        "schema": "openbot.windows-debug-trace/4",
        "harness": "tools/windows-debug-trace.py",
        "harness_version": 4,
        "executable": _sanitize_path(abs_exe),
        "target_pid": pi.dwProcessId,
        "start_time": start_time,
        "end_time": datetime.datetime.now(datetime.UTC).astimezone().isoformat(),
        "collection_status": collection_status,
        "event_collection_status": event_collection_status,
        "cleanup_status": "failed" if cleanup_errors else "ok",
        "cleanup_errors": cleanup_errors,
        "debugger_detached": detached,
        "target_may_continue_after_detach": detached is True,
        "collection_budget_ms": session_timeout_ms,
        "debug_string_capture_requested": capture_debug_strings,
        "debug_string_capture_status": (
            "not_requested"
            if not capture_debug_strings
            else "incomplete"
            if debug_string_incomplete
            else "complete"
        ),
        "debug_string_bytes_captured": debug_string_bytes,
        "debug_string_per_event_cap": MAX_DEBUG_STRING_BYTES,
        "debug_string_total_cap": DEBUG_STRING_BUDGET_BYTES,
        "debug_strings_may_contain_sensitive_data": capture_debug_strings,
        "entry_point_measured": False,
        "entry_point_reached": None,
        "pe_entry_crt_address": entry_point_crt_address,
        "process_exit_code": process_exit_code,
        "total_events_recorded": len(events),
        "loaded_modules_before_termination": loaded_modules,
        "module_paths_resolved": all(m["path"] is not None for m in loaded_modules),
        "diagnostic_limitations": (
            "Entry execution is unmeasured; reported start address is not execution proof. "
            "Only observed debug notifications are recorded, not every mapping attempt or a stack. "
            "Unresolved module paths cannot prove a named module's absence. "
            "Exception fields are recorded only when an exception notification arrives; no stack is captured. "
            "The first first-chance breakpoint is assumed to be debugger startup, not address-validated. "
            "The collection deadline bounds waits/event-loop checks, not arbitrary native API blocking. "
            "Target ISA is not independently checked; native validation is limited to the intended x64 workflow. "
            "A successful detach can leave this target running; detach is not a workload stop/reap guarantee. "
            "Debug-string capture is explicit opt-in, bounded, and can contain unredacted sensitive data. "
            "ANSI payload text is a Latin-1 byte view; raw_base64 preserves the observed bytes. "
            "Debug-string lengths are low-16-bit byte counts: complete capture covers that reported range, not necessarily the original full string. "
            "Collection exit zero means successful collection/cleanup, not successful native application launch."
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
    parser.add_argument(
        "--session-timeout-ms",
        type=int,
        default=30000,
        help="Total event-collection budget in milliseconds (1..120000; default30000)",
    )
    parser.add_argument(
        "--debug-strings",
        action="store_true",
        help="Opt in to bounded debug-string payload capture from this target; use a PRIVATE new output file",
    )
    args = parser.parse_args()
    output = Path(args.output) if args.output else None
    if args.debug_strings and output is None:
        parser.error(
            "--debug-strings requires --output in a PRIVATE directory; payloads may contain secrets"
        )
    if output is not None and (output.exists() or output.is_symlink()):
        parser.error("output must be a NEW filename; existing recordings are never overwritten")

    try:
        result = trace_native_launch(
            args.exe,
            timeout_ms=args.timeout_ms,
            max_events=args.max_events,
            session_timeout_ms=args.session_timeout_ms,
            capture_debug_strings=args.debug_strings,
        )
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if output is not None:
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(encoded)
        except OSError as exc:
            print(f"Trace output failed: {type(exc).__name__}", file=sys.stderr)
            return 2
        print(f"Trace written to {output}")
    else:
        print(encoded, end="")

    # Non-zero exit if collection did not complete normally.
    status = result.get("collection_status", "")
    return 0 if status == "complete" and result.get("cleanup_status") == "ok" else 2


if __name__ == "__main__":
    sys.exit(main())
