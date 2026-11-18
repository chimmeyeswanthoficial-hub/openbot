#!/usr/bin/env python3
"""Repackage the manifest-listed workspace and labeled test builds into a NEW ZIP."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("source_verifier", ROOT / "tools/verify-source.py")
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


def package(output):
    manifest_path, _ = VERIFY.safe_file(ROOT, "SOURCE_MANIFEST.json")
    manifest_raw = manifest_path.read_bytes()
    VERIFY.check()
    if manifest_path.read_bytes() != manifest_raw:
        raise ValueError("manifest changed during verification")
    target = Path(os.path.abspath(output))
    if any(p.is_symlink() for p in (target, *target.parents)):
        raise ValueError("linked output path refused")
    manifest = json.loads(manifest_raw)
    names = sorted([*manifest["files"], "SOURCE_MANIFEST.json"])
    # A single predictable root, no nested increment archives or source duplication.
    with (
        target.open("xb") as stream,
        zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive,
    ):
        for name in names:
            source, observed = VERIFY.safe_file(ROOT, name)
            item = zipfile.ZipInfo("OpenBot-Workspace/" + name, date_time=(2026, 1, 1, 0, 0, 0))
            item.create_system = 3
            mode = manifest["files"][name].get("mode", 0o644) if (os.name != "posix" and name in manifest["files"]) else (observed.st_mode & 0o777)
            item.external_attr = (0o100000 | mode) << 16
            item.compress_type = zipfile.ZIP_DEFLATED
            observed_hash = hashlib.sha256()
            count = 0
            with source.open("rb") as src, archive.open(item, "w", force_zip64=True) as dst:
                while chunk := src.read(1024 * 1024):
                    dst.write(chunk)
                    observed_hash.update(chunk)
                    count += len(chunk)
            expected = manifest["files"].get(name)
            if name == "SOURCE_MANIFEST.json":
                expected = {
                    "bytes": len(manifest_raw),
                    "sha256": hashlib.sha256(manifest_raw).hexdigest(),
                }
            if count != expected["bytes"] or observed_hash.hexdigest() != expected["sha256"]:
                raise ValueError("source changed while exporting: " + name)
    return {
        "archive": target.name,
        "bytes": target.stat().st_size,
        "sha256": VERIFY.digest(target),
        "files": len(names),
        "signed_release": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, required=True, help="new output filename; never overwrites"
    )
    args = parser.parse_args()
    try:
        print(json.dumps(package(args.output), sort_keys=True))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
