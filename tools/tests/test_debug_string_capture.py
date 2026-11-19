"""Schema-4 opt-in payload contracts: fake Win32 only, NOT a native Windows test."""

import base64
import ctypes
import io
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

from test_windows_debug_trace import _MOD, _make_fake_k32


def info(length, *, wide=False, address=0x1000):
    value = _MOD.OUTPUT_DEBUG_STRING_INFO()
    value.lpDebugStringData = address
    value.fUnicode = int(wide)
    value.nDebugStringLength = length
    return value


def memory_reader(data, *, ok=True, count=None):
    k32 = MagicMock()
    k32.GetLastError.return_value = 299

    def read(process, address, buffer, size, out_count):
        n = min(len(data), size)
        if n:
            ctypes.memmove(buffer, data, n)
        out_count._obj.value = n if count is None else count
        return int(ok)

    k32.ReadProcessMemory.side_effect = read
    return k32


def trace(sequence, *, capture=True, reader=None):
    k32 = _make_fake_k32(sequence)
    # Separate mocks make selecting the Unicode-opt-in wait function observable.
    k32.WaitForDebugEventEx = MagicMock(side_effect=k32.WaitForDebugEvent.side_effect)
    if reader is not None:
        k32.ReadProcessMemory.side_effect = reader.ReadProcessMemory.side_effect

    def create(*args):
        pi = args[9]._obj
        pi.hProcess, pi.hThread = 11, 12
        pi.dwProcessId, pi.dwThreadId = 1234, 5678
        return 1

    k32.CreateProcessW.side_effect = create
    with (
        patch.object(_MOD, "_declare_win32_apis", return_value=k32),
        patch.object(_MOD, "os", types.SimpleNamespace(name="nt", environ={})),
    ):
        result = _MOD.trace_native_launch("fake.exe", capture_debug_strings=capture)
    return result, k32


class DebugStringTests(unittest.TestCase):
    def test_ansi_bytes_are_preserved_without_claiming_ansi_codepage(self):
        data = b"hello \xe9\x00"
        k32 = memory_reader(data)
        result = _MOD._capture_debug_string(k32, 11, info(len(data)), 100)
        self.assertEqual(result["text"], "hello \u00e9")
        self.assertEqual(result["encoding"], "latin-1-byte-view")
        self.assertEqual(base64.b64decode(result["raw_base64"]), data)
        self.assertEqual(result["status"], "complete")
        self.assertTrue(result["reported_length_is_lower_16_bits"])

    def test_unicode_length_is_bytes_not_characters_and_no_overread(self):
        data = "OpenBot \u0c05\U0001f642\x00".encode("utf-16-le")
        k32 = memory_reader(data)
        result = _MOD._capture_debug_string(k32, 11, info(len(data), wide=True), 100)
        self.assertEqual(result["text"], "OpenBot \u0c05\U0001f642")
        self.assertEqual(k32.ReadProcessMemory.call_args.args[3], len(data))
        self.assertEqual(result["bytes_read"], len(data))
        self.assertEqual(result["status"], "complete")

    def test_zero_reported_length_does_not_scan_or_claim_original_length(self):
        k32 = memory_reader(b"not read")
        result = _MOD._capture_debug_string(k32, 11, info(65536), 100)
        self.assertEqual(result["declared_bytes"], 0)
        self.assertTrue(result["reported_length_is_lower_16_bits"])
        k32.ReadProcessMemory.assert_not_called()

    def test_null_pointer_or_missing_process_handle_never_read(self):
        for handle, address in [(11, 0), (0, 0x1000)]:
            with self.subTest(handle=handle, address=address):
                k32 = memory_reader(b"test")
                result = _MOD._capture_debug_string(k32, handle, info(4, address=address), 100)
                self.assertEqual(result["status"], "invalid_pointer_or_handle")
                k32.ReadProcessMemory.assert_not_called()

    def test_per_event_cap_is_enforced(self):
        k32 = memory_reader(b"a" * 40000)
        result = _MOD._capture_debug_string(k32, 11, info(40000), 50000)
        self.assertEqual(k32.ReadProcessMemory.call_args.args[3], 16384)
        self.assertEqual(result["bytes_read"], 16384)
        self.assertEqual(result["status"], "truncated")

    def test_remaining_session_budget_is_enforced(self):
        k32 = memory_reader(b"abcdef")
        result = _MOD._capture_debug_string(k32, 11, info(6), 3)
        self.assertEqual(k32.ReadProcessMemory.call_args.args[3], 3)
        self.assertEqual(result["text"], "abc")
        self.assertEqual(result["status"], "truncated")

    def test_exhausted_budget_does_not_read(self):
        k32 = memory_reader(b"abcdef")
        result = _MOD._capture_debug_string(k32, 11, info(6), 0)
        self.assertEqual(result["status"], "budget_exhausted")
        k32.ReadProcessMemory.assert_not_called()

    def test_read_failure_preserves_partial_bytes_and_error(self):
        k32 = memory_reader(b"ab", ok=False)
        result = _MOD._capture_debug_string(k32, 11, info(10), 100)
        self.assertEqual(result["status"], "read_failed")
        self.assertEqual(result["win32_last_error"], 299)
        self.assertEqual(result["bytes_read"], 2)
        self.assertEqual(result["text"], "ab")

    def test_success_with_short_read_is_explicitly_incomplete(self):
        result = _MOD._capture_debug_string(memory_reader(b"ab"), 11, info(10), 100)
        self.assertEqual(result["status"], "partial_read")

    def test_impossible_read_count_is_rejected_without_publishing_buffer(self):
        result = _MOD._capture_debug_string(memory_reader(b"ab", count=999), 11, info(2), 100)
        self.assertEqual(result["status"], "invalid_read_count")
        self.assertEqual(result["raw_base64"], "")
        self.assertEqual(result["bytes_read"], 0)

    def test_reader_exception_is_reported_without_exception_message_leak(self):
        k32 = memory_reader(b"")
        k32.ReadProcessMemory.side_effect = OSError("synthetic private information")
        result = _MOD._capture_debug_string(k32, 11, info(4), 100)
        self.assertEqual(result["status"], "reader_exception")
        self.assertEqual(result["error_type"], "OSError")
        self.assertNotIn("synthetic private", str(result))

    def test_odd_unicode_byte_count_is_preserved_and_decode_failure_explicit(self):
        result = _MOD._capture_debug_string(memory_reader(b"A\x00B"), 11, info(3, wide=True), 100)
        self.assertEqual(result["status"], "invalid_encoding")
        self.assertTrue(result["text_decode_had_errors"])
        self.assertEqual(base64.b64decode(result["raw_base64"]), b"A\x00B")

    def test_invalid_surrogate_is_preserved_and_decode_failure_explicit(self):
        data = b"\x00\xd8\x00\x00"
        result = _MOD._capture_debug_string(memory_reader(data), 11, info(4, wide=True), 100)
        self.assertEqual(result["status"], "invalid_encoding")
        self.assertEqual(base64.b64decode(result["raw_base64"]), data)

    def test_default_path_uses_original_wait_and_never_reads_memory(self):
        result, k32 = trace([{"code": 3}, {"code": 8}, {"code": 5}], capture=False)
        k32.ReadProcessMemory.assert_not_called()
        k32.WaitForDebugEventEx.assert_not_called()
        self.assertEqual(k32.WaitForDebugEvent.call_count, 3)
        self.assertEqual(result["events"][1]["debug_string"]["status"], "not_requested")
        self.assertEqual(result["debug_string_capture_status"], "not_requested")
        self.assertEqual(result["collection_status"], "complete")

    def test_opt_in_selects_unicode_wait_and_records_exact_text(self):
        data = "Hello\x00".encode("utf-16-le")
        result, k32 = trace(
            [{"code": 3}, {"code": 8, "wide": True, "length": len(data)}, {"code": 5}],
            reader=memory_reader(data),
        )
        self.assertEqual(k32.WaitForDebugEventEx.call_count, 3)
        k32.WaitForDebugEvent.assert_not_called()
        self.assertEqual(result["events"][1]["debug_string"]["text"], "Hello")
        self.assertEqual(result["debug_string_capture_status"], "complete")
        self.assertEqual(result["debug_string_bytes_captured"], len(data))
        self.assertEqual(result["collection_status"], "complete")
        self.assertIsNone(result["entry_point_reached"])
        k32.DebugActiveProcessStop.assert_not_called()

    def test_failed_payload_read_still_continues_event_and_cleans_up(self):
        result, k32 = trace([{"code": 3}, {"code": 8}, {"code": 5}])
        self.assertEqual(result["event_collection_status"], "complete")
        self.assertEqual(result["collection_status"], "diagnostic_incomplete")
        self.assertEqual(result["debug_string_capture_status"], "incomplete")
        self.assertEqual(result["cleanup_status"], "ok")
        self.assertEqual(k32.ContinueDebugEvent.call_count, 3)
        self.assertEqual(k32.CloseHandle.call_count, 2)
        k32.DebugActiveProcessStop.assert_not_called()

    def test_total_session_capture_never_exceeds_256_kib(self):
        result, k32 = trace(
            [{"code": 3}] + [{"code": 8, "length": 65535}] * 20 + [{"code": 5}],
            reader=memory_reader(b"a" * 65535),
        )
        self.assertEqual(result["debug_string_bytes_captured"], 262144)
        self.assertEqual(k32.ReadProcessMemory.call_count, 16)
        self.assertEqual(result["collection_status"], "diagnostic_incomplete")
        self.assertEqual(result["events"][-2]["debug_string"]["status"], "budget_exhausted")

    def test_non_boolean_opt_in_refused_before_api_binding(self):
        with (
            patch.object(_MOD, "os", types.SimpleNamespace(name="nt")),
            patch.object(_MOD, "_declare_win32_apis") as api,
            self.assertRaises(ValueError),
        ):
            _MOD.trace_native_launch("fake.exe", capture_debug_strings=1)
        api.assert_not_called()

    def test_cli_payload_capture_requires_new_private_output_not_stdout(self):
        with (
            patch.object(sys, "argv", ["trace", "fake.exe", "--debug-strings"]),
            patch.object(_MOD, "trace_native_launch") as launch,
            redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as error,
        ):
            _MOD.main()
        self.assertEqual(error.exception.code, 2)
        launch.assert_not_called()

    def test_cli_passes_explicit_opt_in_and_reports_incomplete_with_exit_2(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "new-private-trace.json"
            stub = {"collection_status": "diagnostic_incomplete", "cleanup_status": "ok"}
            with (
                patch.object(
                    sys, "argv", ["trace", "fake.exe", "--debug-strings", "--output", str(output)]
                ),
                patch.object(_MOD, "trace_native_launch", return_value=stub) as launch,
                redirect_stdout(io.StringIO()),
            ):
                result = _MOD.main()
            self.assertEqual(result, 2)
            self.assertTrue(launch.call_args.kwargs["capture_debug_strings"])
            self.assertTrue(output.is_file())


if __name__ == "__main__":
    unittest.main()
