#!/usr/bin/env python3
"""Conservative housekeeping: dry-run by default; remove only untracked Python/tool caches.

Never remove business state, logs, run evidence, source, donor repos, or archives. This is not a
production retention policy. Call with --apply only after reviewing the read-only --check output.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

CACHE_NAMES = {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
SOURCE_ROOTS = {"services", "packages", "scripts"}
EXCLUDE = {".git", ".openbot", "repos", "archive", "node_modules", ".venv", ".config"}


def tracked_paths(root: Path) -> set[Path]:
    """If a Git index exists, we must read it successfully before deleting anything."""
    try:
        top = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError:
        if any((p / ".git").exists() for p in (root, *root.parents)):
            raise RuntimeError("git unavailable; cannot prove cache files are untracked") from None
        return set()
    if top.returncode:
        if any((p / ".git").exists() for p in (root, *root.parents)):
            raise RuntimeError("cannot read Git metadata; refusing cleanup")
        return set()
    git_root = Path(top.stdout.strip()).resolve()
    index = subprocess.run(
        ["git", "-C", str(git_root), "ls-files", "--cached", "-z"],
        capture_output=True, check=False,
    )
    if index.returncode:
        raise RuntimeError("cannot read Git index; refusing cleanup")
    return {git_root / os.fsdecode(p) for p in index.stdout.split(b"\0") if p}


def candidates(root: Path, tracked: set[Path]) -> tuple[list[Path], list[Path]]:
    """Do not follow symlinks, or descend into data / third-party directories."""
    removable, retained = [], []
    for current, directories, _ in os.walk(root, followlinks=False):
        base = Path(current)
        keep = []
        for name in sorted(directories):
            path = base / name
            if path.is_symlink() or name in EXCLUDE:
                continue
            if name in CACHE_NAMES:
                if any(p == path or path in p.parents for p in tracked):
                    retained.append(path)
                else:
                    removable.append(path)
                continue
            if base != root or name in SOURCE_ROOTS:
                keep.append(name)
        directories[:] = keep
    return removable, retained


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="list caches; never change files (default)")
    mode.add_argument("--apply", action="store_true", help="remove the listed untracked caches only")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    try:
        tracked = tracked_paths(root)
        removable, retained = candidates(root, tracked)
        for path in retained:
            print(f"KEEP (contains tracked files): {path.relative_to(root)}")
        for path in removable:
            print(f"{'REMOVE' if args.apply else 'WOULD REMOVE'}: {path.relative_to(root)}")
        if not args.apply:
            print(f"clean: read-only; {len(removable)} cache directorie(s); no records touched")
            return 1 if removable else 0
        for path in removable:
            # Recheck before removal; cleanup is an operator task, not a concurrent janitor.
            if path.is_symlink():
                raise RuntimeError(f"path changed to a symlink: {path.relative_to(root)}")
            shutil.rmtree(path)
        print(f"clean: removed {len(removable)} cache directorie(s); business records retained")
        return 0
    except (OSError, RuntimeError) as exc:
        print(f"clean: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
