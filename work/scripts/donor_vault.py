#!/usr/bin/env python3
"""Verify/recover inert donor sources. Never deletes sources or activates donor code.

Checks trusted expected SHA-256, bounded regular members, exact manifest file set,
paths, sizes, modes and every file hash before writing. Recovery only targets a new
non-symlink directory, never an existing project. Run on a trusted, quiescent host;
these checks are not hostile-process isolation, provenance or licence clearance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tarfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from handoff import GENERATED, PRIVATE_DIRS, _credential_name

PREFIX = "donor-source"
MANIFEST = f"{PREFIX}/manifest.json"
ALLOWED_SOURCES = {"repos/rakazo", "repos/OpenDots"}
MAX_FILES = 10_000
MAX_BYTES = 128_000_000
MAX_MANIFEST_BYTES = 4_000_000
DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def _hash(stream) -> str:
    digest = hashlib.sha256()
    while chunk := stream.read(1024 * 1024):
        digest.update(chunk)
    return digest.hexdigest()


def _relative(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("missing relative path")
    path = PurePosixPath(value)
    if (path.is_absolute() or ".." in path.parts or str(path) != value or value == "."
            or any(c in value for c in "\\:\0") or any(ord(c) < 32 for c in value)):
        raise ValueError("unsafe or noncanonical path")
    return value


def _source_path(value: str) -> str:
    value = _relative(value)
    if any(p in GENERATED | PRIVATE_DIRS or _credential_name(p)
           for p in PurePosixPath(value).parts):
        raise ValueError("generated or private file in donor archive")
    return value


@contextmanager
def _validated(path: Path, expected_sha256: str):
    if not isinstance(expected_sha256, str) or not DIGEST.fullmatch(expected_sha256):
        raise ValueError("an independently retained lowercase SHA-256 is required")
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError("archive must be a regular non-symlink file")
    with path.open("rb") as raw:
        if _hash(raw) != expected_sha256:
            raise ValueError("archive SHA-256 mismatch")
        raw.seek(0)
        with tarfile.open(fileobj=raw, mode="r:*") as archive:
            members, expanded = {}, 0
            for member in archive:
                name = _relative(member.name)
                if (not member.isfile() or member.mode & ~0o777 or member.size < 0
                        or name in members or not name.startswith(f"{PREFIX}/")):
                    raise ValueError("nonregular, duplicate, foreign or special-mode member")
                members[name] = member
                expanded += member.size
                if len(members) > MAX_FILES + 1 or expanded > MAX_BYTES:
                    raise ValueError("archive expands beyond limits")
            info = members.get(MANIFEST)
            if info is None or info.size > MAX_MANIFEST_BYTES:
                raise ValueError("missing or oversized manifest")
            with archive.extractfile(info) as stream:
                manifest = json.load(stream)
            if (not isinstance(manifest, dict) or type(manifest.get("schema")) is not int
                    or manifest["schema"] != 1
                    or not isinstance(manifest.get("source_root"), str)
                    or manifest["source_root"] not in ALLOWED_SOURCES):
                raise ValueError("unsupported donor manifest or source root")
            rows = manifest.get("files")
            if not isinstance(rows, list) or not rows or len(rows) > MAX_FILES:
                raise ValueError("invalid manifest file list")
            expected, paths = {}, set()
            for row in rows:
                if not isinstance(row, dict):
                    raise ValueError("invalid file record")
                rel = _source_path(row.get("path"))
                if (type(row.get("bytes")) is not int or row["bytes"] < 0
                        or type(row.get("mode")) is not int or row["mode"] & ~0o777
                        or not isinstance(row.get("sha256"), str)
                        or not DIGEST.fullmatch(row["sha256"]) or rel in paths):
                    raise ValueError("invalid or duplicate manifest record")
                paths.add(rel)
                expected[f"{PREFIX}/files/{rel}"] = row
            if "LICENSE" not in paths:
                raise ValueError("donor root licence must be preserved")
            if any(str(parent) in paths for p in paths for parent in PurePosixPath(p).parents):
                raise ValueError("a file cannot also be a directory")
            if set(members) != {*expected, MANIFEST}:
                raise ValueError("manifest and archive file sets differ")
            for name, row in expected.items():
                info = members[name]
                if info.size != row["bytes"] or info.mode != row["mode"]:
                    raise ValueError("payload size or mode mismatch")
                with archive.extractfile(info) as stream:
                    if _hash(stream) != row["sha256"]:
                        raise ValueError("payload hash mismatch")
            summary = {"validated": True, "source_root": manifest["source_root"],
                       "archive_sha256": expected_sha256, "files": len(rows),
                       "payload_bytes": sum(r["bytes"] for r in rows),
                       "expanded_with_manifest_bytes": expanded}
            yield archive, manifest, summary


def verify_archive(path: Path, *, expected_sha256: str) -> dict:
    with _validated(Path(path), expected_sha256) as (_, _manifest, summary):
        return summary


def restore_archive(path: Path, destination: Path, *, expected_sha256: str) -> dict:
    destination = Path(destination).absolute()
    if (".." in destination.parts or destination.exists()
            or any(p.is_symlink() for p in (destination, *destination.parents))
            or not destination.parent.is_dir()):
        raise ValueError("restore requires a new path under an existing non-symlink parent")
    with _validated(Path(path), expected_sha256) as (archive, manifest, summary):
        # All checks complete before the first filesystem write. No extractall(),
        # ownership restoration, install hooks or execution of recovered code.
        destination.mkdir(mode=0o700)
        for row in manifest["files"]:
            target = destination / row["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256()
            size = 0
            with archive.extractfile(f"{PREFIX}/files/{row['path']}") as source, target.open("xb") as out:
                while chunk := source.read(1024 * 1024):
                    out.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
            if size != row["bytes"] or digest.hexdigest() != row["sha256"]:
                raise ValueError("payload changed during recovery; keep partial directory for inspection")
            os.chmod(target, row["mode"])
        return {**summary, "files_restored": len(manifest["files"]),
                "destination": str(destination), "sources_deleted": False,
                "code_executed": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("verify", "restore"):
        task = sub.add_parser(command)
        task.add_argument("archive", type=Path)
        task.add_argument("--sha256", required=True)
        if command == "restore":
            task.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            result = verify_archive(args.archive, expected_sha256=args.sha256)
        else:
            result = restore_archive(args.archive, args.destination, expected_sha256=args.sha256)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, tarfile.TarError) as exc:
        print(f"donor-vault: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
