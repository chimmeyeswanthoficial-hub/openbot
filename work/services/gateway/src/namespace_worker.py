"""Reviewed fixed namespace worker; no arbitrary programs, files or network tools."""
from __future__ import annotations

import ctypes
import json
import os
import resource
import signal
import socket
import sys
import time


def security():
    status = {}
    with open('/proc/self/status') as stream:
        for line in stream:
            key, _, value = line.partition(':')
            if key in {'CapEff', 'NoNewPrivs', 'Seccomp'}:
                status[key] = value.strip()
    return {'status': status, 'environment_keys': sorted(os.environ),
            'rlimits': {name: resource.getrlimit(getattr(resource, 'RLIMIT_' + name))
                        for name in ('CPU', 'AS', 'FSIZE', 'NOFILE', 'CORE', 'NPROC')},
            'namespaces': {n: os.readlink('/proc/self/ns/' + n) for n in ('net', 'mnt', 'pid', 'user', 'uts', 'ipc')},
            'pid_count': len([n for n in os.listdir('/proc') if n.isdigit()]),
            # Bubblewrap creates PWD from the fixed --chdir, never from the host.
            'host_environment_absent': (set(os.environ) <= {'PATH', 'LANG', 'LC_CTYPE', 'PWD', 'PYTHONNOUSERSITE', 'PYTHONDONTWRITEBYTECODE'}
                                        and os.environ.get('PWD') == '/tmp')}


def blocked(fn):
    try:
        fn()
    except OSError:
        return True
    return False


def probe(body):
    path = body['host_canary']

    def read_canary():
        with open(path, 'rb') as stream:
            stream.read(1)  # Never print contents, even if a bad mount exposes it.

    def read_via_init_root():
        with open('/proc/1/root' + path, 'rb') as stream:
            stream.read(1)

    def write_canary():
        with open(path, 'r+b') as stream:
            stream.write(b'X')  # Caller supplies a disposable synthetic canary only.

    def write_file(path):
        with open(path, 'xb') as stream:
            stream.write(b'namespace-probe')

    def connect_socket(family):
        with socket.socket(family, socket.SOCK_STREAM):
            return

    libc = ctypes.CDLL(None, use_errno=True)
    result = security()
    result.update(host_read_blocked=blocked(read_canary), host_write_blocked=blocked(write_canary),
                  root_write_blocked=blocked(lambda: write_file('/escape-canary')),
                  tmp_write_blocked=blocked(lambda: write_file('/tmp/escape-canary')),
                  ipv4_socket_blocked=blocked(lambda: connect_socket(socket.AF_INET)),
                  ipv6_socket_blocked=blocked(lambda: connect_socket(socket.AF_INET6)),
                  unix_socket_blocked=blocked(lambda: connect_socket(socket.AF_UNIX)))
    ctypes.set_errno(0)
    sock = libc.syscall(41, socket.AF_INET, socket.SOCK_STREAM, 0)
    result['raw_syscall_socket_blocked'] = sock == -1 and ctypes.get_errno() == 1
    if sock >= 0:
        os.close(sock)
    # NULL params cannot create a usable ring even if a future filter drifts.
    ctypes.set_errno(0)
    ring = libc.syscall(425, 1, ctypes.c_void_p())
    result['raw_syscall_io_uring_blocked'] = ring == -1 and ctypes.get_errno() == 1
    if ring >= 0:
        os.close(ring)
    result['pid1_root_canary_blocked'] = blocked(read_via_init_root)
    ctypes.set_errno(0)
    result['nested_userns_blocked'] = libc.unshare(0x10000000) == -1 and ctypes.get_errno() == 1
    try:
        pid = os.fork()
    except PermissionError:
        result['fork_blocked'] = True
    else:
        if pid == 0:
            os._exit(0)
        os.waitpid(pid, 0)
        result['fork_blocked'] = False
    print(json.dumps(result, sort_keys=True), flush=True)


def main():
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0 or os.getppid() != 1:
        raise SystemExit('namespace parent guard unavailable')
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
    resource.setrlimit(resource.RLIMIT_AS, (128 * 1024 * 1024, 128 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (16, 16))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))
    raw = sys.stdin.buffer.read(65537)
    if len(raw) > 65536:
        raise SystemExit('input bound')
    body = json.loads(raw)
    mode = sys.argv[1]
    if mode == 'probe':
        probe(body)
        return
    if mode != 'wordcount':
        raise SystemExit('unknown fixed mode')
    rid = body['request_id']
    evidence = security()

    def emit(kind, **fields):
        print('data: ' + json.dumps({'type': kind, 'runId': rid, **fields}, separators=(',', ':')) + '\n', flush=True)

    emit('RUN_STARTED', threadId=rid, sandbox=evidence)
    emit('TOOL_CALL_START', toolCallId=rid + ':count', toolCallName='local.wordcount')
    time.sleep(body['delay_ms'] / 1000)
    result = {'words': len(body['text'].split()), 'characters': len(body['text']),
              'worker_pid': os.getpid(), 'minimal_environment': evidence['host_environment_absent']}
    emit('TOOL_CALL_END', toolCallId=rid + ':count')
    emit('TEXT_MESSAGE_START', messageId=rid + ':output', role='assistant')
    emit('TEXT_MESSAGE_CONTENT', messageId=rid + ':output', delta=json.dumps(result, sort_keys=True))
    emit('TEXT_MESSAGE_END', messageId=rid + ':output')
    emit('RUN_FINISHED', threadId=rid)


if __name__ == '__main__':
    main()
