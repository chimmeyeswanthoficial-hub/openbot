#!/usr/bin/env python3
"""Read-only workspace identity check; includes labeled test builds, not release approval."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {".cache", "__pycache__", ".pytest_cache", ".ruff_cache", ".venv", "node_modules"}


def safe_file(root, name):
    rel = PurePosixPath(name)
    if (
        not isinstance(name, str)
        or not name
        or rel.is_absolute()
        or str(rel) != name
        or "\\" in name
        or any(p in (".", "..") for p in rel.parts)
    ):
        raise ValueError("unsafe manifest path")
    path = root / name
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("symlink refused: " + name)
    observed = path.stat()
    if not stat.S_ISREG(observed.st_mode) or observed.st_nlink != 1:
        raise ValueError("regular single-link source required: " + name)
    return path, observed


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def check(root=ROOT, *, strict=False):
    path, _ = safe_file(root, "SOURCE_MANIFEST.json")
    manifest = json.loads(path.read_bytes())
    if (
        manifest.get("schema") != "openbot.workspace-source/1"
        or not isinstance(manifest.get("files"), dict)
        or not 1 <= len(manifest["files"]) <= 10000
    ):
        raise ValueError("bounded source manifest required")
    # Legacy small fixture manifests may omit this optional summary. If supplied,
    # it must describe the actual file map, not an obsolete or differently encoded one.
    if "files_metadata_sha256" in manifest:
        encoded = json.dumps(manifest["files"], sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        if hashlib.sha256(encoded).hexdigest() != manifest["files_metadata_sha256"]:
            raise ValueError("manifest metadata digest mismatch")
    for name, meta in manifest["files"].items():
        path, observed = safe_file(root, name)
        if observed.st_size != meta["bytes"] or digest(path) != meta["sha256"]:
            raise ValueError("source identity mismatch: " + name)
        if os.name == "posix" and observed.st_mode & 0o777 != meta["mode"]:
            raise ValueError("source mode mismatch: " + name)
    if strict:
        extras = []
        for path in root.rglob("*"):
            rel = path.relative_to(root)
            if any(p in IGNORED for p in rel.parts):
                continue
            rel_posix = rel.as_posix()
            if (
                path.is_file()
                and rel_posix not in manifest["files"]
                and rel_posix != "SOURCE_MANIFEST.json"
            ):
                extras.append(rel_posix)
        if extras:
            raise ValueError("unlisted files present: " + ", ".join(extras[:5]))
    return {
        "schema": manifest["schema"],
        "verified_files": len(manifest["files"]),
        "source_bytes": sum(m["bytes"] for m in manifest["files"].values()),
        "signed_release": False,
        "scope": "workspace file integrity only; no installs, network, runtime state or release acceptance",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict", action="store_true", help="also refuse unexpected non-cache files"
    )
    args = parser.parse_args()
    try:
        print(json.dumps(check(strict=args.strict), sort_keys=True))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
