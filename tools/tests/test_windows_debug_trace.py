"""Regression tests for tools/windows-debug-trace.py.

All tests use a fake Win32 backend (pure Python); no Windows API calls,
no target process and no native execution.  The fake backend patches the
ctypes.windll.kernel32 interface so the recorder logic can be exercised
on any platform.

Coverage targets (per Arena review daac285):
  T01  entry_point_reached is null and entry_point_measured is False
       regardless of event sequence — including a healthy control sequence.
  T02  initial debugger breakpoint (STATUS_BREAKPOINT first-chance) is
       continued with DBG_CONTINUE, not DBG_EXCEPTION_NOT_HANDLED.
  T03  genuine non-breakpoint first-chance exception is forwarded with
       DBG_EXCEPTION_NOT_HANDLED.
  T04  CreateProcessW failure returns collection_status=creation_failed and
       a non-empty collection_error; no events list.
  T05  per-event timeout sets collection_status=timeout; DebugActiveProcessStop
       is called (detach path).
  T06  max_events cap sets collection_status=event_cap; DebugActiveProcessStop
       is called.
  T07  image file handle from CREATE_PROCESS is closed after path resolution.
  T08  DLL file handle from LOAD_DLL is closed after path resolution.
  T09  ContinueDebugEvent failure appends a CONTINUE_DEBUG_EVENT_FAILED record.
  T10  PROCESS_INFORMATION handles (hProcess, hThread) are always closed in
       the finally block, even when CreateProcessW succeeds and an exception
       is raised during the loop.
  T11  schema is openbot.windows-debug-trace/2; harness_version is 2.
  T12  collection_status == "complete" after EXIT_PROCESS; exit code is captured.
  T13  loaded_modules_before_termination lists only notified modules.
  T14  non-Windows platform raises RuntimeError (not a Windows API call).
  T15  CLI exits with code 2 when collection_status != "complete" (timeout path).
"""

from __future__ import annotations

import ctypes
import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------
_MOD_PATH = Path(__file__).resolve().parents[1] / "windows-debug-trace.py"
_SPEC = importlib.util.spec_from_file_location("windows_debug_trace", _MOD_PATH)
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

trace_native_launch = _MOD.trace_native_launch
STATUS_BREAKPOINT = _MOD.STATUS_BREAKPOINT
DBG_CONTINUE = _MOD.DBG_CONTINUE
DBG_EXCEPTION_NOT_HANDLED = _MOD.DBG_EXCEPTION_NOT_HANDLED
CREATE_PROCESS_DEBUG_EVENT = _MOD.CREATE_PROCESS_DEBUG_EVENT
LOAD_DLL_DEBUG_EVENT = _MOD.LOAD_DLL_DEBUG_EVENT
EXCEPTION_DEBUG_EVENT = _MOD.EXCEPTION_DEBUG_EVENT
EXIT_PROCESS_DEBUG_EVENT = _MOD.EXIT_PROCESS_DEBUG_EVENT
EXIT_THREAD_DEBUG_EVENT = _MOD.EXIT_THREAD_DEBUG_EVENT


# ---------------------------------------------------------------------------
# Fake Win32 backend helpers
# ---------------------------------------------------------------------------

def _make_fake_k32(event_sequence):
    """Return a mock kernel32 that feeds *event_sequence* through WaitForDebugEvent.

    *event_sequence* is a list of dicts with keys:
        code        int   debug event code
        exit_code   int   used for EXIT_PROCESS (optional, default 0)
        exc_code    int   used for EXCEPTION (optional)
        first_chance bool  used for EXCEPTION (optional, default True)
        dll_base    int   used for LOAD_DLL (optional)

    WaitForDebugEvent fills the passed DEBUG_EVENT structure on each call
    by casting the CArgObject back to a pointer to DEBUG_EVENT and writing
    through the pointer.
    After the sequence is exhausted it returns 0 (timeout / error).
    """
    k32 = MagicMock()
    k32.GetLastError.return_value = 0

    sequence = list(event_sequence)

    def _wait(p_event_arg, timeout_ms):
        # p_event_arg is a CArgObject from ctypes.byref(debug_event).
        # Cast it to a pointer so we can write to the underlying structure.
        p = ctypes.cast(p_event_arg, ctypes.POINTER(_MOD.DEBUG_EVENT))
        ev = p[0]

        if not sequence:
            k32.GetLastError.return_value = 258  # WAIT_TIMEOUT
            return 0
        item = sequence.pop(0)
        code = item["code"]
        ev.dwDebugEventCode = code
        ev.dwProcessId = 1234
        ev.dwThreadId = 5678

        if code == CREATE_PROCESS_DEBUG_EVENT:
            ev.u.CreateProcessInfo.lpBaseOfImage = 0x140000000
            ev.u.CreateProcessInfo.lpStartAddress = 0x1400013d0
            ev.u.CreateProcessInfo.hFile = item.get("hFile", 0)
            ev.u.CreateProcessInfo.hProcess = 0
            ev.u.CreateProcessInfo.hThread = 0
        elif code == LOAD_DLL_DEBUG_EVENT:
            ev.u.LoadDll.lpBaseOfDll = item.get("dll_base", 0x7FFF00000000)
            ev.u.LoadDll.hFile = item.get("hFile", 0)
        elif code == EXCEPTION_DEBUG_EVENT:
            exc_code = item.get("exc_code", STATUS_BREAKPOINT)
            ev.u.Exception.ExceptionRecord.ExceptionCode = exc_code
            ev.u.Exception.ExceptionRecord.ExceptionAddress = 0x7FFF12345678
            ev.u.Exception.dwFirstChance = int(item.get("first_chance", True))
        elif code == EXIT_PROCESS_DEBUG_EVENT:
            ev.u.ExitProcess.dwExitCode = item.get("exit_code", 0)
        return 1

    k32.WaitForDebugEvent.side_effect = _wait
    k32.ContinueDebugEvent.return_value = 1
    k32.CloseHandle.return_value = 1
    k32.CreateProcessW.return_value = 1
    k32.GetFinalPathNameByHandleW.return_value = 0  # no path resolution
    k32.DebugActiveProcessStop.return_value = 1
    return k32


def _pi_with(h_process=11, h_thread=12, pid=1234, tid=5678):
    """Return a fake PROCESS_INFORMATION-like object."""
    pi = _MOD.PROCESS_INFORMATION()
    pi.hProcess = h_process
    pi.hThread = h_thread
    pi.dwProcessId = pid
    pi.dwThreadId = tid
    return pi


def _run_trace(event_seq, *, create_ok=True, h_process=11, h_thread=12, timeout_ms=5000, max_events=500):
    """Run trace_native_launch with a fake Win32 backend."""
    k32 = _make_fake_k32(event_seq)

    if not create_ok:
        k32.CreateProcessW.return_value = 0
        k32.GetLastError.return_value = 2  # ERROR_FILE_NOT_FOUND

    pi_obj = _pi_with(h_process=h_process, h_thread=h_thread)

    def _create_proc(*args, **kwargs):
        # Populate PROCESS_INFORMATION out-param.
        p_pi = args[9]  # 10th positional arg
        p_pi._obj.hProcess = pi_obj.hProcess
        p_pi._obj.hThread = pi_obj.hThread
        p_pi._obj.dwProcessId = pi_obj.dwProcessId
        p_pi._obj.dwThreadId = pi_obj.dwThreadId
        return 1 if create_ok else 0

    k32.CreateProcessW.side_effect = _create_proc

    with (
        patch.object(_MOD, "_declare_win32_apis", return_value=k32),
        patch("os.name", "nt"),
    ):
        result = trace_native_launch("fake.exe", timeout_ms=timeout_ms, max_events=max_events)

    return result, k32


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDebugTraceHarness(unittest.TestCase):

    # T01 — entry_point_reached is always null; entry_point_measured always False
    def test_T01_entry_point_never_set_to_true_healthy_exit(self):
        seq = [
            {"code": CREATE_PROCESS_DEBUG_EVENT},
            {"code": LOAD_DLL_DEBUG_EVENT},
            {"code": EXIT_PROCESS_DEBUG_EVENT, "exit_code": 0},
        ]
        result, _ = _run_trace(seq)
        self.assertIs(result["entry_point_reached"], None,
                      "entry_point_reached must be null (not measured)")
        self.assertIs(result["entry_point_measured"], False,
                      "entry_point_measured must be False")

    def test_T01b_entry_point_null_on_failure_exit(self):
        seq = [
            {"code": CREATE_PROCESS_DEBUG_EVENT},
            {"code": LOAD_DLL_DEBUG_EVENT},
            {"code": EXIT_PROCESS_DEBUG_EVENT, "exit_code": 0xC000007B},
        ]
        result, _ = _run_trace(seq)
        self.assertIs(result["entry_point_reached"], None)
        self.assertFalse(result["entry_point_measured"])

    # T02 — initial breakpoint handled with DBG_CONTINUE
    def test_T02_initial_breakpoint_continued(self):
        seq = [
            {"code": CREATE_PROCESS_DEBUG_EVENT},
            {"code": EXCEPTION_DEBUG_EVENT, "exc_code": STATUS_BREAKPOINT, "first_chance": True},
            {"code": EXIT_PROCESS_DEBUG_EVENT, "exit_code": 0},
        ]
        result, k32 = _run_trace(seq)
        # Find the ContinueDebugEvent call that corresponds to the breakpoint event.
        exc_event = next(
            e for e in result["events"] if e["event_name"] == "EXCEPTION_DEBUG_EVENT"
        )
        self.assertIn("DBG_CONTINUE", exc_event.get("exception_disposition", ""),
                      "Initial breakpoint must be continued with DBG_CONTINUE")

    # T03 — genuine exception forwarded with DBG_EXCEPTION_NOT_HANDLED
    def test_T03_genuine_exception_not_handled(self):
        seq = [
            {"code": CREATE_PROCESS_DEBUG_EVENT},
            {"code": EXCEPTION_DEBUG_EVENT, "exc_code": 0xC0000005, "first_chance": True},
            {"code": EXIT_PROCESS_DEBUG_EVENT, "exit_code": 0xC0000005},
        ]
        result, k32 = _run_trace(seq)
        exc_event = next(
            e for e in result["events"] if e["event_name"] == "EXCEPTION_DEBUG_EVENT"
        )
        self.assertIn("DBG_EXCEPTION_NOT_HANDLED", exc_event.get("exception_disposition", ""),
                      "Genuine exception must be forwarded with DBG_EXCEPTION_NOT_HANDLED")

    # T04 — CreateProcessW failure
    def test_T04_create_process_failure(self):
        result, k32 = _run_trace([], create_ok=False)
        self.assertEqual(result["collection_status"], "creation_failed")
        self.assertIn("collection_error", result)
        self.assertNotIn("events", result)

    # T05 — timeout sets collection_status=timeout; DebugActiveProcessStop called
    def test_T05_timeout_sets_status_and_detaches(self):
        # Empty sequence means WaitForDebugEvent returns 0 immediately.
        result, k32 = _run_trace([])
        self.assertEqual(result["collection_status"], "timeout")
        k32.DebugActiveProcessStop.assert_called()

    # T06 — event cap sets collection_status=event_cap; DebugActiveProcessStop called
    def test_T06_event_cap_detaches(self):
        # Feed 5 LOAD_DLL events into a cap of 3.
        seq = [{"code": LOAD_DLL_DEBUG_EVENT} for _ in range(5)]
        result, k32 = _run_trace(seq, max_events=3)
        self.assertEqual(result["collection_status"], "event_cap")
        k32.DebugActiveProcessStop.assert_called()

    # T07 — CREATE_PROCESS image file handle closed after path resolution
    def test_T07_create_process_image_handle_closed(self):
        h_image = 99
        seq = [
            {"code": CREATE_PROCESS_DEBUG_EVENT, "hFile": h_image},
            {"code": EXIT_PROCESS_DEBUG_EVENT, "exit_code": 0},
        ]
        _, k32 = _run_trace(seq)
        closed_handles = [c.args[0] for c in k32.CloseHandle.call_args_list]
        self.assertIn(h_image, closed_handles,
                      "Image file handle from CREATE_PROCESS must be closed")

    # T08 — LOAD_DLL file handle closed after path resolution
    def test_T08_load_dll_handle_closed(self):
        h_dll = 77
        seq = [
            {"code": CREATE_PROCESS_DEBUG_EVENT},
            {"code": LOAD_DLL_DEBUG_EVENT, "hFile": h_dll},
            {"code": EXIT_PROCESS_DEBUG_EVENT, "exit_code": 0},
        ]
        _, k32 = _run_trace(seq)
        closed_handles = [c.args[0] for c in k32.CloseHandle.call_args_list]
        self.assertIn(h_dll, closed_handles,
                      "DLL file handle from LOAD_DLL must be closed")

    # T09 — ContinueDebugEvent failure appends CONTINUE_DEBUG_EVENT_FAILED record
    def test_T09_continue_debug_event_failure_recorded(self):
        k32 = _make_fake_k32([
            {"code": CREATE_PROCESS_DEBUG_EVENT},
            {"code": EXIT_PROCESS_DEBUG_EVENT, "exit_code": 0},
        ])
        # Make ContinueDebugEvent fail on the EXIT_PROCESS call.
        call_count = [0]
        def _cont(pid, tid, status):
            call_count[0] += 1
            if call_count[0] >= 2:
                k32.GetLastError.return_value = 5  # ERROR_ACCESS_DENIED
                return 0
            return 1
        k32.ContinueDebugEvent.side_effect = _cont

        pi_obj = _pi_with()
        def _create(*args, **kwargs):
            p = args[9]
            p._obj.hProcess = pi_obj.hProcess
            p._obj.hThread = pi_obj.hThread
            p._obj.dwProcessId = pi_obj.dwProcessId
            p._obj.dwThreadId = pi_obj.dwThreadId
            return 1
        k32.CreateProcessW.side_effect = _create

        with (
            patch.object(_MOD, "_declare_win32_apis", return_value=k32),
            patch("os.name", "nt"),
        ):
            result = trace_native_launch("fake.exe")

        names = [e["event_name"] for e in result["events"]]
        self.assertIn("CONTINUE_DEBUG_EVENT_FAILED", names,
                      "ContinueDebugEvent failure must be recorded")

    # T10 — PROCESS_INFORMATION handles closed in finally even when loop raises
    def test_T10_pi_handles_closed_on_exception(self):
        h_proc, h_thr = 55, 66
        k32 = _make_fake_k32([])
        k32.WaitForDebugEvent.side_effect = RuntimeError("simulated loop error")

        pi_obj = _pi_with(h_process=h_proc, h_thread=h_thr)
        def _create(*args, **kwargs):
            p = args[9]
            p._obj.hProcess = pi_obj.hProcess
            p._obj.hThread = pi_obj.hThread
            p._obj.dwProcessId = pi_obj.dwProcessId
            p._obj.dwThreadId = pi_obj.dwThreadId
            return 1
        k32.CreateProcessW.side_effect = _create

        with (
            patch.object(_MOD, "_declare_win32_apis", return_value=k32),
            patch("os.name", "nt"),
        ):
            with self.assertRaises(RuntimeError):
                trace_native_launch("fake.exe")

        closed = [c.args[0] for c in k32.CloseHandle.call_args_list]
        self.assertIn(h_proc, closed, "hProcess must be closed in finally")
        self.assertIn(h_thr, closed, "hThread must be closed in finally")

    # T11 — schema and harness_version
    def test_T11_schema_and_version(self):
        seq = [
            {"code": CREATE_PROCESS_DEBUG_EVENT},
            {"code": EXIT_PROCESS_DEBUG_EVENT, "exit_code": 0},
        ]
        result, _ = _run_trace(seq)
        self.assertEqual(result["schema"], "openbot.windows-debug-trace/2")
        self.assertEqual(result["harness_version"], 2)

    # T12 — complete collection captures exit code
    def test_T12_complete_collection_exit_code(self):
        seq = [
            {"code": CREATE_PROCESS_DEBUG_EVENT},
            {"code": EXIT_PROCESS_DEBUG_EVENT, "exit_code": 0xC000007B},
        ]
        result, _ = _run_trace(seq)
        self.assertEqual(result["collection_status"], "complete")
        self.assertEqual(result["process_exit_code"], hex(0xC000007B))

    # T13 — loaded_modules lists only notified modules
    def test_T13_loaded_modules_list(self):
        seq = [
            {"code": CREATE_PROCESS_DEBUG_EVENT},
            {"code": LOAD_DLL_DEBUG_EVENT, "dll_base": 0xAAAA0000},
            {"code": EXIT_PROCESS_DEBUG_EVENT, "exit_code": 0},
        ]
        result, _ = _run_trace(seq)
        types_seen = [m["type"] for m in result["loaded_modules_before_termination"]]
        self.assertIn("main_executable", types_seen)
        self.assertIn("dll", types_seen)
        self.assertEqual(len(types_seen), 2)

    # T14 — non-Windows raises RuntimeError
    def test_T14_non_windows_raises(self):
        with patch("os.name", "posix"):
            with self.assertRaises(RuntimeError):
                trace_native_launch("fake.exe")

    # T15 — CLI exit code 2 when collection_status != "complete"
    def test_T15_cli_exit_code_on_timeout(self):
        result_stub = {
            "schema": "openbot.windows-debug-trace/2",
            "collection_status": "timeout",
        }
        with patch.object(_MOD, "trace_native_launch", return_value=result_stub):
            # Simulate main() with --output suppressed (print only)
            import io
            from contextlib import redirect_stdout
            with patch("sys.argv", ["windows-debug-trace.py", "fake.exe"]):
                with redirect_stdout(io.StringIO()):
                    exit_code = _MOD.main()
        self.assertEqual(exit_code, 2,
                         "CLI must exit 2 when collection is incomplete (timeout)")


if __name__ == "__main__":
    unittest.main()
