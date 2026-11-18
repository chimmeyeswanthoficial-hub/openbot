#!/usr/bin/env python3
"""Windows Native Loader Debugger Trace Harness.

Attaches a Win32 debugging loop (DEBUG_ONLY_THIS_PROCESS) to observe
early process initialization, DLL loading events, exceptions, and exit status
before and up to user-mode entry.
"""

import argparse
import ctypes
from ctypes import wintypes
import datetime
import json
import os
from pathlib import Path
import sys

# Win32 Debug Constants
DEBUG_ONLY_THIS_PROCESS = 0x00000002
DBG_CONTINUE = 0x00010002
DBG_EXCEPTION_NOT_HANDLED = 0x80010001

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
    9: "RIP_EVENT"
}

class EXCEPTION_RECORD(ctypes.Structure):
    pass
EXCEPTION_RECORD._fields_ = [
    ('ExceptionCode', wintypes.DWORD),
    ('ExceptionFlags', wintypes.DWORD),
    ('ExceptionRecord', ctypes.POINTER(EXCEPTION_RECORD)),
    ('ExceptionAddress', ctypes.c_void_p),
    ('NumberParameters', wintypes.DWORD),
    ('ExceptionInformation', ctypes.c_ulonglong * 15),
]

class EXCEPTION_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ('ExceptionRecord', EXCEPTION_RECORD),
        ('dwFirstChance', wintypes.DWORD),
    ]

class CREATE_THREAD_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ('hThread', wintypes.HANDLE),
        ('lpThreadLocalBase', ctypes.c_void_p),
        ('lpStartAddress', ctypes.c_void_p),
    ]

class CREATE_PROCESS_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ('hFile', wintypes.HANDLE),
        ('hProcess', wintypes.HANDLE),
        ('hThread', wintypes.HANDLE),
        ('lpBaseOfImage', ctypes.c_void_p),
        ('dwDebugInfoFileOffset', wintypes.DWORD),
        ('nDebugInfoSize', wintypes.DWORD),
        ('lpThreadLocalBase', ctypes.c_void_p),
        ('lpStartAddress', ctypes.c_void_p),
        ('lpImageName', ctypes.c_void_p),
        ('fUnicode', wintypes.WORD),
    ]

class EXIT_THREAD_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ('dwExitCode', wintypes.DWORD),
    ]

class EXIT_PROCESS_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ('dwExitCode', wintypes.DWORD),
    ]

class LOAD_DLL_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ('hFile', wintypes.HANDLE),
        ('lpBaseOfDll', ctypes.c_void_p),
        ('dwDebugInfoFileOffset', wintypes.DWORD),
        ('nDebugInfoSize', wintypes.DWORD),
        ('lpImageName', ctypes.c_void_p),
        ('fUnicode', wintypes.WORD),
    ]

class UNLOAD_DLL_DEBUG_INFO(ctypes.Structure):
    _fields_ = [
        ('lpBaseOfDll', ctypes.c_void_p),
    ]

class OUTPUT_DEBUG_STRING_INFO(ctypes.Structure):
    _fields_ = [
        ('lpDebugStringData', ctypes.c_void_p),
        ('fUnicode', wintypes.WORD),
        ('nDebugStringLength', wintypes.WORD),
    ]

class RIP_INFO(ctypes.Structure):
    _fields_ = [
        ('dwError', wintypes.DWORD),
        ('dwType', wintypes.DWORD),
    ]

class DEBUG_EVENT_UNION(ctypes.Union):
    _fields_ = [
        ('Exception', EXCEPTION_DEBUG_INFO),
        ('CreateThread', CREATE_THREAD_DEBUG_INFO),
        ('CreateProcessInfo', CREATE_PROCESS_DEBUG_INFO),
        ('ExitThread', EXIT_THREAD_DEBUG_INFO),
        ('ExitProcess', EXIT_PROCESS_DEBUG_INFO),
        ('LoadDll', LOAD_DLL_DEBUG_INFO),
        ('UnloadDll', UNLOAD_DLL_DEBUG_INFO),
        ('DebugString', OUTPUT_DEBUG_STRING_INFO),
        ('RipInfo', RIP_INFO),
    ]

class DEBUG_EVENT(ctypes.Structure):
    _fields_ = [
        ('dwDebugEventCode', wintypes.DWORD),
        ('dwProcessId', wintypes.DWORD),
        ('dwThreadId', wintypes.DWORD),
        ('u', DEBUG_EVENT_UNION),
    ]

class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD),
        ('lpReserved', wintypes.LPWSTR),
        ('lpDesktop', wintypes.LPWSTR),
        ('lpTitle', wintypes.LPWSTR),
        ('dwX', wintypes.DWORD),
        ('dwY', wintypes.DWORD),
        ('dwXSize', wintypes.DWORD),
        ('dwYSize', wintypes.DWORD),
        ('dwXCountChars', wintypes.DWORD),
        ('dwYCountChars', wintypes.DWORD),
        ('dwFillAttribute', wintypes.DWORD),
        ('dwFlags', wintypes.DWORD),
        ('wShowWindow', wintypes.WORD),
        ('cbReserved2', wintypes.WORD),
        ('lpReserved2', ctypes.c_char_p),
        ('hStdInput', wintypes.HANDLE),
        ('hStdOutput', wintypes.HANDLE),
        ('hStdError', wintypes.HANDLE),
    ]

class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('hProcess', wintypes.HANDLE),
        ('hThread', wintypes.HANDLE),
        ('dwProcessId', wintypes.DWORD),
        ('dwThreadId', wintypes.DWORD),
    ]


def get_path_from_handle(h_file):
    if not h_file:
        return None
    buf = ctypes.create_unicode_buffer(1024)
    # FILE_NAME_NORMALIZED = 0
    res = ctypes.windll.kernel32.GetFinalPathNameByHandleW(h_file, buf, 1024, 0)
    if res > 0:
        val = buf.value
        if val.startswith("\\\\?\\"):
            val = val[4:]
        return val
    return None


def sanitize_path(p):
    if not p:
        return None
    # Replace user profile username with generic placeholder for privacy
    userprofile = os.environ.get("USERPROFILE", "")
    if userprofile and userprofile in p:
        p = p.replace(userprofile, "<USERPROFILE>")
    return p.replace("\\", "/")


def trace_native_launch(exe_path: str, timeout_ms: int = 10000):
    if os.name != "nt":
        raise RuntimeError("Windows native debugger harness must run on Windows")

    kernel32 = ctypes.windll.kernel32
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(STARTUPINFOW)
    pi = PROCESS_INFORMATION()

    abs_exe = str(Path(exe_path).resolve())
    work_dir = str(Path(abs_exe).parent)
    start_time = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()

    success = kernel32.CreateProcessW(
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
    if not success:
        err = kernel32.GetLastError()
        return {
            "error": f"CreateProcessW failed with error {err} (0x{err:08x})",
            "start_time": start_time,
        }

    events = []
    debug_event = DEBUG_EVENT()
    process_exit_code = None
    entry_point_reached = False
    entry_point_address = None
    loaded_modules = []

    try:
        while True:
            if not kernel32.WaitForDebugEvent(ctypes.byref(debug_event), timeout_ms):
                err = kernel32.GetLastError()
                events.append({
                    "event_name": "TIMEOUT_OR_POLL_ERROR",
                    "win32_last_error": err,
                })
                break

            code = debug_event.dwDebugEventCode
            pid = debug_event.dwProcessId
            tid = debug_event.dwThreadId
            event_name = EVENT_NAMES.get(code, f"UNKNOWN_{code}")

            rec = {
                "sequence": len(events) + 1,
                "event_code": code,
                "event_name": event_name,
                "pid": pid,
                "tid": tid,
            }

            continue_status = DBG_CONTINUE

            if code == CREATE_PROCESS_DEBUG_EVENT:
                info = debug_event.u.CreateProcessInfo
                base = info.lpBaseOfImage
                raw_path = get_path_from_handle(info.hFile)
                start_addr = info.lpStartAddress
                entry_point_address = hex(start_addr) if start_addr else None
                rec.update({
                    "image_base": hex(base) if base else None,
                    "entry_point_rva_address": entry_point_address,
                    "image_path": sanitize_path(raw_path),
                })
                loaded_modules.append({
                    "type": "main_executable",
                    "base": hex(base) if base else None,
                    "path": sanitize_path(raw_path),
                })

            elif code == LOAD_DLL_DEBUG_EVENT:
                info = debug_event.u.LoadDll
                base = info.lpBaseOfDll
                raw_path = get_path_from_handle(info.hFile)
                rec.update({
                    "dll_base": hex(base) if base else None,
                    "dll_path": sanitize_path(raw_path),
                })
                loaded_modules.append({
                    "type": "dll",
                    "base": hex(base) if base else None,
                    "path": sanitize_path(raw_path),
                })

            elif code == CREATE_THREAD_DEBUG_EVENT:
                info = debug_event.u.CreateThread
                rec.update({
                    "start_address": hex(info.lpStartAddress) if info.lpStartAddress else None,
                })

            elif code == EXCEPTION_DEBUG_EVENT:
                info = debug_event.u.Exception
                exc = info.ExceptionRecord
                exc_code = exc.ExceptionCode
                exc_addr = exc.ExceptionAddress
                rec.update({
                    "exception_code": hex(exc_code),
                    "exception_address": hex(exc_addr) if exc_addr else None,
                    "first_chance": bool(info.dwFirstChance),
                })
                continue_status = DBG_EXCEPTION_NOT_HANDLED

            elif code == EXIT_THREAD_DEBUG_EVENT:
                info = debug_event.u.ExitThread
                rec.update({
                    "exit_code": hex(info.dwExitCode),
                })

            elif code == EXIT_PROCESS_DEBUG_EVENT:
                info = debug_event.u.ExitProcess
                process_exit_code = hex(info.dwExitCode)
                rec.update({
                    "exit_code": process_exit_code,
                })
                events.append(rec)
                kernel32.ContinueDebugEvent(pid, tid, continue_status)
                break

            events.append(rec)
            kernel32.ContinueDebugEvent(pid, tid, continue_status)

    finally:
        kernel32.CloseHandle(pi.hThread)
        kernel32.CloseHandle(pi.hProcess)

    end_time = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()

    return {
        "schema": "openbot.windows-debug-trace/1",
        "harness": "tools/windows-debug-trace.py",
        "executable": sanitize_path(abs_exe),
        "start_time": start_time,
        "end_time": end_time,
        "entry_point_address_expected": entry_point_address,
        "entry_point_reached": entry_point_reached,
        "process_exit_code": process_exit_code,
        "total_events_recorded": len(events),
        "loaded_modules_before_termination": loaded_modules,
        "diagnostic_limitations": (
            "Trace captures only modules successfully mapped by NT loader before termination. "
            "A trace with only ntdll.dll mapped narrows the failure to initial static dependency "
            "resolution or PE directory/header verification, but does not identify the specific "
            "rejected image or parser failure."
        ),
        "events": events,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", help="Path to Windows executable to trace")
    parser.add_argument("--output", help="Optional path to write JSON trace output")
    args = parser.parse_args()

    result = trace_native_launch(args.exe)
    encoded = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(encoded + "\n", encoding="utf-8", newline="\n")
        print(f"Trace written to {out_path}")
    else:
        print(encoded)


if __name__ == "__main__":
    main()
