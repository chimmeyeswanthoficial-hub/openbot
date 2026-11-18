#!/usr/bin/env python3
"""Package only reviewed local artifacts into a NEW output directory; no release.

Does not compile, sign, install, upload, deploy or read private build profiles.
Source/evidence backend reconstruction is handled by the sibling checkpoint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def archive(path, files):
    assert not path.exists()
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as result:
        for source, name in sorted(files, key=lambda pair: pair[1]):
            assert source.is_file() and not any(p.is_symlink() for p in (source, *source.parents))
            assert source.suffix.lower() not in {
                ".pem",
                ".p12",
                ".pk8",
                ".keystore",
                ".mobileprovision",
            }
            entry = zipfile.ZipInfo(
                name, (2026, 11, 10, 0, 0, 0)
            )  # fixed archive metadata, not a build-date claim
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = (stat.S_IFREG | stat.S_IMODE(source.stat().st_mode)) << 16
            result.writestr(
                entry, source.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9
            )
    with zipfile.ZipFile(path) as result:
        assert result.testzip() is None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.absolute()
    if out.exists() or any(p.is_symlink() for p in (out, *out.parents)):
        raise SystemExit("NEW non-symlinked output directory required")
    out.mkdir(parents=True)
    windows = ROOT / "releases/windows-x64"
    names = [
        "OpenBot-Control-Local-x64.exe",
        "WebView2Loader.dll",
        "WebView2-LICENSE.txt",
        "README-Windows.txt",
    ]
    archive(
        out / "OpenBot-Control-Windows-x64-LOCAL.zip",
        [(windows / name, "OpenBot-Control-Local/" + name) for name in names]
        + [
            (
                ROOT / "scripts/uninstall-local-preview.ps1",
                "OpenBot-Control-Local/scripts/uninstall-local-preview.ps1",
            )
        ],
    )
    (out / "OpenBot-Control-Android-LOCAL.apk").write_bytes(
        (ROOT / "releases/OpenBot-Control-Local-android.apk").read_bytes()
    )
    ios = ROOT / "native/ios"
    archive(
        out / "OpenBot-Control-iOS-SOURCE-ONLY.zip",
        [
            (p, "OpenBot-Control-iOS-source/" + p.relative_to(ROOT).as_posix())
            for p in ios.rglob("*")
            if p.is_file()
        ]
        + [
            (ROOT / "scripts/build-ios.sh", "OpenBot-Control-iOS-source/scripts/build-ios.sh"),
            (ROOT / "web/index.html", "OpenBot-Control-iOS-source/web/index.html"),
            (ROOT / "RELEASE_STATUS.md", "OpenBot-Control-iOS-source/RELEASE_STATUS.md"),
            (ROOT / "LICENSE", "OpenBot-Control-iOS-source/LICENSE"),
        ],
    )
    result = {
        "schema": "openbot.local-native-package-list/1",
        "artifacts": {
            p.name: {
                "bytes": p.stat().st_size,
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            }
            for p in sorted(out.iterdir())
        },
        "windows_unsigned": True,
        "android_demo_key_only": True,
        "ios_compiled": False,
        "native_launch_tested": False,
        "public_release_authorized": False,
        "archive_metadata_note": "ZIP timestamps are fixed for deterministic metadata, not claims of when builds ran.",
    }
    (out / "PACKAGE_LIST.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
