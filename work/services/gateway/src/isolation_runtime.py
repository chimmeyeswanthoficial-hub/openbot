"""Shared integrity checks for the trusted-host fixed namespace experiment.

Pins protect byte identity against accidental download/cache drift, not a hostile
host administrator, source modification or kernel vulnerability. No installation.
"""
from __future__ import annotations

import hashlib
import json
import platform
import re
import stat
from pathlib import Path


def no_symlinks(path: Path):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('symlinked fixed-tool path')


def load_lock(root: Path) -> dict:
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise ValueError('only the measured Linux x86_64 fixed-tool profile is supported')
    source = root / 'audit/isolation-runtime-lock.json'
    no_symlinks(source)
    if not source.is_file() or source.stat().st_size > 32768:
        raise ValueError('missing or oversized tool lock')
    lock = json.loads(source.read_bytes())
    if not isinstance(lock, dict):
        raise ValueError('tool lock must be an object')
    try:
        version = lock['version']
        parsed = re.fullmatch(r'(\d+\.\d+\.\d+)-\d+~deb13u(\d+)', version)
        if (type(lock['schema']) is not int or lock['schema'] != 1 or parsed is None
                or lock['package'] != 'bubblewrap' or lock['architecture'] != 'amd64'
                or lock['distribution'] != 'Debian trixie'
                or lock['profile'] != 'debian13-linux-x86_64-fixed-namespace-experiment'
                or lock['binary_relative_path'] != 'usr/bin/bwrap'
                or lock['cache_directory'] != f'.cache/openbot-isolation/bubblewrap-{parsed[1]}-deb13u{parsed[2]}'
                or type(lock['package_bytes']) is not int or not 1024 <= lock['package_bytes'] <= 1_048_576
                or lock['url'] != 'https://deb.debian.org/debian/pool/main/b/bubblewrap/' + f'bubblewrap_{version}_amd64.deb'
                or any(not isinstance(lock[k], str) or not re.fullmatch('[0-9a-f]{64}', lock[k])
                       for k in ('package_sha256', 'binary_sha256'))):
            raise ValueError('invalid tool lock bounds, paths or pinned download origin')
    except (KeyError, TypeError) as exc:
        raise ValueError('invalid fixed-tool lock shape') from exc
    return lock


def checked_binary(root: Path, lock: dict) -> Path:
    path = root / lock['cache_directory'] / lock['binary_relative_path']
    no_symlinks(path)
    if (not path.is_file() or not stat.S_ISREG(path.stat().st_mode)
            or stat.S_IMODE(path.stat().st_mode) != 0o755 or path.stat().st_size > 4_194_304
            or hashlib.sha256(path.read_bytes()).hexdigest() != lock['binary_sha256']):
        raise ValueError('pinned regular mode-0755 tool unavailable; never fall back')
    return path
