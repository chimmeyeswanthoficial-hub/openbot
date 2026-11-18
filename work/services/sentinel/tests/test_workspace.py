"""Housekeeping must not erase the company or publish code while trying to tidy it."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[3]


def _copy_script(root: Path, name: str) -> Path:
    directory = root / "scripts"
    directory.mkdir(exist_ok=True)
    script = directory / name
    shutil.copy2(ROOT / "scripts" / name, script)
    if name == "clean.sh" and (ROOT / "scripts/workspace_hygiene.py").exists():
        shutil.copy2(ROOT / "scripts/workspace_hygiene.py", directory)
    return script


def _run(script: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(script), *args], capture_output=True, text=True, check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


def _put(root: Path, relative: str, content: str = "keep this") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


@pytest.mark.parametrize("args", [(), ("--check",)])
def test_cleanup_is_read_only_until_explicitly_applied(tmp_path, args):
    script = _copy_script(tmp_path, "clean.sh")
    cache = _put(tmp_path, ".pytest_cache/example", "regenerable")
    result = _run(script, *args)
    assert result.returncode == 1, result.stdout + result.stderr
    assert cache.read_text() == "regenerable"


@pytest.mark.parametrize("args", [("--force",), ("--apply", "--typo")])
def test_cleanup_rejects_unknown_args_without_mutation(tmp_path, args):
    script = _copy_script(tmp_path, "clean.sh")
    cache = _put(tmp_path, ".pytest_cache/example")
    result = _run(script, *args)
    assert result.returncode == 2, result.stdout + result.stderr
    assert cache.exists()


def test_cleanup_only_removes_known_caches_not_business_records(tmp_path):
    script = _copy_script(tmp_path, "clean.sh")
    caches = [
        _put(tmp_path, ".pytest_cache/example"),
        _put(tmp_path, "services/a path with spaces/__pycache__/example.pyc"),
        _put(tmp_path, ".ruff_cache/example"),
    ]
    records = [
        ".openbot/runs/order-1/stderr.log",
        ".openbot/runs/order-1/meta.json",
        ".openbot/state/openbot.db",
        ".openbot/state/pnl.json",
        ".openbot/state/budget.json",
        ".openbot/post_mortems/error_registry.jsonl",
        "repos/donor/.pytest_cache/record",
        "archive/__pycache__/record",
        "data/customers.log",
        "services/deployment.log",
        "source.py",
        "loose.pyc",
        ".venv/__pycache__/record",
        "node_modules/library/__pycache__/record",
        ".config/tool/.pytest_cache/record",
    ]
    paths = [_put(tmp_path, p) for p in records]
    result = _run(script, "--apply")
    assert result.returncode == 0, result.stdout + result.stderr
    assert not any(p.exists() for p in caches)
    assert all(p.read_text() == "keep this" for p in paths)
    assert _run(script, "--check").returncode == 0


def test_cleanup_never_follows_cache_symlinks(tmp_path):
    script = _copy_script(tmp_path, "clean.sh")
    outside = tmp_path / "outside"
    _put(outside, "record.txt")
    (tmp_path / ".ruff_cache").symlink_to(outside, target_is_directory=True)
    result = _run(script, "--apply")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / ".ruff_cache").is_symlink()
    assert (outside / "record.txt").read_text() == "keep this"


def test_cleanup_preserves_git_tracked_cache_contents(tmp_path):
    script = _copy_script(tmp_path, "clean.sh")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    tracked = _put(tmp_path, "services/__pycache__/tracked.txt")
    cache = _put(tmp_path, "services/__pycache__/runtime.pyc")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-f", str(tracked)], check=True)
    result = _run(script, "--apply")
    assert result.returncode == 0, result.stdout + result.stderr
    assert tracked.read_text() == "keep this"
    # Retain the entire directory if any part is tracked; don't partially erase evidence.
    assert cache.exists()


def test_cleanup_refuses_to_delete_if_git_index_cannot_be_read(tmp_path):
    script = _copy_script(tmp_path, "clean.sh")
    (tmp_path / ".git").mkdir()
    cache = _put(tmp_path, ".pytest_cache/example")
    result = _run(script, "--apply")
    assert result.returncode == 2, result.stdout + result.stderr
    assert cache.exists()


@pytest.mark.parametrize("args", [("--init",), ("--push", "someone"), ("--check", "extra")])
def test_upstream_helper_cannot_initialize_or_push_repositories(tmp_path, args):
    script = _copy_script(tmp_path, "mirror-upstreams.sh")
    donor = _put(tmp_path, "repos/OpenBot/LICENSE", "licence stays here")
    result = _run(script, *args)
    assert result.returncode == 2, result.stdout + result.stderr
    assert donor.read_text() == "licence stays here"
    assert not (donor.parent / ".git").exists()
    assert not (tmp_path / ".mirror-scratch").exists()


def test_upstream_check_only_reports_local_provenance(tmp_path):
    script = _copy_script(tmp_path, "mirror-upstreams.sh")
    donor = _put(tmp_path, "repos/OpenBot/LICENSE", "licence stays here")
    result = _run(script, "--check")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "no git history" in result.stdout
    assert donor.read_text() == "licence stays here"
    assert not (donor.parent / ".git").exists()


def test_make_lint_propagates_failure(tmp_path):
    shutil.copy2(ROOT / "Makefile", tmp_path / "Makefile")
    fake_python = _put(tmp_path, "bad-python", "#!/bin/sh\nexit 7\n")
    fake_python.chmod(0o755)
    result = subprocess.run(
        ["make", "lint", f"PY={fake_python}"], cwd=tmp_path,
        capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0, "make lint turned a linter failure into a successful build"


@pytest.mark.parametrize("curl_exit, expected", [(0, 0), (22, 1)])
def test_console_smoke_consumes_the_body_and_requires_http_success(tmp_path, curl_exit, expected):
    # A slow/large response used to SIGPIPE curl when grep -q exited after the title. Exercise the
    # actual smoke section with a deterministic streaming curl fixture, without a server/network.
    curl = _put(
        tmp_path, "curl",
        f"#!{sys.executable}\nimport os\n"
        "os.write(1, b'OpenBot OS\\n')\n"
        "for _ in range(256):\n    os.write(1, b'x' * 8192)\n"
        f"raise SystemExit({curl_exit})\n",
    )
    curl.chmod(0o755)
    source = (ROOT / "scripts/smoke.sh").read_text()
    section = source.split("# --- console + overview\n", 1)[1].split(
        '\ncurl -s "127.0.0.1:$PORT/v1/overview"', 1,
    )[0]
    result = subprocess.run(
        ["bash", "-o", "pipefail", "-c", 'PORT=1; check() { test "$1" = 1; };\n' + section],
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"},
        capture_output=True, text=True, check=False, timeout=15,
    )
    assert result.returncode == expected, result.stdout + result.stderr


@pytest.mark.parametrize("state", ["verified", "tampered", "missing"])
def test_provenance_report_understands_archived_donors_without_mutating_sources(tmp_path, state):
    script = _copy_script(tmp_path, "mirror-upstreams.sh")
    archive = _put(tmp_path, "archive/donor-sources/rakazo.tar.xz", "opaque source archive")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    catalogue = {"donors": {"rakazo": {"archive": "archive/donor-sources/rakazo.tar.xz",
                                      "archive_sha256": digest}}}
    _put(tmp_path, "audit/donor-consolidation.json", json.dumps(catalogue))
    private = _put(tmp_path, "repos/OpenDots/.env", "never report or alter this")
    if state == "tampered":
        archive.write_text("changed archive")
    elif state == "missing":
        archive.unlink()
    before = archive.read_bytes() if archive.exists() else None
    result = _run(script, "--check")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "rakazo: archived source" in result.stdout
    assert ("SHA-256 matches" if state == "verified" else "UNVERIFIED") in result.stdout
    assert "never report or alter this" not in result.stdout
    assert private.read_text() == "never report or alter this"
    assert (archive.read_bytes() if archive.exists() else None) == before
    assert not (tmp_path / "repos/rakazo").exists()
