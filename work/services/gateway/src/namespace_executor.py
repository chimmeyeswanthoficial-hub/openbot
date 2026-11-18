"""Explicit opt-in fixed namespace experiment on existing audited executor seams.

Not an HTTP route, arbitrary-code service, cgroup substitute or independent human
identity provider. Trusted HOST APIs still supply Authority/Owner. Never falls back
to the old host worker. No provider, money or external-delivery authority.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import isolation
from local_executor import EVENTS, ChildFailure, LocalExecutor, canonical, digest


class NamespaceExecutor(LocalExecutor):
    def __init__(self, *args, experimental=False, **kwargs):
        if experimental is not True:
            raise ValueError('experimental=True is required; general execution remains disabled')
        isolation.load_binary()
        super().__init__(*args, **kwargs)

    def _request_digest(self, body):
        here = Path(__file__)
        relevant = {'namespace_executor': here, 'isolation_launcher': here.with_name('isolation.py'),
                    'runtime_integrity': here.with_name('isolation_runtime.py'),
                    'namespace_worker': here.with_name('namespace_worker.py'),
                    'runtime_lock': isolation.ROOT / 'audit/isolation-runtime-lock.json',
                    'pinned_binary': isolation.load_binary()}
        return digest(canonical({'legacy_review_binding': super()._request_digest(body),
                                 'profile': 'rootless-fixed-v1',
                                 'files': {k: digest(p.read_bytes()) for k, p in relevant.items()}}).encode())

    def _child(self, body):
        rid = body['request_id']
        try:
            child = isolation.run_fixed('wordcount', {'request_id': rid,
                'text': body['arguments']['text'], 'delay_ms': body['arguments']['delay_ms']},
                timeout_s=self.timeout_s, cancelled=lambda: bool(self.job(rid)['cancel_requested']),
                on_start=lambda pid: self._update(rid, pid=pid))
        except isolation.IsolationFailure as exc:
            raise ChildFailure(exc.pid) from exc
        if child.terminal:
            return {'terminal': child.terminal, 'pid': child.pid, 'child_exit_confirmed': True}
        try:
            if child.returncode != 0 or not child.stdout.endswith(b'\n\n'):
                raise ValueError('no isolated completion')
            frames = child.stdout[:-2].split(b'\n\n')
            if len(frames) != len(EVENTS) or any(not f.startswith(b'data: ') for f in frames):
                raise ValueError('invalid isolated SSE')
            events = [json.loads(f[6:]) for f in frames]
            for kind, event in zip(EVENTS, events, strict=True):
                if not isinstance(event, dict) or event.get('runId') != rid or event.get('type') != kind:
                    raise ValueError('uncorrelated isolated event')
                if kind.startswith('TOOL_CALL_') and event.get('toolCallId') != rid + ':count':
                    raise ValueError('tool identity')
                if kind.startswith('TEXT_MESSAGE_') and event.get('messageId') != rid + ':output':
                    raise ValueError('message identity')
            evidence = events[0]['sandbox']
            if (evidence['status']['NoNewPrivs'] != '1' or evidence['status']['Seccomp'] != '2'
                    or int(evidence['status']['CapEff'], 16) != 0 or evidence['host_environment_absent'] is not True
                    or evidence['rlimits'] != {'CPU': [2, 2], 'AS': [134217728, 134217728],
                                              'FSIZE': [0, 0], 'NOFILE': [16, 16], 'CORE': [0, 0], 'NPROC': [1, 1]}
                    or type(evidence['pid_count']) is not int or not 1 <= evidence['pid_count'] <= 2):
                raise ValueError('missing fixed isolation controls')
            for name in ('net', 'mnt', 'pid', 'user', 'uts', 'ipc'):
                value = evidence['namespaces'][name]
                if not isinstance(value, str) or not re.fullmatch(r'[a-z]+:\[\d+\]', value) or value == os.readlink('/proc/self/ns/' + name):
                    raise ValueError('namespace did not change')
            result = json.loads(events[4]['delta'])
            if result != {'words': len(body['arguments']['text'].split()),
                          'characters': len(body['arguments']['text']),
                          'worker_pid': 2, 'minimal_environment': True}:
                raise ValueError('untrusted isolated count')
            result['isolation'] = {'profile': 'rootless-fixed-v1', 'cgroup_enforced': False,
                                   'general_hostile_execution_authorized': False, **evidence}
            return {'result': result, 'events': events, 'pid': child.pid}
        except (ValueError, KeyError, TypeError) as exc:
            raise ChildFailure(child.pid) from exc
