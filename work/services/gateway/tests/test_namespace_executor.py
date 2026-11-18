"""Fixed namespace experiment: no live models, credentials or arbitrary program API."""
from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import isolation
import pytest
from local_executor import Authority, LocalExecutor, Owner
from namespace_executor import NamespaceExecutor

REAL = pytest.mark.skipif(os.environ.get('OPENBOT_TEST_NAMESPACE') != '1',
                          reason='explicit fixed-namespace test opt-in and pinned tool required')


def request(text='one two three', *, tool='local.wordcount', delay=0):
    return {'request_id': str(uuid.uuid4()), 'tool': tool,
            'arguments': {'text': text, 'output': 'result.json', 'delay_ms': delay}}


def authority(venture='isolation-fixture'):
    return Authority('agent:fixture', venture, 'person', 'synthetic-human-fixture')


def test_experiment_is_explicit_and_disabled_by_default(tmp_path):
    with pytest.raises(ValueError, match='experimental'):
        NamespaceExecutor(tmp_path / 'state', authority())
    assert not (tmp_path / 'state').exists()


@pytest.mark.parametrize('mode', ['shell', 'python', '', None, [], 'wordcount --share-net'])
def test_fixed_launcher_has_no_arbitrary_program_or_option_surface(mode):
    with pytest.raises(ValueError):
        isolation.run_fixed(mode, {}, timeout_s=1)


@pytest.mark.parametrize('timeout', [True, 0, -1, float('nan'), float('inf'), 30])
def test_native_launcher_validates_host_deadlines(timeout):
    with pytest.raises(ValueError):
        isolation.run_fixed('probe', {}, timeout_s=timeout)


def test_source_pin_rejects_missing_binary_without_fallback(tmp_path):
    lock = Path(isolation.ROOT / 'audit/isolation-runtime-lock.json').read_text()
    (tmp_path / 'audit').mkdir()
    (tmp_path / 'audit/isolation-runtime-lock.json').write_text(lock)
    with pytest.raises((ValueError, OSError)):
        isolation.load_binary(tmp_path)


def test_seccomp_is_bounded_binary_and_includes_architecture_guard():
    program = isolation.seccomp_program()
    assert isinstance(program, bytes) and 64 < len(program) < 4096 and len(program) % 8 == 0
    assert b'\x3e\x00\x00\xc0' in program  # AUDIT_ARCH_X86_64


@REAL
def test_actual_namespace_negative_probes_and_host_canary_unchanged(tmp_path, monkeypatch):
    canary = tmp_path / 'host-private.txt'
    canary.write_bytes(b'synthetic-host-canary-not-a-real-secret')
    monkeypatch.setenv('OPENBOT_SYNTHETIC_SECRET', 'synthetic-never-pass-to-child')
    result = isolation.run_fixed('probe', {'host_canary': str(canary)}, timeout_s=3)
    assert result.returncode == 0 and not result.terminal
    evidence = json.loads(result.stdout)
    assert evidence['host_read_blocked'] and evidence['host_write_blocked']
    assert evidence['root_write_blocked'] and evidence['tmp_write_blocked']
    assert evidence['ipv4_socket_blocked'] and evidence['ipv6_socket_blocked']
    assert evidence['unix_socket_blocked'] and evidence['raw_syscall_socket_blocked']
    assert evidence['fork_blocked'] and evidence['nested_userns_blocked']
    assert evidence['raw_syscall_io_uring_blocked'] and evidence['pid1_root_canary_blocked']
    assert evidence['rlimits'] == {'CPU': [2, 2], 'AS': [134217728, 134217728],
                                  'FSIZE': [0, 0], 'NOFILE': [16, 16], 'CORE': [0, 0], 'NPROC': [1, 1]}
    assert evidence['status']['NoNewPrivs'] == '1'
    assert evidence['status']['Seccomp'] == '2'
    assert int(evidence['status']['CapEff'], 16) == 0
    assert evidence['host_environment_absent'] and evidence['pid_count'] <= 2
    for kind in ('net', 'mnt', 'pid', 'user', 'uts', 'ipc'):
        assert evidence['namespaces'][kind] != os.readlink(f'/proc/self/ns/{kind}')
    assert canary.read_bytes() == b'synthetic-host-canary-not-a-real-secret'


@REAL
def test_actual_audited_isolated_wordcount_and_restart_replay(tmp_path):
    body = request()
    executor = NamespaceExecutor(tmp_path, authority(), experimental=True)
    try:
        result = executor.execute(body)
        assert result['ok'] and result['executed'] and result['status'] == 'delivered'
        assert result['result']['words'] == 3 and result['result']['characters'] == 13
        assert result['result']['isolation']['profile'] == 'rootless-fixed-v1'
        assert result['result']['isolation']['cgroup_enforced'] is False
        assert executor.quota()['used_units'] == 1
        assert executor.outbox_count(body['request_id']) == 1
        assert any(r['action'] == 'local.execution.complete' for r in executor.audit.audit_tail(100))
    finally:
        executor.close()
    executor = NamespaceExecutor(tmp_path, authority(), experimental=True)
    try:
        replay = executor.execute(body)
        assert replay['ok'] and replay['replayed'] and not replay['executed']
        assert executor.quota()['used_units'] == 1 and executor.outbox_count(body['request_id']) == 1
    finally:
        executor.close()


@REAL
def test_namespace_review_binds_exact_input_and_real_host_owner(tmp_path):
    executor = NamespaceExecutor(tmp_path, authority(), experimental=True)
    try:
        body = request(tool='local.reviewed_wordcount')
        pending = executor.execute(body)
        assert pending['status'] == 'gated' and executor.quota()['used_units'] == 0
        assert not executor.resolve(body['request_id'], pending['request_digest'], 'approved', owner={'actor': 'human:owner'})
        altered = {**body, 'arguments': {**body['arguments'], 'text': 'changed'}}
        assert executor.execute(altered)['code'] == 'request_conflict'
        assert executor.resolve(body['request_id'], pending['request_digest'], 'approved', owner=Owner('human:owner'))
        assert executor.execute(body)['ok']
    finally:
        executor.close()


@REAL
def test_legacy_host_completion_cannot_be_promoted_into_isolated_evidence(tmp_path):
    body = request()
    legacy = LocalExecutor(tmp_path, authority())
    try:
        assert legacy.execute(body)['ok']
    finally:
        legacy.close()
    executor = NamespaceExecutor(tmp_path, authority(), experimental=True)
    try:
        assert executor.execute(body)['code'] == 'request_conflict'
    finally:
        executor.close()


@REAL
def test_isolated_tool_still_refuses_arbitrary_authority_and_audit_failure(tmp_path, monkeypatch):
    executor = NamespaceExecutor(tmp_path, authority(), experimental=True)
    try:
        assert executor.execute({**request(), 'actor': 'human:owner'})['code'] == 'invalid_request'
        assert executor.execute(request(tool='shell.run'))['code'] == 'invalid_request'
        launched = []
        monkeypatch.setattr(isolation, 'run_fixed', lambda *a, **k: launched.append(True))
        monkeypatch.setattr(executor, '_audit', lambda *a, **k: (_ for _ in ()).throw(sqlite3.OperationalError('fixture audit down')))
        assert not executor.execute(request())['ok']
        assert not launched
    finally:
        executor.close()


@REAL
def test_actual_namespace_deadline_kills_and_reaps_launcher(tmp_path):
    executor = NamespaceExecutor(tmp_path, authority(), experimental=True, timeout_s=0.15)
    try:
        result = executor.execute(request(delay=3000))
        assert result['status'] == 'timed_out' and result['child_exit_confirmed']
        with pytest.raises(ProcessLookupError):
            os.kill(result['pid'], 0)
    finally:
        executor.close()


@REAL
def test_actual_namespace_cancel_waits_for_observed_exit(tmp_path):
    a = authority()
    worker = NamespaceExecutor(tmp_path, a, experimental=True, timeout_s=4)
    cancel = NamespaceExecutor(tmp_path, a, experimental=True, timeout_s=4)
    body = request(delay=3000)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(worker.execute, body)
            end = time.monotonic() + 2
            while time.monotonic() < end:
                row = cancel.job(body['request_id'])
                if row and row['pid']:
                    break
                time.sleep(0.01)
            else:
                pytest.fail('isolated launcher never became observable')
            assert cancel.cancel(body['request_id'])['status'] == 'cancel_requested'
            result = future.result(timeout=4)
        assert result['status'] == 'cancelled' and result['child_exit_confirmed']
        with pytest.raises(ProcessLookupError):
            os.kill(result['pid'], 0)
    finally:
        worker.close()
        cancel.close()


def _filter_action(number, arch=0xC000003E):
    """Tiny evaluator for this reviewed four-op classic-BPF program, not a kernel proof."""
    import struct
    rows = list(struct.iter_unpack('HBBI', isolation.seccomp_program()))
    pc, accumulator = 0, 0
    while pc < len(rows):
        code, yes, no, value = rows[pc]
        if code == 0x20:
            accumulator = arch if value == 4 else number
        elif code in (0x15, 0x35):
            condition = accumulator == value if code == 0x15 else accumulator >= value
            pc += yes if condition else no
        elif code == 0x06:
            return value
        else:
            pytest.fail('unreviewed BPF instruction')
        pc += 1
    pytest.fail('no terminal BPF result')


@pytest.mark.parametrize('number', [41, 53, 56, 57, 58, 101, 165, 272, 298, 308,
                                    310, 311, 317, 321, 425, 426, 427, 434, 435, 438])
def test_filter_denies_alternate_network_process_kernel_and_fd_paths(number):
    assert _filter_action(number) == 0x00050001


def test_filter_rejects_other_abi_and_x32_and_keeps_basic_io():
    assert _filter_action(41, arch=0x40000003) == 0x80000000
    assert _filter_action(0x40000000) == 0x80000000
    assert _filter_action(0) == 0x7FFF0000
    assert _filter_action(1) == 0x7FFF0000


@REAL
def test_actual_parent_death_probe_leaves_no_observed_child_and_no_retry(tmp_path):
    import importlib.util
    source = isolation.ROOT / 'scripts/isolation-demo.py'
    spec = importlib.util.spec_from_file_location('namespace_parent_death_fixture', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    proof = module.parent_death_probe(tmp_path)
    assert proof['actual_supervisor_killed'] and proof['all_observed_tree_pids_gone']
    assert proof['supervisor_returncode'] == -9 and proof['interrupted_request_not_reexecuted']


@REAL
def test_namespace_launch_failure_cannot_fall_back_to_host_worker(tmp_path, monkeypatch):
    executor = NamespaceExecutor(tmp_path, authority(), experimental=True)
    called = []
    try:
        monkeypatch.setattr(LocalExecutor, '_child', lambda *_: pytest.fail('forbidden host fallback'))
        actual = isolation.subprocess.Popen
        def bad_namespace(command, **kw):
            called.append(True)
            # A genuinely failing mandatory namespace setup, not a mock successful sandbox.
            return actual([command[0], '--this-option-is-intentionally-invalid'], **kw)
        monkeypatch.setattr(isolation.subprocess, 'Popen', bad_namespace)
        result = executor.execute(request())
        assert not result['ok'] and result['code'] == 'reconciliation_required' and called
        assert executor.quota()['used_units'] == 1
    finally:
        executor.close()


@REAL
def test_missing_resource_evidence_is_not_promoted_to_verified_output(tmp_path, monkeypatch):
    from dataclasses import replace
    actual = isolation.run_fixed
    def without_limits(*args, **kwargs):
        child = actual(*args, **kwargs)
        frames = child.stdout[:-2].split(b'\n\n')
        start = json.loads(frames[0][6:])
        start['sandbox'].pop('rlimits', None)
        frames[0] = b'data: ' + json.dumps(start).encode()
        return replace(child, stdout=b'\n\n'.join(frames) + b'\n\n')
    executor = NamespaceExecutor(tmp_path, authority(), experimental=True)
    try:
        monkeypatch.setattr(isolation, 'run_fixed', without_limits)
        result = executor.execute(request())
        assert not result['ok'] and result['code'] == 'reconciliation_required'
    finally:
        executor.close()
