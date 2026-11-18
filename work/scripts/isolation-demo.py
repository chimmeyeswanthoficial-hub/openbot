#!/usr/bin/env python3
"""Actual fixed rootless namespace, denial and parent-crash experiment.

Only synthetic input/disposable state under .cache. No arbitrary program API,
model/provider/remote delivery/account/spend or claim of production isolation.
"""
from __future__ import annotations

import ctypes
import json
import os
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import closing, suppress
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / 'services/gateway/src'), str(ROOT / 'services/sentinel')]
from isolation import load_binary, run_fixed  # noqa: E402
from local_executor import Authority  # noqa: E402
from namespace_executor import NamespaceExecutor  # noqa: E402


def _pid_identity(pid):
    try:
        # starttime prevents a recycled PID being mistaken for our fixed probe.
        text = Path(f'/proc/{pid}/stat').read_text().rpartition(')')[2].split()
        return text[19], text[0]
    except (FileNotFoundError, ProcessLookupError):
        return None


def _descendants(pid):
    seen, todo = {}, [pid]
    for _ in range(4):
        more = []
        for p in todo:
            identity = _pid_identity(p)
            if identity:
                seen[p] = identity[0]
                with suppress(FileNotFoundError, ProcessLookupError):
                    more.extend(int(x) for x in Path(f'/proc/{p}/task/{p}/children').read_text().split())
        todo = more
    return seen


def parent_death_probe(base: Path):
    """Kill an actual disposable supervising Python parent; inspect/reap its tree."""
    libc = ctypes.CDLL(None, use_errno=True)
    prior = ctypes.c_int()
    if libc.prctl(37, ctypes.byref(prior), 0, 0, 0) != 0 or libc.prctl(36, 1, 0, 0, 0) != 0:
        raise RuntimeError('cannot independently observe/reap the fixed crash probe')
    state = base / 'parent-death'
    body = {'request_id': str(uuid.uuid4()), 'tool': 'local.wordcount',
            'arguments': {'text': 'synthetic fixed parent death proof', 'output': 'result.json', 'delay_ms': 3000}}
    program = (
        'import sys,json;from pathlib import Path;'
        f'sys.path[:0]={sys.path[:2]!r};'
        'from local_executor import Authority;from namespace_executor import NamespaceExecutor;'
        "e=NamespaceExecutor(Path(sys.argv[1]),Authority('agent:probe','probe','person','synthetic-parent-death'),"
        'capacity=1,timeout_s=4,experimental=True);e.execute(json.loads(sys.argv[2]))'
    )
    parent = subprocess.Popen([sys.executable, '-I', '-S', '-c', program, str(state), json.dumps(body)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                              env={'PATH': '/usr/local/bin:/usr/bin:/bin', 'LANG': 'C.UTF-8'},
                              start_new_session=True)
    identities, reaped, child_pid = {}, {}, None
    try:
        deadline = time.monotonic() + 3
        ready = False
        while time.monotonic() < deadline and parent.poll() is None:
            try:
                with closing(sqlite3.connect(f"file:{state / 'execution.sqlite3'}?mode=ro", uri=True)) as db:
                    row = db.execute('SELECT pid FROM local_jobs WHERE request_id=?', (body['request_id'],)).fetchone()
                if row and row[0]:
                    child_pid = row[0]
                    identities = _descendants(child_pid)
                    for pid in identities:
                        status = Path(f'/proc/{pid}/status').read_text()
                        if ('Name:\tpython3' in status and 'NoNewPrivs:\t1' in status
                                and 'Seccomp:\t2' in status):
                            ready = True
                            break
                    if ready:
                        break
            except (sqlite3.OperationalError, FileNotFoundError, ProcessLookupError):
                pass
            time.sleep(0.01)
        if not ready or len(identities) < 2:
            raise RuntimeError('parent-crash probe did not observe an actual isolated Python worker')
        parent.kill()
        parent.wait(timeout=2)
        started = time.monotonic()
        while time.monotonic() - started < 1.5:
            pending = []
            for pid, birth in identities.items():
                try:
                    got, status = os.waitpid(pid, os.WNOHANG)
                    if got:
                        reaped[pid] = os.waitstatus_to_exitcode(status)
                except ChildProcessError:
                    pass  # Namespace init may have reaped it; check actual PID identity.
                identity = _pid_identity(pid)
                if identity and identity[0] == birth:
                    pending.append(pid)
            if not pending:
                break
            time.sleep(0.01)
        else:
            raise RuntimeError('fixed namespace tree survived supervisor death')
        restart = NamespaceExecutor(state, Authority('agent:probe', 'probe', 'person', 'synthetic-parent-death'),
                                    experimental=True, capacity=1, timeout_s=4)
        try:
            replay = restart.execute(body)
            assert not replay['executed'] and replay['code'] == 'reconciliation_required'
            assert restart.quota()['used_units'] == 1 and restart.outbox_count(body['request_id']) == 0
        finally:
            restart.close()
        return {'actual_supervisor_killed': True, 'supervisor_returncode': parent.returncode,
                'launcher_pid': child_pid, 'observed_tree_pids': sorted(identities),
                'all_observed_tree_pids_gone': True, 'adopted_exit_codes': reaped,
                'stop_observation_seconds': round(time.monotonic() - started, 4),
                'interrupted_request_not_reexecuted': True, 'reserved_attempt_not_refunded': True}
    finally:
        if parent.poll() is None:
            parent.kill()
        parent.wait(timeout=2)
        parent.stderr.close()
        # Best effort cleanup of only this disposable tree, with PID-reuse guards.
        for pid, birth in identities.items():
            identity = _pid_identity(pid)
            if identity and identity[0] == birth:
                try:
                    os.kill(pid, signal.SIGKILL)
                    os.waitpid(pid, 0)
                except (ProcessLookupError, ChildProcessError):
                    pass
        libc.prctl(36, prior.value, 0, 0, 0)


def main():
    load_binary()
    (ROOT / '.cache').mkdir(exist_ok=True)
    base = Path(tempfile.mkdtemp(prefix='isolation-demo-', dir=ROOT / '.cache'))
    canary = base / 'synthetic-host-canary'
    original = b'synthetic disposable host canary, never real credentials'
    canary.write_bytes(original)
    probe = run_fixed('probe', {'host_canary': str(canary)}, timeout_s=3)
    assert probe.returncode == 0 and not probe.terminal
    denials = json.loads(probe.stdout)
    assert all(denials[k] for k in ('host_read_blocked', 'host_write_blocked', 'root_write_blocked',
               'tmp_write_blocked', 'ipv4_socket_blocked', 'ipv6_socket_blocked', 'unix_socket_blocked',
               'raw_syscall_socket_blocked', 'raw_syscall_io_uring_blocked', 'pid1_root_canary_blocked',
               'fork_blocked', 'nested_userns_blocked', 'host_environment_absent'))
    assert canary.read_bytes() == original
    authority = Authority('agent:probe', 'probe', 'person', 'synthetic-isolation-demo')
    executor = NamespaceExecutor(base / 'execution', authority, experimental=True)
    body = {'request_id': str(uuid.uuid4()), 'tool': 'local.wordcount',
            'arguments': {'text': 'reviewed fixed namespace evidence', 'output': 'result.json', 'delay_ms': 0}}
    try:
        first = executor.execute(body)
        assert first['ok'] and first['executed'] and first['result']['words'] == 4
        executor.close()
        executor = NamespaceExecutor(base / 'execution', authority, experimental=True)
        replay = executor.execute(body)
        assert replay['ok'] and replay['replayed'] and not replay['executed']
        assert executor.quota()['used_units'] == 1 and executor.outbox_count(body['request_id']) == 1
        crash = parent_death_probe(base)
        print(json.dumps({'observed_runner_utc': datetime.now(UTC).isoformat(), 'passed': True,
                          'profile': 'rootless-fixed-v1', 'negative_probe': denials,
                          'host_canary_unchanged': True, 'actual_wordcount': first['result'],
                          'seven_correlated_events': [e['type'] for e in first['events']],
                          'restart_replay_without_execution_or_redelivery': True, 'parent_death': crash,
                          'cgroup_enforced': False, 'authenticated_mandatory_runtime_hook': False,
                          'providers_enabled': False, 'external_delivery_attempted': False,
                          'production_ready': False, 'generated_disposable_state': str(base.relative_to(ROOT)),
                          'limits': ['Reviewed fixed worker only; not arbitrary customer programs',
                                     'Read-only /usr and libraries are trusted host runtime, not hermetic images',
                                     'Rlimits/seccomp/namespaces do not replace delegated cgroups or independent security review',
                                     'Authority/Owner remain trusted-host APIs, not remote identity authentication']}, indent=2))
    finally:
        executor.close()


if __name__ == '__main__':
    main()
