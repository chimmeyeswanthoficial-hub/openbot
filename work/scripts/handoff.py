#!/usr/bin/env python3
"""Create/verify a private owner continuation archive. Never deletes project data.

Generated deps/builds, credentials, harness config and earlier copies of this bundle
are omitted. SQLite uses consistent backups; only HQ authentication tables are
sanitized in the COPY, with business row counts checked. No source DB is rewritten.
Verification rejects unsafe paths, links, duplicates, missing/extra files and bad
hashes before any extraction. This is integrity checking, not provenance signing.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import lzma
import os
import shutil
import sqlite3
import stat
import tarfile
from contextlib import closing
from datetime import UTC, date, datetime
from pathlib import Path, PurePosixPath
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_NAME = "openbot-continuation.tar.xz"
PREFIX = "openbot-continuation"
MANIFEST = "audit/continuation-manifest.json"
RECEIPT = "audit/continuation-bundle.json"
BYTE_CAP = 128_000_000
FILE_CAP = 10_000
GENERATED = {
    ".arena", ".cache", ".local", ".mypy_cache", ".next", ".nox", ".npm", ".nuxt",
    ".output", ".parcel-cache", ".playwright-cli", ".pytest_cache", ".ruff_cache",
    ".svelte-kit", ".tox", ".turbo", ".venv", ".vite", "__pycache__", "build",
    "coverage", "dist", "node_modules", "out", "target",
}
PRIVATE_DIRS = {".git", ".config", ".ssh", ".aws"}
SELF_OUTPUTS = {ARCHIVE_NAME, ARCHIVE_NAME + ".sha256", MANIFEST, RECEIPT}
BUSINESS_TABLES = ("users", "bots", "rows", "tasks", "skills", "hq_jobs", "audit", "runs", "ledger", "approvals")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_database(source: Path, target: Path, *, sanitize_hq: bool = False) -> dict:
    target.parent.mkdir(parents=True, exist_ok=True)
    # sqlite3's transaction context does not close a connection. Explicit closure
    # checkpoints the COPY's WAL before hashing/packing its main file, so neither
    # pre-redaction pages nor a later GC checkpoint can invalidate the export.
    with closing(sqlite3.connect(f"file:{quote(str(source))}?mode=ro", uri=True)) as src, closing(sqlite3.connect(target)) as dst:
        src.backup(dst)
        tables = {row[0] for row in dst.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        before = {name: dst.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]
                  for name in BUSINESS_TABLES if name in tables}
        stripped = {}
        if sanitize_hq:
            dst.execute("PRAGMA secure_delete=ON")
            for name in ("auth_sessions", "login_attempts"):
                if name in tables:
                    stripped[name] = dst.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]
                    dst.execute(f'DELETE FROM "{name}"')
            dst.commit()
            dst.execute("VACUUM")
        after = {name: dst.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]
                 for name in BUSINESS_TABLES if name in tables}
        if before != after:
            raise ValueError("business evidence changed during authentication sanitization")
    return {"kind": "consistent SQLite backup", "authentication_rows_removed_from_copy": stripped,
            "business_counts": before, "business_counts_preserved": True}


def _safe_name(name: str) -> str:
    path = PurePosixPath(name)
    if ("\\" in name or path.is_absolute() or ".." in path.parts or
            len(path.parts) < 2 or path.parts[0] != PREFIX or str(path) != name):
        raise ValueError(f"unsafe archive member name: {name!r}")
    return str(PurePosixPath(*path.parts[1:]))


def verify_bundle(archive_path: Path, *, expected_sha256: str | None = None) -> dict:
    actual_sha = _sha(archive_path)
    if expected_sha256 and actual_sha != expected_sha256:
        raise ValueError("archive digest mismatch")
    with tarfile.open(archive_path, "r:*") as archive:
        members = archive.getmembers()
        if len(members) > FILE_CAP or sum(m.size for m in members) > BYTE_CAP:
            raise ValueError("archive expands beyond workspace limits")
        by_path = {}
        for member in members:
            rel = _safe_name(member.name)
            if not member.isfile() or member.size < 0 or rel in by_path:
                raise ValueError("links/non-regular/duplicate archive members are refused")
            if member.mode & 0o7000:
                raise ValueError("special permission bits are refused")
            by_path[rel] = member
        if MANIFEST not in by_path or by_path[MANIFEST].size > 10_000_000:
            raise ValueError("missing or oversized manifest")
        manifest = json.load(archive.extractfile(by_path[MANIFEST]))
        rows = manifest.get("files", [])
        expected = {row["path"]: row for row in rows}
        if len(expected) != len(rows) or set(by_path) != {*expected, MANIFEST}:
            raise ValueError("manifest and archive file sets differ")
        for rel, row in expected.items():
            member = by_path[rel]
            if member.size != row["bytes"]:
                raise ValueError("payload size mismatch")
            digest = hashlib.sha256()
            with archive.extractfile(member) as stream:
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
            if digest.hexdigest() != row["sha256"]:
                raise ValueError("payload hash mismatch")
    return {"validated": True, "regular_files": len(members),
            "payload_bytes": sum(m.size for m in members), "archive_sha256": actual_sha,
            "checks": ["regular files only", "safe relative paths", "no duplicate members",
                       "manifest file set", "every payload size and SHA-256", "bounded expanded size"]}


def _credential_name(name: str) -> bool:
    return ((name.startswith(".env") and not name.endswith((".example", ".sample", ".template")))
            or name in {".netrc", ".git-credentials", "credentials.json", "credentials", "hosts.yml"}
            or name.endswith((".pem", ".key")))


def _source_files(root: Path) -> tuple[list[Path], list[dict]]:
    selected, omitted = [], []
    for base, dirs, files in os.walk(root, followlinks=False):
        base_path = Path(base)
        kept = []
        for name in sorted(dirs):
            path = base_path / name
            if name in GENERATED or name in PRIVATE_DIRS or path.is_symlink():
                omitted.append({"path": str(path.relative_to(root)) + "/",
                                "reason": "generated/private directory or symlink; not deleted"})
            else:
                kept.append(name)
        dirs[:] = kept
        for name in sorted(files):
            path = base_path / name
            rel = path.relative_to(root).as_posix()
            if rel in SELF_OUTPUTS:
                continue
            if (path.is_symlink() or not path.is_file() or _credential_name(name)
                    or name.endswith(("-wal", "-shm", "-journal"))):
                omitted.append({"path": rel, "reason": "credential/link/non-regular/SQLite journal; not deleted"})
                continue
            selected.append(path)
    return sorted(selected), omitted


def workspace_budget(root: Path) -> dict:
    size = count = 0
    for base, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in GENERATED]
        for name in files:
            path = Path(base) / name
            if path.is_file() and not path.is_symlink():
                count += 1
                size += path.stat().st_size
    return {"files": count, "bytes": size, "decimal_megabytes": round(size / 1_000_000, 3),
            "file_cap": FILE_CAP, "byte_cap": BYTE_CAP,
            "within_cap": count <= FILE_CAP and size <= BYTE_CAP}


def create_bundle(root: Path = ROOT, *, task_date: str) -> dict:
    date.fromisoformat(task_date)
    root = root.resolve()
    stage = root / ".cache/openbot-handoff"
    stage.mkdir(parents=True, exist_ok=True)
    paths, omitted = _source_files(root)
    staged_paths, rows = {}, []
    for index, path in enumerate(paths):
        rel = path.relative_to(root).as_posix()
        transform = None
        with path.open("rb") as stream:
            is_sqlite = stream.read(16) == b"SQLite format 3\x00"
        if is_sqlite:
            export = stage / f"database-{index}.sqlite3"
            if export.exists():
                # This is a generated private COPY only, not the source or business evidence.
                export = stage / f"database-{index}-{datetime.now(UTC).timestamp()}.sqlite3"
            transform = snapshot_database(path, export, sanitize_hq=rel == ".openbot/hq/hq.sqlite3")
            staged_paths[rel] = export
        else:
            staged_paths[rel] = path
        payload = staged_paths[rel]
        row = {"path": rel, "bytes": payload.stat().st_size, "sha256": _sha(payload),
               "mode": stat.S_IMODE(path.stat().st_mode) & 0o777}
        if transform:
            row["transformation"] = transform
        rows.append(row)
    manifest = {"schema": 1, "task_date": task_date,
                "observed_runner_utc": datetime.now(UTC).isoformat(),
                "scope": "Private owner continuation, not public redistribution/licence/security clearance",
                "files": rows, "omissions": omitted,
                "not_transferred": ["dependencies/toolchains/builds/caches", "authentication/credentials/harness settings",
                                    "running processes", "literal assistant identity or unlimited chat memory"],
                "preservation": "Source/business files are not deleted or rewritten; auth redaction affects export copies only"}
    manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode()
    staged_archive = stage / ARCHIVE_NAME
    with tarfile.open(staged_archive, "w:xz", preset=9 | lzma.PRESET_EXTREME) as archive:
        for row in rows:
            info = tarfile.TarInfo(f"{PREFIX}/{row['path']}")
            info.mode, info.size = row["mode"], row["bytes"]
            with staged_paths[row["path"]].open("rb") as stream:
                archive.addfile(info, stream)
            if _sha(staged_paths[row["path"]]) != row["sha256"]:
                raise ValueError("source changed during packaging; retry after checkpointing")
        info = tarfile.TarInfo(f"{PREFIX}/{MANIFEST}")
        info.mode, info.size = 0o644, len(manifest_bytes)
        archive.addfile(info, io.BytesIO(manifest_bytes))
    validation = verify_bundle(staged_archive)
    budget = workspace_budget(root)
    # Keep the full manifest INSIDE the archive rather than spending almost 2MB
    # duplicating it alongside the complete working tree. Never delete an older
    # external manifest if one happens to exist; count its bytes conservatively.
    replaced_outputs = {ARCHIVE_NAME, ARCHIVE_NAME + ".sha256", RECEIPT}
    old_bytes = sum((root / name).stat().st_size for name in replaced_outputs if (root / name).is_file())
    old_files = sum((root / name).is_file() for name in replaced_outputs)
    projected_bytes = budget["bytes"] - old_bytes + staged_archive.stat().st_size + 8192
    projected_files = budget["files"] - old_files + 3
    if projected_bytes > BYTE_CAP or projected_files > FILE_CAP:
        raise ValueError("bundle would exceed snapshot cap; nothing replaces the old deliverable")
    (root / "audit").mkdir(exist_ok=True)
    shutil.copy2(staged_archive, root / ARCHIVE_NAME)
    (root / (ARCHIVE_NAME + ".sha256")).write_text(validation["archive_sha256"] + "  " + ARCHIVE_NAME + "\n")
    receipt = {"task_date": task_date, "observed_runner_utc": datetime.now(UTC).isoformat(),
               "archive": ARCHIVE_NAME, "archive_bytes": (root / ARCHIVE_NAME).stat().st_size,
               "archive_sha256": validation["archive_sha256"], "validation": validation,
               "source_files": len(rows), "manifest": MANIFEST, "manifest_location": "inside archive only",
               "compression": "LZMA2 preset 9 extreme; sorted relative-path payload order",
               "omitted_entries": len(omitted), "workspace_budget": workspace_budget(root),
               "limits": ["Restore dependencies/builds/auth from pinned instructions; not an offline binary installation",
                          "Retained donor code is for private owner continuity; existing notices/rights still apply",
                          "Integrity digest is not a publisher signature or malware/secret-history certification"]}
    (root / RECEIPT).write_text(json.dumps(receipt, indent=2) + "\n")
    receipt["workspace_budget"] = workspace_budget(root)
    (root / RECEIPT).write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("--task-date", required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("archive", type=Path)
    verify.add_argument("--sha256")
    args = parser.parse_args()
    result = create_bundle(task_date=args.task_date) if args.command == "create" else verify_bundle(args.archive, expected_sha256=args.sha256)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
