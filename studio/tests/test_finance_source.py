"""Check the actual offline build and attributed source export, not just UI mocks."""

import base64
import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from studio_core import clean_export  # noqa: E402


class FinanceSourceTests(unittest.TestCase):
    def test_actual_module_source_export_keeps_licence_and_exact_upstream_sources(self):
        files = json.loads((ROOT / "SOURCE_FILES.json").read_bytes())
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "new-source.zip"
            result = clean_export(ROOT, files, output)
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(result["files"], len(files) + 1)
                self.assertEqual(set(archive.namelist()), {*files, "EXPORT_MANIFEST.json"})
                notice = archive.read("third_party/openmuse/LICENSE")
                self.assertIn(b"Copyright (c) 2026 OpenMuse contributors", notice)
                self.assertIn(b"Permission is hereby granted", notice)
                provenance = json.loads(archive.read("third_party/openmuse/PROVENANCE.json"))
                self.assertEqual(hashlib.sha256(notice).hexdigest(), provenance["license_sha256"])
                for name, meta in provenance["upstream_files"].items():
                    raw = archive.read("third_party/openmuse/upstream/" + name)
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), meta["sha256"])
                    self.assertEqual(len(raw), meta["bytes"])
                for name in ("web/finance-preview.js", "web/index.html"):
                    raw = archive.read(name)
                    self.assertIn(b"Copyright (c) 2026 OpenMuse contributors", raw)
                    self.assertIn(b"Permission is hereby granted", raw)
                    self.assertIn(b'THE SOFTWARE IS PROVIDED "AS IS"', raw)

    def test_built_offline_page_matches_the_actual_ordered_assets_and_csp(self):
        web = ROOT / "web"
        script = "\n".join(
            (web / name).read_text()
            for name in (
                "finance-preview.js",
                "finance-workspace.js",
                "gateway-session.js",
                "app.js",
            )
        )
        style = (web / "styles.css").read_text()
        digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
        csp = (
            "default-src 'none'; script-src 'sha256-"
            + digest
            + "'; style-src 'unsafe-inline'; img-src data:; connect-src 'self'; "
            + "object-src 'none'; base-uri 'none'; form-action 'none'"
        )
        expected = (web / "template.html").read_text()
        for marker, content in [("__CSP__", csp), ("__STYLE__", style), ("__SCRIPT__", script)]:
            self.assertEqual(expected.count(marker), 1)
            expected = expected.replace(marker, content)
        self.assertEqual((web / "index.html").read_text(), expected)
        self.assertNotIn("<script src=", expected)


if __name__ == "__main__":
    unittest.main()
