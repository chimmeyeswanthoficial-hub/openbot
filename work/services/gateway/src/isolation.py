"""Fixed rootless Linux experiment, not a general sandbox or authenticated runtime.

Pinned Bubblewrap, mandatory namespaces, no host RW mounts, sealed seccomp and
bounded stdio/deadline. Missing controls fail; there is NEVER a host fallback.
Only reviewed wordcount/probe code may run. Host setup and source remain trusted.
"""
from __future__ import annotations

import json
import math
import os
import selectors
import signal
import struct
import subprocess
import time
import uuid
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from isolation_runtime import checked_binary, load_lock

# Optional only for collection; the fixed runtime must refuse without sealing.
try:
    import fcntl
except ImportError:
    fcntl = None

ROOT = Path(__file__).resolve().parents[3]


def load_binary(root: Path = ROOT) -> Path:
    if fcntl is None:
        raise ValueError('mandatory Linux fcntl sealing unavailable; never fall back')
    return checked_binary(root, load_lock(root))


def seccomp_program() -> bytes:
    # x86_64 only. Reject other architectures/x32; deny network, process creation,
    # namespace/mount, tracing, kernel key/BPF/perf and sensitive kernel interfaces.
    rows = [(0x20, 0, 0, 4), (0x15, 1, 0, 0xC000003E), (0x06, 0, 0, 0x80000000),
            (0x20, 0, 0, 0), (0x35, 0, 1, 0x40000000), (0x06, 0, 0, 0x80000000)]
    denied = {41, 42, 43, 49, 50, 53, 56, 57, 58, 101, 155, 161, 165, 166,
              169, 175, 176, 246, 248, 249, 250, 272, 288, 298, 303, 304,
              308, 310, 311, 312, 313, 317, 321, 323, 425, 426, 427, 434, 435, 438}
    for number in sorted(denied):
        rows += [(0x15, 0, 1, number), (0x06, 0, 0, 0x00050001)]  # EPERM
    rows += [(0x06, 0, 0, 0x7FFF0000)]
    return b''.join(struct.pack('HBBI', *row) for row in rows)


@dataclass(frozen=True)
class LaunchResult:
    stdout: bytes
    returncode: int
    pid: int
    terminal: str | None = None
    stderr: bytes = b''


class IsolationFailure(RuntimeError):
    def __init__(self, pid):
        super().__init__('isolated process produced no trusted completion')
        self.pid = pid


def _terminate(process):
    if process.poll() is None:
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
    process.wait(timeout=2)


def run_fixed(mode, body, *, timeout_s=2, cancelled: Callable[[], bool] = lambda: False,
              on_start: Callable[[int], None] = lambda _pid: None) -> LaunchResult:
    if not isinstance(mode, str) or mode not in {'wordcount', 'probe', 'qa'}:
        raise ValueError('only reviewed fixed wordcount/probe modes exist')
    if (type(timeout_s) not in (int, float) or not math.isfinite(timeout_s)
            or not 0.05 <= timeout_s <= 5):
        raise ValueError('invalid fixed host deadline')
    if not isinstance(body, dict):
        raise ValueError('fixed JSON body required')
    if mode == 'wordcount':
        if (set(body) != {'request_id', 'text', 'delay_ms'}
                or not isinstance(body['request_id'], str)
                or str(uuid.UUID(body['request_id'])) != body['request_id']
                or not isinstance(body['text'], str) or len(body['text'].encode()) > 8192
                or type(body['delay_ms']) is not int or not 0 <= body['delay_ms'] <= 3000):
            raise ValueError('invalid fixed wordcount arguments')
    elif mode == 'qa':
        from qa_catalog import FIXTURES
        if set(body) != {'fixture'} or not isinstance(body['fixture'],str) or body['fixture'] not in FIXTURES:
            raise ValueError('only bundled owned QA fixtures')
    elif (set(body) != {'host_canary'} or not isinstance(body['host_canary'], str)
          or not body['host_canary'].startswith('/') or len(body['host_canary']) > 4096
          or '\0' in body['host_canary']):
        raise ValueError('probe needs an operator-owned synthetic absolute canary path')
    payload = json.dumps(body, separators=(',', ':'), allow_nan=False).encode()
    if len(payload) > 65536:
        raise ValueError('input limit')
    binary = load_binary()
    worker = Path(__file__).with_name('qa_fixture_worker.py' if mode=='qa' else 'namespace_worker.py')
    catalog = Path(__file__).with_name('qa_catalog.py')
    if mode=='qa' and any(p.is_symlink() for p in (catalog,*catalog.parents)):
        raise ValueError('symlinked reviewed catalog')
    extra_mounts = ['--ro-bind',str(catalog),'/fixtures.py'] if mode=='qa' else []
    if any(p.is_symlink() for p in (worker, *worker.parents)):
        raise ValueError('symlinked reviewed worker')
    fd = os.memfd_create('openbot-fixed-seccomp', os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    process = None
    try:
        os.write(fd, seccomp_program())
        os.lseek(fd, 0, os.SEEK_SET)
        fcntl.fcntl(fd, fcntl.F_ADD_SEALS, fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW |
                    fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL)
        command = [str(binary), '--unshare-all', '--unshare-user', '--disable-userns', '--assert-userns-disabled',
                   '--new-session', '--die-with-parent', '--cap-drop', 'ALL',
                   '--hostname', 'openbot-fixed', '--clearenv', '--setenv', 'PATH', '/usr/bin:/bin',
                   '--setenv', 'LANG', 'C.UTF-8', '--setenv', 'PYTHONNOUSERSITE', '1',
                   '--setenv', 'PYTHONDONTWRITEBYTECODE', '1',
                   '--ro-bind', '/usr', '/usr', '--ro-bind', '/lib', '/lib',
                   '--ro-bind', '/lib64', '/lib64', '--proc', '/proc', '--dev', '/dev',
                   '--size', '8388608', '--tmpfs', '/tmp', '--ro-bind', str(worker), '/worker.py', *extra_mounts,
                   '--remount-ro', '/proc', '--remount-ro', '/dev', '--remount-ro', '/tmp',
                   '--remount-ro', '/', '--chdir', '/tmp', '--seccomp', str(fd),
                   '/usr/bin/python3', '-I', '-S', '/worker.py', mode]
        deadline = time.monotonic() + timeout_s
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, close_fds=True, pass_fds=(fd,),
                                   start_new_session=True, cwd='/',
                                   env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
        on_start(process.pid)
        output, errors, pending = bytearray(), bytearray(), memoryview(payload)
        with selectors.DefaultSelector() as selector:
            for stream, kind in ((process.stdin, 'in'), (process.stdout, 'out'), (process.stderr, 'err')):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_WRITE if kind == 'in' else selectors.EVENT_READ, kind)
            while selector.get_map():
                stop = 'cancelled' if cancelled() else 'timed_out' if time.monotonic() >= deadline else None
                if stop:
                    _terminate(process)
                    return LaunchResult(bytes(output), process.returncode, process.pid, stop, bytes(errors))
                for key, _ in selector.select(0.02):
                    stream = key.fileobj
                    if key.data == 'in':
                        try:
                            sent = os.write(stream.fileno(), pending)
                            pending = pending[sent:]
                        except BrokenPipeError:
                            pending = pending[:0]
                        if not pending:
                            selector.unregister(stream)
                            stream.close()
                    else:
                        chunk = os.read(stream.fileno(), 4096)
                        if not chunk:
                            selector.unregister(stream)
                            continue
                        target = output if key.data == 'out' else errors
                        target.extend(chunk)
                        if len(target) > (65536 if key.data == 'out' else 8192):
                            raise ValueError('isolated output bound')
        process.wait(timeout=max(0.01, deadline - time.monotonic()))
        return LaunchResult(bytes(output), process.returncode, process.pid, stderr=bytes(errors))
    except Exception as exc:
        if process is not None:
            raise IsolationFailure(process.pid) from exc
        raise
    finally:
        os.close(fd)
        if process is not None:
            _terminate(process)
            for stream in (process.stdin, process.stdout, process.stderr):
                if not stream.closed:
                    stream.close()
