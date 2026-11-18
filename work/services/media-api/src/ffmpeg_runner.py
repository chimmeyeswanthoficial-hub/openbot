"""Bounded local-owned-media process plumbing. No shell; no public arbitrary argv.

Selectors drain stdout/stderr while feeding stdin. A watchdog also kills/reaps a
process when a generator is suspended by a slow consumer. This is local resource
containment only; rlimit NPROC is UID-wide, not an S09 per-job PID boundary.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import selectors
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Generator
from pathlib import Path


class MediaError(ValueError):
    def __init__(self, code, status=422):
        super().__init__(code)
        self.code, self.status = code, status


def _file_sha(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def tool_paths():
    """Require explicit reviewed file pins. Never silently fall back to PATH."""
    try:
        lock_path = Path(os.environ["MEDIA_TOOL_LOCK"])
        lock = json.loads(lock_path.read_text())
        if lock.get("schema") != "openbot.media-tools/1" or lock["library_path"] != os.environ.get(
            "MEDIA_LIBRARY_PATH"
        ):
            raise ValueError("schema_or_library_selection")
        result = {}
        for name in ("ffmpeg", "ffprobe"):
            record = lock["executables"][name]
            path = Path(record["path"])
            if not path.is_absolute() or not path.is_file() or path.is_symlink():
                raise ValueError("path")
            if _file_sha(path) != record["sha256"]:
                raise ValueError("hash")
            result[name] = str(path)
        for record in lock["libraries"]:
            if _file_sha(record["path"]) != record["sha256"]:
                raise ValueError("library_hash")
        return result
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise MediaError("reviewed_media_tools_unavailable", 503) from exc


def is_ffmpeg_available():
    try:
        tool_paths()
        return True
    except MediaError:
        return False


def terminate_reap(proc):
    """Kill the private session, then wait. Repeated cleanup is harmless."""
    with contextlib.suppress(ProcessLookupError):
        os.killpg(proc.pid, signal.SIGTERM)
    try:
        proc.wait(timeout=0.3)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=2)
    # A parent may have exited first; remaining members still receive SIGKILL.
    with contextlib.suppress(ProcessLookupError):
        os.killpg(proc.pid, signal.SIGKILL)


def run_process(
    executable,
    args,
    *,
    input_stream=(),
    timeout=30.0,
    max_input=260 << 20,
    max_output=128 << 10,
    max_stderr=64 << 10,
    cancelled=None,
    cwd=None,
    disk_check=lambda: None,
    receipt=None,
):
    limits = {"memory": 1536 << 20, "cpu": 30, "file": 300 << 20, "pids": 128}
    environment = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(cwd or "/nonexistent"),
        "LANG": "C.UTF-8",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MEDIA_PARENT_PID": str(os.getpid()),
    }
    # Dynamic library selection is trusted host configuration, pinned by the tool lock.
    if "MEDIA_LIBRARY_PATH" in os.environ:
        environment["LD_LIBRARY_PATH"] = os.environ["MEDIA_LIBRARY_PATH"]
    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).with_name("media_worker.py")),
            json.dumps(limits),
            executable,
            *args,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
        cwd=cwd,
        env=environment,
        bufsize=0,
    )
    start = time.monotonic()
    done = threading.Event()
    timed_out = threading.Event()
    peak_rss_kb = 0
    observed_threads = 0
    kernel_limits = {}

    def watch():
        nonlocal peak_rss_kb, observed_threads
        while not done.wait(0.025):
            try:
                fields = Path(f"/proc/{proc.pid}/status").read_text().splitlines()
                for field in fields:
                    if field.startswith("VmRSS:"):
                        peak_rss_kb = max(peak_rss_kb, int(field.split()[1]))
                    if field.startswith("Threads:"):
                        observed_threads = max(observed_threads, int(field.split()[1]))
                if Path(f"/proc/{proc.pid}/comm").read_text().strip() in {"ffmpeg", "ffprobe"}:
                    kernel_limits["proc_limits"] = Path(f"/proc/{proc.pid}/limits").read_text()
                children = Path(f"/proc/{proc.pid}/task/{proc.pid}/children").read_text().split()
                # The fixed ffmpeg invocation must not spawn any child programs.
                if children:
                    timed_out.set()
            except (FileNotFoundError, ProcessLookupError):
                pass
            if time.monotonic() - start > timeout or (cancelled and cancelled()):
                timed_out.set()
            if timed_out.is_set():
                terminate_reap(proc)
                return

    watcher = threading.Thread(target=watch, name="owned-media-watchdog", daemon=True)
    watcher.start()
    selector = selectors.DefaultSelector()
    source = iter([input_stream]) if isinstance(input_stream, bytes) else iter(input_stream)
    pending = memoryview(b"")
    input_done = False
    input_bytes = output_bytes = stderr_bytes = 0
    try:
        for stream, role, event in [
            (proc.stdin, "in", selectors.EVENT_WRITE),
            (proc.stdout, "out", selectors.EVENT_READ),
            (proc.stderr, "err", selectors.EVENT_READ),
        ]:
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, event, role)
        while selector.get_map():
            if timed_out.is_set():
                raise MediaError("cancelled_or_deadline", 408)
            disk_check()
            for key, _mask in selector.select(0.025):
                stream, role = key.fileobj, key.data
                if role == "in":
                    if not pending and not input_done:
                        try:
                            block = next(source)
                            if not isinstance(block, bytes):
                                raise MediaError("invalid_input_chunk")
                            input_bytes += len(block)
                            if input_bytes > max_input:
                                raise MediaError("input_too_large", 413)
                            pending = memoryview(block)
                        except StopIteration:
                            input_done = True
                    if not pending and input_done:
                        selector.unregister(stream)
                        stream.close()
                        continue
                    if pending:
                        try:
                            written = os.write(stream.fileno(), pending[:65536])
                            pending = pending[written:]
                        except (BrokenPipeError, OSError):
                            selector.unregister(stream)
                            stream.close()
                else:
                    try:
                        block = os.read(stream.fileno(), 65536)
                    except BlockingIOError:
                        continue
                    if not block:
                        selector.unregister(stream)
                        stream.close()
                        continue
                    if role == "err":
                        stderr_bytes += len(block)
                        if stderr_bytes > max_stderr:
                            raise MediaError("stderr_limit")
                    else:
                        output_bytes += len(block)
                        if output_bytes > max_output:
                            raise MediaError("output_limit", 413)
                        yield block
        remaining = max(0.01, timeout - (time.monotonic() - start))
        try:
            code = proc.wait(timeout=remaining)
        except subprocess.TimeoutExpired as exc:
            raise MediaError("deadline", 408) from exc
        if timed_out.is_set():
            raise MediaError("cancelled_or_deadline", 408)
        if code:
            raise MediaError("invalid_media_or_resource_limit")
    finally:
        done.set()
        terminate_reap(proc)
        watcher.join(timeout=3)
        selector.close()
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            if not stream.closed:
                stream.close()
        close = getattr(source, "close", None)
        if close:
            close()
        if receipt is not None:
            receipt.update(
                pid=proc.pid,
                reaped=proc.poll() is not None,
                elapsed_seconds=round(time.monotonic() - start, 6),
                peak_sampled_rss_kb=peak_rss_kb,
                peak_sampled_threads=observed_threads,
                input_bytes=input_bytes,
                output_bytes=output_bytes,
                stderr_bytes=stderr_bytes,
                rlimits=limits,
                per_job_cgroup=False,
                kernel_limits=kernel_limits,
            )


def run_ffmpeg_stream(
    args: list[str], input_stream: Generator[bytes, None, None] | bytes, *, chunk_size=65536
):
    """Compatibility for trusted internal callers; not mounted as arbitrary argv.

    Uses selectors.DefaultSelector through run_process, never sequential whole
    stdin writes. The public service instead spools bounded input and verifies
    the complete output before returning any successful response.
    """
    if not 1 <= chunk_size <= 65536:
        raise MediaError("invalid_chunk_size")
    yield from run_process(
        tool_paths()["ffmpeg"],
        ["-hide_banner", "-loglevel", "error", "-nostdin", "-threads", "1", *args],
        input_stream=input_stream,
        max_output=64 << 20,
    )
