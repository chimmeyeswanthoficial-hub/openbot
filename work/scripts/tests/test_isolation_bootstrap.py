"""Tool setup integrity fixtures: no network, root installation or real execution."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = importlib.util.spec_from_file_location('bootstrap_isolation_fixture', ROOT / 'scripts/bootstrap-isolation.py')
bootstrap = importlib.util.module_from_spec(MODULE)
MODULE.loader.exec_module(bootstrap)


@pytest.fixture()
def pinned(tmp_path, monkeypatch):
    lock = json.loads((ROOT / 'audit/isolation-runtime-lock.json').read_text())
    binary_bytes = b'synthetic pinned executable fixture, never execute'
    lock['binary_sha256'] = hashlib.sha256(binary_bytes).hexdigest()
    path = tmp_path / lock['cache_directory'] / lock['binary_relative_path']
    path.parent.mkdir(parents=True)
    path.write_bytes(binary_bytes)
    path.chmod(0o755)
    (tmp_path / 'audit').mkdir()
    (tmp_path / 'audit/isolation-runtime-lock.json').write_text(json.dumps(lock))
    monkeypatch.setattr(bootstrap, 'ROOT', tmp_path)
    monkeypatch.setattr(bootstrap.platform, 'machine', lambda: 'x86_64')
    calls = []
    def version(command, **kw):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, 'bubblewrap 0.12.0\n', '')
    monkeypatch.setattr(bootstrap.subprocess, 'run', version)
    monkeypatch.setattr(bootstrap.urllib.request, 'urlopen', lambda *_a, **_k: pytest.fail('fixture must never use network'))
    return tmp_path, path, lock, calls


def rewrite_lock(root, lock):
    (root / 'audit/isolation-runtime-lock.json').write_text(json.dumps(lock))


def test_check_pinned_existing_tool_does_not_install_or_download(pinned, capsys):
    _, _, _, calls = pinned
    assert bootstrap.main([]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['ok'] and not result['setuid'] and not result['production_ready']
    assert len(calls) == 1 and calls[0][-1] == '--version'


def test_missing_tool_refuses_without_implicit_download(pinned):
    _, binary, _, calls = pinned
    binary.unlink()
    with pytest.raises((ValueError, OSError)):
        bootstrap.main([])
    assert not calls


@pytest.mark.parametrize('mode', [0o4755, 0o2755, 0o775, 0o777, 0o644, 0o444])
def test_wrong_mode_never_executes_tool(pinned, mode):
    _, binary, _, calls = pinned
    binary.chmod(mode)
    with pytest.raises(ValueError):
        bootstrap.main([])
    assert not calls


def test_mismatched_binary_never_executes(pinned):
    _, binary, _, calls = pinned
    binary.write_bytes(b'corrupted fixture')
    with pytest.raises(ValueError):
        bootstrap.main([])
    assert not calls


def test_symlinked_binary_never_executes(pinned):
    root, binary, _, calls = pinned
    elsewhere = root / 'elsewhere'
    binary.rename(elsewhere)
    binary.symlink_to(elsewhere)
    with pytest.raises(ValueError):
        bootstrap.main([])
    assert not calls


def test_symlinked_parent_never_executes(pinned):
    _, binary, _, calls = pinned
    parent = binary.parent
    other = parent.with_name('other-bin')
    parent.rename(other)
    parent.symlink_to(other, target_is_directory=True)
    with pytest.raises(ValueError):
        bootstrap.main([])
    assert not calls


@pytest.mark.parametrize('field,value', [('cache_directory', '/tmp/outside'),
                                        ('cache_directory', '../outside'),
                                        ('cache_directory', 'outside'),
                                        ('binary_relative_path', '../../outside'),
                                        ('binary_relative_path', '/usr/bin/true'),
                                        ('package_bytes', True),
                                        ('package_bytes', 10 ** 9),
                                        ('url', 'http://example.test/package'),
                                        ('url', 'https://example.test/package'),
                                        ('binary_sha256', 'not-a-hash')])
def test_malformed_lock_refuses_before_any_effect(pinned, field, value):
    root, _, lock, calls = pinned
    lock[field] = value
    rewrite_lock(root, lock)
    with pytest.raises(ValueError):
        bootstrap.main(['--install'])
    assert not calls


def test_pinned_version_disagreement_is_refused(pinned, monkeypatch):
    monkeypatch.setattr(bootstrap.subprocess, 'run', lambda *_a, **_k: subprocess.CompletedProcess([], 0, 'bubblewrap 999\n', ''))
    with pytest.raises(ValueError):
        bootstrap.main([])


def test_cached_package_hash_failure_cannot_extract(pinned):
    root, binary, lock, calls = pinned
    destination = root / lock['cache_directory']
    binary.unlink()
    package = destination.parent / 'bubblewrap-pinned.deb'
    package.write_bytes(b'corrupted package fixture')
    with pytest.raises(ValueError):
        bootstrap.main(['--install'])
    assert not calls


def test_existing_partial_destination_is_not_overlaid_or_redownloaded(pinned):
    root, binary, lock, calls = pinned
    binary.unlink()
    # Check partial destination before fetching anything. Never "repair" over it.
    with pytest.raises(ValueError):
        bootstrap.main(['--install'])
    assert not calls and (root / lock['cache_directory']).is_dir()
