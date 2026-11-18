#!/usr/bin/env python3
"""Explicitly create NEW synthetic local-test inputs; never operating state."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent


def prepare(root):
    root = Path(os.path.abspath(root))
    if any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError("linked work root refused")
    if (
        not (root / "pyproject.toml").is_file()
        or not (root / ".openbot/routines/scout-daily.md").is_file()
    ):
        raise ValueError("explicit reviewed source work-root required")
    target = root / ".openbot/state"
    if any(p.is_symlink() for p in (target, *target.parents)) or target.exists():
        raise ValueError(
            "NEW absent state directory required; never overlay or repair existing state"
        )
    # Read fixed non-secret source fixtures before creating any output.
    files = {
        name: (HERE / "kernel-test-state" / name).read_bytes()
        for name in ("active_ventures.yaml", "budget.json")
    }
    target.mkdir(mode=0o700, exist_ok=False)
    for name, raw in files.items():
        fd = os.open(
            target / name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
    return {
        "synthetic_local_test_state_created": True,
        "files": len(files),
        "services_started": False,
        "external_actions_enabled": False,
        "note": "Only use in a disposable test copy. Never operating state or approval.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--work-root",
        type=Path,
        required=True,
        help="work/ inside an explicit disposable source copy",
    )
    parser.add_argument(
        "--for-local-tests",
        action="store_true",
        required=True,
        help="acknowledge this is not operating state",
    )
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.work_root), sort_keys=True))
        return 0
    except (ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
