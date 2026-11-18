#!/usr/bin/env python3
"""Verify a LOCAL committed Git source tree; never fetch, execute source, or approve release."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
MAX_FILES = 10000
MAX_BLOB = 100 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024
OID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def git_environment():
    env = dict(os.environ)
    for name in list(env):
        # Do not inherit alternate repositories, config injection, askpass, tracing
        # or GIT_ALLOW_PROTOCOL (which can override protocol.*.allow settings).
        if name.startswith("GIT_"):
            env.pop(name, None)
    env.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_TERMINAL_PROMPT="0",
        GIT_NO_LAZY_FETCH="1",
        GIT_NO_REPLACE_OBJECTS="1",
        GIT_OPTIONAL_LOCKS="0",
    )
    return env


def git_command(root):
    args = ["git", "--no-pager", "--no-replace-objects", "-C", str(root)]
    # A missing local object must fail closed, never trigger a credential helper
    # or a promisor/partial-clone network fetch. No transports are needed here.
    for protocol in (None, "http", "https", "ssh", "git", "file", "ext"):
        key = "protocol.allow" if protocol is None else f"protocol.{protocol}.allow"
        args.extend(["-c", key + "=never"])
    args.extend(["-c", "core.fsmonitor=false"])
    return args


def query(root, *args, missing_ok=False):
    result = subprocess.run(
        [*git_command(root), *args],
        env=git_environment(),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=30,
        check=False,
    )
    if missing_ok and result.returncode == 1:
        return b""
    if result.returncode:
        raise ValueError(
            "local Git query failed; require a valid ref and locally available objects"
        )
    return result.stdout


def safe_name(name):
    if not isinstance(name, str) or not name or "\\" in name:
        raise ValueError("unsafe manifest/Git path")
    rel = PurePosixPath(name)
    if (
        rel.is_absolute()
        or str(rel) != name
        or any(p in {".", ".."} or p.lower() == ".git" for p in rel.parts)
        or any(ord(c) < 32 or ord(c) == 127 for c in name)
    ):
        raise ValueError("unsafe manifest/Git path")
    return name


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key in source manifest")
        result[key] = value
    return result


class GitObjects:
    def __init__(self, root):
        self.process = subprocess.Popen(
            [*git_command(root), "cat-file", "--batch"],
            env=git_environment(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

    def __enter__(self):
        return self

    def read(self, oid, limit=MAX_BLOB):
        if not OID.fullmatch(oid):
            raise ValueError("invalid local Git object identity")
        self.process.stdin.write((oid + "\n").encode("ascii"))
        self.process.stdin.flush()
        header = self.process.stdout.readline(256)
        fields = header.decode("ascii").split()
        if not header.endswith(b"\n") or len(fields) != 3 or fields[:2] != [oid, "blob"]:
            raise ValueError("local Git blob unavailable; this verifier does not fetch")
        size = int(fields[2])
        if not 0 <= size <= limit:
            raise ValueError("committed blob exceeds verification size bound")
        raw = self.process.stdout.read(size)
        if len(raw) != size or self.process.stdout.read(1) != b"\n":
            raise ValueError("incomplete local Git blob")
        return raw

    def __exit__(self, exc_type, exc, traceback):
        self.process.stdin.close()
        try:
            code = self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
            code = -1
        finally:
            self.process.stdout.close()
        if exc_type is None and code:
            raise ValueError("local Git object reader failed")
        return False


def check(root=ROOT, *, revision="HEAD"):
    if query(
        root,
        "config",
        "--local",
        "--get-regexp",
        r"^(extensions\.partialclone|remote\..*\.promisor)$",
        missing_ok=True,
    ):
        raise ValueError(
            "partial/promisor configuration refused; use a full local clone, no fetch performed"
        )
    commit = query(root, "rev-parse", "--verify", "--end-of-options", revision + "^{commit}")
    commit = commit.decode("ascii").strip()
    if not OID.fullmatch(commit):
        raise ValueError("full committed Git revision required")
    listing = query(root, "ls-tree", "-r", "-z", "--full-tree", commit)
    entries = {}
    for record in listing.split(b"\0"):
        if not record:
            continue
        head, path = record.split(b"\t", 1)
        mode, kind, oid = head.decode("ascii").split()
        name = safe_name(path.decode("utf-8"))
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise ValueError("non-regular committed entry (symlink/gitlink refused): " + name)
        if name in entries or not OID.fullmatch(oid):
            raise ValueError("invalid/duplicate committed entry")
        entries[name] = (mode, oid)
        if len(entries) > MAX_FILES + 1:
            raise ValueError("committed tree exceeds file-count bound")
    if "SOURCE_MANIFEST.json" not in entries:
        raise ValueError("committed SOURCE_MANIFEST.json is missing")
    if entries["SOURCE_MANIFEST.json"][0] != "100644":
        raise ValueError("source manifest must have regular non-executable Git mode")
    with GitObjects(root) as objects:
        raw = objects.read(entries["SOURCE_MANIFEST.json"][1], 4 * 1024 * 1024)
        manifest = json.loads(raw, object_pairs_hook=unique_pairs)
        if not isinstance(manifest, dict):
            raise ValueError("committed source manifest must be an object")
        files = manifest.get("files")
        if (
            manifest.get("schema") != "openbot.workspace-source/1"
            or not isinstance(files, dict)
            or not 1 <= len(files) <= MAX_FILES
        ):
            raise ValueError("bounded committed source manifest required")
        encoded = json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if hashlib.sha256(encoded).hexdigest() != manifest.get("files_metadata_sha256"):
            raise ValueError("manifest metadata digest mismatch")
        total = 0
        for name, meta in files.items():
            safe_name(name)
            if name == "SOURCE_MANIFEST.json" or not isinstance(meta, dict):
                raise ValueError("invalid source manifest entry")
            if (
                type(meta.get("bytes")) is not int
                or not 0 <= meta["bytes"] <= MAX_BLOB
                or type(meta.get("mode")) is not int
                or not 0 <= meta["mode"] <= 0o777
                or not isinstance(meta.get("sha256"), str)
                or not SHA256.fullmatch(meta["sha256"])
            ):
                raise ValueError("invalid source manifest metadata: " + name)
            total += meta["bytes"]
        if total > MAX_TOTAL:
            raise ValueError("committed source exceeds total-byte bound")
        missing = sorted(set(files) - set(entries))
        if missing:
            raise ValueError("missing committed source paths: " + ", ".join(missing[:5]))
        extras = sorted(set(entries) - set(files) - {"SOURCE_MANIFEST.json"})
        if extras:
            raise ValueError("unlisted committed paths: " + ", ".join(extras[:5]))
        for name, meta in files.items():
            mode, oid = entries[name]
            expected = "100755" if meta["mode"] & 0o111 else "100644"
            if mode != expected:
                raise ValueError("Git executable-bit mismatch: " + name)
            content = objects.read(oid)
            if (
                len(content) != meta["bytes"]
                or hashlib.sha256(content).hexdigest() != meta["sha256"]
            ):
                raise ValueError("committed source identity mismatch: " + name)
    return {
        "schema": "openbot.git-source-verification/1",
        "revision": commit,
        "verified_files": len(files),
        "source_bytes": total,
        "git_entries": len(entries),
        "metadata_digest_verified": True,
        "git_executable_bits_verified": True,
        "private_filesystem_permissions_verified": False,
        "working_tree_verified": False,
        "signed_release": False,
        "scope": "local committed source only; no fetch, source execution, credentials, runtime or release acceptance",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT, help="local repository, not a URL")
    parser.add_argument("--ref", default="HEAD", help="locally available commit/ref; never fetches")
    args = parser.parse_args()
    try:
        print(json.dumps(check(args.repo, revision=args.ref), sort_keys=True))
        return 0
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        UnicodeError,
        subprocess.SubprocessError,
    ) as exc:
        print(json.dumps({"error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
