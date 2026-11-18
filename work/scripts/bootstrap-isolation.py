#!/usr/bin/env python3
"""Restore/check the pinned non-setuid fixed-namespace tool in excluded cache only."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import stat
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'services/gateway/src'))
from isolation_runtime import checked_binary, load_lock, no_symlinks  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', action='store_true', help='download and extract exact package; no root/service startup')
    args = parser.parse_args(argv)
    if sys.platform != 'linux' or platform.machine() != 'x86_64':
        raise ValueError('only the measured Linux x86_64 profile is supported')
    lock = load_lock(ROOT)
    destination = ROOT / lock['cache_directory']
    binary = destination / lock['binary_relative_path']
    no_symlinks(binary)
    if not binary.exists() and args.install:
        # Never fetch/extract over even an incomplete existing tool directory.
        if destination.exists():
            raise ValueError('partial destination exists; inspect before a new reviewed setup')
        destination.parent.mkdir(parents=True, exist_ok=True)
        package = destination.parent / 'bubblewrap-pinned.deb'
        no_symlinks(package)
        if not package.exists():
            request = urllib.request.Request(lock['url'], headers={'User-Agent': 'OpenBot-pinned-tool-restore'})
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = response.read(lock['package_bytes'] + 1)
            if len(payload) != lock['package_bytes'] or hashlib.sha256(payload).hexdigest() != lock['package_sha256']:
                raise ValueError('downloaded package does not match lock')
            fd = os.open(package, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(payload)
        if (not package.is_file() or not stat.S_ISREG(package.stat().st_mode)
                or package.stat().st_size != lock['package_bytes']
                or hashlib.sha256(package.read_bytes()).hexdigest() != lock['package_sha256']):
            raise ValueError('cached package does not match lock; no overwrite')
        subprocess.run(['/usr/bin/dpkg-deb', '-x', str(package), str(destination)], check=True,
                       timeout=10, env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
    binary = checked_binary(ROOT, lock)
    version = subprocess.run([str(binary), '--version'], check=True, capture_output=True, text=True,
                             timeout=5, env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
    upstream_version = re.fullmatch(r'(\d+\.\d+\.\d+)-.+', lock['version'])[1]
    if version.stdout.strip() != f'bubblewrap {upstream_version}' or version.stderr:
        raise ValueError('pinned executable version disagrees with lock')
    print(json.dumps({'ok': True, 'binary': str(binary.relative_to(ROOT)),
                      'binary_sha256': lock['binary_sha256'], 'version': version.stdout.strip(),
                      'setuid': False, 'cgroup_path_writable': os.access('/sys/fs/cgroup', os.W_OK),
                      'cgroup_delegated': False, 'production_ready': False,
                      'server_or_provider_started': False}, indent=2))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f'isolation setup refused: {exc}', file=sys.stderr)
        raise SystemExit(2) from None
