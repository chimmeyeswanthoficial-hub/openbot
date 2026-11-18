#!/usr/bin/env python3
"""Download/extract a reviewed Debian profile into an explicit cache, no install.

Requires Debian trixie amd64 and apt's authenticated repository metadata. The
runtime library receipt is host-specific, not a cross-host portability promise.
This build enables GPL; no FFmpeg binary is redistributed in the source handoff.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

PACKAGES = {
    "ffmpeg": (
        "7:7.1.5-0+deb13u1",
        "8669bc77e55393c14e0dd257ba9a916007cb6da0e1074c9b5e1d53812024f2af",
    ),
    "libavdevice61": (
        "7:7.1.5-0+deb13u1",
        "90a1b5e3256960a9297b9767b230da0ea29281acf9532cc08b0de785c3b901fe",
    ),
    "libcdio-paranoia2t64": (
        "10.2+2.0.2-1+b1",
        "8721c897d6f70d694d4b5f09e66ce00a98d236b2746664a8e27635532b7695b8",
    ),
    "libcdio-cdda2t64": (
        "10.2+2.0.2-1+b1",
        "3d6cb8220d4e67719bb84feb35022656e6b6ca3dec88e823906fc72b57c83e6f",
    ),
    "libcdio19t64": (
        "2.2.0-4.1~deb13u1",
        "bddfa8b7eca542379962152216d3414e999bca809a4a25543a193b4d1acc4ba1",
    ),
}


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    cache = args.cache.resolve()
    cache.mkdir(parents=True, exist_ok=True)
    for name, (version, expected) in PACKAGES.items():
        matches = list(cache.glob(name + "_*.deb"))
        if not matches:
            subprocess.run(["apt-get", "download", name + "=" + version], cwd=cache, check=True)
            matches = list(cache.glob(name + "_*.deb"))
        if len(matches) != 1 or sha(matches[0]) != expected:
            raise SystemExit("Refused package pin: " + name)
        subprocess.run(["dpkg-deb", "-x", str(matches[0]), str(cache / "ffmpeg")], check=True)
    library_path = str(cache / "ffmpeg/usr/lib/x86_64-linux-gnu")
    env = {**os.environ, "LD_LIBRARY_PATH": library_path}
    executables, libraries = {}, {}
    for name in ["ffmpeg", "ffprobe"]:
        path = cache / "ffmpeg/usr/bin" / name
        version = subprocess.check_output([str(path), "-version"], env=env, text=True)
        linkage = subprocess.check_output(["ldd", str(path)], env=env, text=True)
        if "not found" in linkage:
            raise SystemExit("Unresolved reviewed media dependency")
        for match in re.findall(r"(?:=> )?(/[^\s()]+)", linkage):
            lib = Path(match).resolve()
            libraries[str(lib)] = {"path": str(lib), "sha256": sha(lib)}
        executables[name] = {"path": str(path), "sha256": sha(path), "version": version}
    license_text = subprocess.check_output(
        [executables["ffmpeg"]["path"], "-L"], env=env, stderr=subprocess.DEVNULL, text=True
    )
    value = {
        "schema": "openbot.media-tools/1",
        "executables": executables,
        "libraries": list(libraries.values()),
        "library_path": library_path,
        "packages": {n: {"version": v, "sha256": s} for n, (v, s) in PACKAGES.items()},
        "license_output": license_text,
        "redistributes_ffmpeg": False,
        "security_certification": False,
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "receipt": str(args.receipt),
                "library_count": len(libraries),
                "version": executables["ffmpeg"]["version"].splitlines()[0],
            }
        )
    )


if __name__ == "__main__":
    main()
