#!/usr/bin/env python3
"""Verify local binary/assets/tool/static-source facts. NEVER native launch proof."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import re
import struct
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def pe(path):
    data = path.read_bytes()
    assert data[:2] == b"MZ"
    offset = struct.unpack_from("<I", data, 0x3C)[0]
    assert data[offset : offset + 4] == b"PE\0\0"
    assert struct.unpack_from("<H", data, offset + 4)[0] == 0x8664
    optional = offset + 24
    assert struct.unpack_from("<H", data, optional)[0] == 0x20B
    return {
        "bytes": len(data),
        "machine": "amd64",
        "subsystem": struct.unpack_from("<H", data, optional + 68)[0],
        "dll_characteristics": struct.unpack_from("<H", data, optional + 70)[0],
        "certificate_directory": list(struct.unpack_from("<II", data, optional + 112 + 8 * 4)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--ios-zip", type=Path, required=True)
    args = parser.parse_args()
    checks = []
    commands = {}

    def check(name, ok, kind):
        if not ok:
            raise AssertionError(name)
        checks.append({"name": name, "passed": True, "class": kind})

    def command(name, argv):
        result = subprocess.run(argv, capture_output=True, text=True, check=True, timeout=30)
        commands[name] = {"argv": argv, "stdout": result.stdout, "stderr": result.stderr}
        return result.stdout + result.stderr

    html = (ROOT / "web/index.html").read_bytes()
    windows = ROOT / "releases/windows-x64"
    exe = windows / "OpenBot-Control-Local-x64.exe"
    loader = windows / "WebView2Loader.dll"
    windows_pe = pe(exe)
    check("Actual x64 PE GUI", windows_pe["subsystem"] == 2, "binary_structure")
    check(
        "Local Windows artifact is honestly unsigned",
        windows_pe["certificate_directory"] == [0, 0],
        "binary_structure",
    )
    check(
        "ASLR/NX/high-entropy flags set",
        windows_pe["dll_characteristics"] & 0x160 == 0x160,
        "binary_structure",
    )
    check("Exact reviewed shared UI is embedded in EXE", html in exe.read_bytes(), "asset_bytes")
    check(
        "x64 loader is the selected pinned SDK loader",
        pe(loader)["machine"] == "amd64"
        and sha(loader)
        == sha(Path(os.environ["WEBVIEW2_SDK"]) / "build/native/x64/WebView2Loader.dll"),
        "asset_bytes",
    )
    check(
        "Windows version resource identifies 0.3.0 local test build",
        "0.3.0-local".encode("utf-16le") in exe.read_bytes()
        and 'assemblyIdentity version="0.3.0.0"'
        in exe.read_bytes().decode("utf-8", errors="ignore"),
        "binary_structure",
    )
    check(
        "Studio and gateway payload bytes match",
        (ROOT.parent / "studio/web/index.html").read_bytes() == html,
        "asset_bytes",
    )
    native = (ROOT / "native/windows/main.cpp").read_text()
    check(
        "Windows source has explicit owner-origin confirmation and no native authority bridge",
        "selectServer" in native
        and "sameOrigin" in native
        and "MB_DEFBUTTON2" in native
        and "put_IsWebMessageEnabled(FALSE)" in native,
        "static_source",
    )
    check(
        "Windows per-monitor DPI path exists",
        "WM_DPICHANGED" in native
        and "PerMonitorV2" in (ROOT / "native/windows/app.manifest").read_text(),
        "static_source",
    )
    apk = ROOT / "releases/OpenBot-Control-Local-android.apk"
    bt = Path(os.environ["ANDROID_HOME"]) / "build-tools/35.0.0"
    with zipfile.ZipFile(apk) as archive:
        check(
            "Exact shared UI is embedded in APK",
            archive.read("assets/index.html") == html,
            "asset_bytes",
        )
        dex = archive.read("classes.dex")
        check(
            "Actual DEX contains compiled control Activity",
            dex[:4] == b"dex\n" and b"Ldev/openbot/controlpreview/MainActivity;" in dex,
            "binary_structure",
        )
        check(
            "Actual compiled Android manifest present",
            archive.read("AndroidManifest.xml")[:4] == b"\x03\x00\x08\x00",
            "binary_structure",
        )
    badging = command("apk_badging", [str(bt / "aapt"), "dump", "badging", str(apk)])
    check(
        "Compiled APK is package version 0.3.0-local / code 3",
        "versionCode='3'" in badging and "versionName='0.3.0-local'" in badging,
        "tool_output",
    )
    signature = command(
        "apk_signature", [str(bt / "apksigner"), "verify", "--verbose", "--print-certs", str(apk)]
    )
    check(
        "Actual Android v3 demo signature verifies",
        "Verified using v3 scheme (APK Signature Scheme v3): true" in signature
        and "Not a release key" in signature,
        "tool_output",
    )
    command("apk_alignment", [str(bt / "zipalign"), "-c", "-p", "4", str(apk)])
    check("Actual APK alignment passes", True, "tool_output")
    permission = command("apk_permissions", [str(bt / "aapt"), "dump", "permissions", str(apk)])
    check(
        "INTERNET is the only declared Android permission",
        re.findall(r"uses-permission: name='([^']+)'", permission)
        == ["android.permission.INTERNET"],
        "tool_output",
    )
    manifest = command(
        "apk_manifest", [str(bt / "aapt"), "dump", "xmltree", str(apk), "AndroidManifest.xml"]
    )
    check(
        "Android cleartext/backup/debuggable flags disabled",
        all(
            re.search(flag + r".*0x0", manifest)
            for flag in ["usesCleartextTraffic", "allowBackup", "debuggable"]
        ),
        "tool_output",
    )
    java = (ROOT / "native/android/src/dev/openbot/controlpreview/MainActivity.java").read_text()
    check(
        "Android source rejects TLS errors and arbitrary origins",
        "handler.cancel()" in java
        and "handler.proceed" not in java
        and "sameOrigin" in java
        and "addJavascriptInterface" not in java,
        "static_source",
    )
    check(
        "Android back/pause/resume are wired in source",
        all(x in java for x in ["openbotBack", "openbotpause", "openbotresume"]),
        "static_source",
    )
    ios = ROOT / "native/ios/OpenBotControl"
    info = plistlib.loads((ios / "Info.plist").read_bytes())
    privacy = plistlib.loads((ios / "PrivacyInfo.xcprivacy").read_bytes())
    check(
        "iOS plist templates parse without ATS cleartext exceptions",
        info["CFBundlePackageType"] == "APPL"
        and "NSAppTransportSecurity" not in info
        and info["UIUserInterfaceStyle"] == "Light",
        "static_source",
    )
    check(
        "iOS privacy template is nontracking, pending final owner review",
        privacy["NSPrivacyTracking"] is False,
        "static_source",
    )
    project = (ROOT / "native/ios/OpenBotControl.xcodeproj/project.pbxproj").read_text()
    check(
        "iOS project targets 0.3.0 / iOS 16, without a configured signing team",
        "MARKETING_VERSION = 0.3.0" in project
        and "IPHONEOS_DEPLOYMENT_TARGET = 16.0" in project
        and "DEVELOPMENT_TEAM" not in project,
        "static_source",
    )
    swift = (ios / "PreviewWebView.swift").read_text()
    check(
        "iOS source uses ephemeral exact-origin WebView, no native JS bridge",
        "nonPersistent()" in swift
        and "ignore-previous-rules" in swift
        and "addScriptMessageHandler" not in swift
        and "serverTrust" not in swift,
        "static_source",
    )
    check(
        "All three native sources select light chrome (static only)",
        "RGB(255, 255, 255)" in native
        and "Color.rgb(255, 255, 255)" in java
        and "preferredColorScheme(.light)" in (ios / "ControlApp.swift").read_text(),
        "static_source",
    )
    check(
        "iOS bundled offline UI matches shared source",
        (ios / "index.html").read_bytes() == html,
        "asset_bytes",
    )
    with zipfile.ZipFile(args.ios_zip) as archive:
        names = archive.namelist()
        check(
            "iOS deliverable is explicitly source only, not an IPA",
            any(n.endswith("ControlApp.swift") for n in names)
            and not any(n.endswith((".ipa", ".app/")) for n in names),
            "archive_structure",
        )
        check(
            "No private signing/provisioning credentials in iOS source ZIP",
            not any(
                n.endswith((".pem", ".p12", ".pk8", ".keystore", ".mobileprovision")) for n in names
            ),
            "archive_structure",
        )
    result = {
        "schema": "openbot.local-package-verification/1",
        "checks": checks,
        "count": len(checks),
        "commands": commands,
        "windows_pe": windows_pe,
        "artifacts": {
            str(p.relative_to(ROOT)): {"bytes": p.stat().st_size, "sha256": sha(p)}
            for p in [exe, loader, apk]
        },
        "native_launch_tests_performed": False,
        "ios_compiled": False,
        "release_signing_performed": False,
        "note": "Binary/tool/static facts only. No native runtime, installation, pairing or store acceptance follows.",
    }
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "passed": len(checks),
                "failed": 0,
                "native_launch_tested": False,
                "ios_compiled": False,
            }
        )
    )


if __name__ == "__main__":
    main()
