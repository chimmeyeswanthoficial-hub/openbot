#!/usr/bin/env python3
"""Fetch hash-pinned public SDK ZIPs into the build cache, never the backend tree.

No account login, provider activation, provisioning, upload, or SDK-license
acceptance command is performed. Review the SDKs' terms for your own use.
Hashes bind the exact HTTPS downloads used for this preview; they are not a
claim of independent vendor-signature authentication.
"""

import hashlib
import os
import stat
from pathlib import Path
from urllib.request import Request, urlopen
from zipfile import ZipFile

CACHE = Path(
    os.environ.get("OPENBOT_BUILD_CACHE", Path.home() / ".cache/openbot-control")
).resolve()
PACKAGES = [
    dict(
        name="platform-35_r02.zip",
        url="https://dl.google.com/android/repository/platform-35_r02.zip",
        size=64273788,
        sha256="0988cacad01b38a18a47bac14a0695f246bc76c1b06c0eeb8eb0dc825ab0c8e0",
        prefix="android-35/",
        output="android-sdk/platforms/android-35",
    ),
    dict(
        name="build-tools_r35_linux.zip",
        url="https://dl.google.com/android/repository/build-tools_r35_linux.zip",
        size=61958799,
        sha256="bd3a4966912eb8b30ed0d00b0cda6b6543b949d5ffe00bea54c04c81e1561d88",
        prefix="android-15/",
        output="android-sdk/build-tools/35.0.0",
    ),
    dict(
        name="webview2.1.0.2903.40.nupkg",
        url="https://api.nuget.org/v3-flatcontainer/microsoft.web.webview2/1.0.2903.40/microsoft.web.webview2.1.0.2903.40.nupkg",
        size=8769233,
        sha256="ef128016dd1e51c59178c827ed5b8aa3322c57afa8675d930f8109505542ad74",
        prefix="",
        output="webview2",
    ),
]


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    downloads = CACHE / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    for package in PACKAGES:
        archive = downloads / package["name"]
        if not archive.exists():
            partial = archive.with_suffix(archive.suffix + ".partial")
            # Exclusive creation: do not silently reuse or overwrite a partial download.
            with (
                partial.open("xb") as output,
                urlopen(
                    Request(
                        package["url"], headers={"User-Agent": "OpenBot-Control-local-build/0.1"}
                    ),
                    timeout=90,
                ) as response,
            ):
                total = 0
                while block := response.read(1024 * 1024):
                    total += len(block)
                    if total > package["size"]:
                        raise RuntimeError("Download exceeded its pinned size")
                    output.write(block)
            if partial.stat().st_size != package["size"] or digest(partial) != package["sha256"]:
                raise RuntimeError(f"Hash/size mismatch: {partial}. Not extracted.")
            partial.rename(archive)
        if archive.stat().st_size != package["size"] or digest(archive) != package["sha256"]:
            raise RuntimeError(f"Existing archive does not match pin: {archive}")
        destination = CACHE / package["output"]
        with ZipFile(archive) as zipped:
            for entry in zipped.infolist():
                if entry.is_dir() or not entry.filename.startswith(package["prefix"]):
                    continue
                relative = Path(entry.filename[len(package["prefix"]) :])
                if (
                    relative.is_absolute()
                    or ".." in relative.parts
                    or stat.S_ISLNK(entry.external_attr >> 16)
                ):
                    raise RuntimeError("Unsafe archive member")
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zipped.read(entry))
                target.chmod(((entry.external_attr >> 16) & 0o777) or 0o644)
        print("VERIFIED / EXTRACTED", archive.name, package["sha256"])
    print("ANDROID_HOME=" + str(CACHE / "android-sdk"))
    print("WEBVIEW2_SDK=" + str(CACHE / "webview2"))


if __name__ == "__main__":
    main()
