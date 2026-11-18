"""Local source/build contracts. Static checks are not native runtime acceptance."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class SharedSourceTests(unittest.TestCase):
    def test_the_actual_gateway_and_ios_payloads_are_byte_identical_to_studio(self):
        page = (ROOT / "studio/web/index.html").read_bytes()
        for name in ("control/web/index.html", "control/native/ios/OpenBotControl/index.html"):
            self.assertEqual((ROOT / name).read_bytes(), page, name)

    def test_build_is_offline_deterministic_and_writes_only_the_explicit_payloads(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("studio/scripts", "studio/web", "control"):
                (root / name).mkdir(parents=True, exist_ok=True)
            for name in [
                "scripts/build-web.py",
                *[
                    "web/" + x
                    for x in (
                        "template.html",
                        "styles.css",
                        "finance-preview.js",
                        "finance-workspace.js",
                        "gateway-session.js",
                        "app.js",
                    )
                ],
            ]:
                shutil.copyfile(ROOT / "studio" / name, root / "studio" / name)
            subprocess.run(
                [sys.executable, str(root / "studio/scripts/build-web.py")],
                check=True,
                capture_output=True,
                env={
                    **os.environ,
                    "http_proxy": "http://127.0.0.1:9",
                    "https_proxy": "http://127.0.0.1:9",
                },
            )
            expected = (ROOT / "studio/web/index.html").read_bytes()
            self.assertEqual((root / "studio/web/index.html").read_bytes(), expected)
            self.assertEqual((root / "control/web/index.html").read_bytes(), expected)
            self.assertEqual(
                (root / "control/native/ios/OpenBotControl/index.html").read_bytes(), expected
            )

    def test_build_handles_crlf_input_canonicalizes_to_lf_and_preserves_expected_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("studio/scripts", "studio/web", "control"):
                (root / name).mkdir(parents=True, exist_ok=True)
            shutil.copyfile(
                ROOT / "studio/scripts/build-web.py", root / "studio/scripts/build-web.py"
            )
            for name in (
                "template.html",
                "styles.css",
                "finance-preview.js",
                "finance-workspace.js",
                "gateway-session.js",
                "app.js",
            ):
                content = (ROOT / "studio/web" / name).read_bytes().decode("utf-8")
                # Force CRLF newlines into the input assets
                crlf_content = content.replace("\r\n", "\n").replace("\n", "\r\n")
                (root / "studio/web" / name).write_bytes(crlf_content.encode("utf-8"))
            subprocess.run(
                [sys.executable, str(root / "studio/scripts/build-web.py")],
                check=True,
                capture_output=True,
                env={
                    **os.environ,
                    "http_proxy": "http://127.0.0.1:9",
                    "https_proxy": "http://127.0.0.1:9",
                },
            )
            expected = (ROOT / "studio/web/index.html").read_bytes()
            built = (root / "studio/web/index.html").read_bytes()
            self.assertEqual(built, expected)
            self.assertEqual(len(built), 127185)
            self.assertNotIn(b"\r\n", built)

    def test_light_mobile_css_and_no_external_assets_in_actual_built_html(self):
        page = (ROOT / "studio/web/index.html").read_text()
        self.assertIn('name="color-scheme" content="light"', page)
        self.assertIn("@media(max-width:760px)", page)
        self.assertIn(".workspace.show-thread", page)
        self.assertNotIn("<script src=", page)
        self.assertNotIn('<link rel="stylesheet"', page)
        self.assertNotIn('src="https://', page)
        self.assertNotIn('<script id="recorded-data"', page)

    def test_public_diagnostics_are_read_only_and_do_not_expose_device_keys(self):
        script = (ROOT / "studio/web/app.js").read_text()
        start = script.index("Object.defineProperty(window,'OpenBotWorkspace'")
        diagnostic = script[start:]
        self.assertIn("get connection(){return gateway.info();}", diagnostic)
        for name in ("gateway.propose", "gateway.taskAction", "privateKey", "get keys"):
            self.assertNotIn(name, diagnostic)

    def test_native_sources_select_light_chrome_without_weakening_tls_or_bridges(self):
        java = (
            ROOT / "control/native/android/src/dev/openbot/controlpreview/MainActivity.java"
        ).read_text()
        windows = (ROOT / "control/native/windows/main.cpp").read_text()
        swift = (ROOT / "control/native/ios/OpenBotControl/PreviewWebView.swift").read_text()
        theme = (ROOT / "control/native/android/res/values/styles.xml").read_text()
        self.assertIn("Theme.Material.Light.NoActionBar", theme)
        self.assertIn("Color.rgb(255, 255, 255)", java)
        self.assertIn("RGB(255, 255, 255)", windows)
        self.assertIn("UIColor.white", swift)
        self.assertIn(
            "<key>UIUserInterfaceStyle</key><string>Light</string>",
            (ROOT / "control/native/ios/OpenBotControl/Info.plist").read_text(),
        )
        self.assertIn(
            "preferredColorScheme(.light)",
            (ROOT / "control/native/ios/OpenBotControl/ControlApp.swift").read_text(),
        )
        for name in (
            "handler.proceed",
            "addJavascriptInterface",
            "setWebContentsDebuggingEnabled(true)",
        ):
            self.assertNotIn(name, java)
        self.assertIn("handler.cancel()", java)
        self.assertIn("put_IsWebMessageEnabled(FALSE)", windows)
        self.assertNotIn("addScriptMessageHandler", swift)
        self.assertIn("nonPersistent()", swift)
        for source in (java, windows, swift):
            self.assertIn("OpenBotNative/0.3.0", source)

    def test_native_lifecycle_paths_preserve_fresh_readback_requirements(self):
        for name in (
            "control/native/android/src/dev/openbot/controlpreview/MainActivity.java",
            "control/native/windows/main.cpp",
            "control/native/ios/OpenBotControl/PreviewWebView.swift",
        ):
            source = (ROOT / name).read_text()
            self.assertIn("openbotpause", source)
            self.assertIn("openbotresume", source)
        adapter = (ROOT / "studio/web/gateway-session.js").read_text()
        self.assertIn("non-exportable private key in renderer memory only", adapter)
        self.assertNotIn("localStorage", adapter)
        self.assertNotIn("sessionStorage", adapter)


if __name__ == "__main__":
    unittest.main()
