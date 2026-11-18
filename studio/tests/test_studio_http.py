"""Real ephemeral HTTP fixture, only local stateless requests."""

from __future__ import annotations

import http.client
import json
import socket
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from studio import PreviewServer, make_handler


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        (cls.root / "web").mkdir()
        (cls.root / "web/index.html").write_text(
            '<!doctype html><h1>Local</h1><script>"use strict";</script>'
        )
        cls.archive = cls.root / "source.zip"
        cls.archive.write_bytes(b"fixed-test-bytes-not-an-actual-release")
        cls.server = PreviewServer(("127.0.0.1", 0), make_handler(cls.root, source_zip=cls.archive))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.temp.cleanup()

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        self.addCleanup(conn.close)
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        return response.status, dict(response.getheaders()), response.read()

    def post(self, path, obj, **headers):
        return self.request(
            "POST", path, json.dumps(obj).encode(), {"Content-Type": "application/json", **headers}
        )

    def test_status_never_advertises_a_provider_pc_or_account_as_running(self):
        status, headers, body = self.request("GET", "/api/status")
        self.assertEqual(status, 200)
        result = json.loads(body)
        self.assertEqual(result["accounts_connected"], 0)
        for key in [
            "model_connected",
            "public_writes_enabled",
            "vm_started",
            "private_store_exposed",
        ]:
            self.assertFalse(result[key])
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        self.assertNotIn("Set-Cookie", headers)

    def test_preview_is_embed_compatible_and_has_hashed_inline_script_csp(self):
        status, headers, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"<h1>Local", body)
        self.assertIn("'sha256-", headers["Content-Security-Policy"])
        self.assertNotIn("X-Frame-Options", headers)
        self.assertNotIn("frame-ancestors", headers["Content-Security-Policy"])
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_real_pure_companion_plan_roundtrip(self):
        status, _, body = self.post(
            "/api/companion-plan",
            {"name": "Scout", "role": "researcher", "provider": "xai", "ide_tools": ["t3_code"]},
        )
        self.assertEqual(status, 200)
        plan = json.loads(body)
        self.assertFalse(plan["vm_started"])
        self.assertEqual(len(plan["sha256"]), 64)
        self.assertEqual(plan["provider_requested"], "xai")
        self.assertEqual(plan["toolchain"][0]["status"], "requested_not_installed")

    def test_real_social_plan_uses_explicit_private_privacy(self):
        status, _, body = self.post(
            "/api/social-plan",
            {
                "draft": {
                    "platform": "youtube",
                    "text": "Draft",
                    "title": "Owned",
                    "media_kind": "video",
                    "asset_sha256": "",
                    "rights_ref": "",
                    "ai_disclosure": "needs_review",
                    "made_for_kids": "needs_review",
                },
                "history": [],
            },
        )
        self.assertEqual(status, 200)
        plan = json.loads(body)
        self.assertEqual(plan["metadata_preview"]["status"]["privacyStatus"], "private")
        self.assertIsNone(plan["transport_request"])
        self.assertFalse(plan["external_write_enabled"])

    def test_paths_and_queries_cannot_read_private_files(self):
        for path in [
            "/etc/passwd",
            "/../src/studio.py",
            "/web/index.html",
            "/api/status?token=hidden",
            "/%2e%2e/secret",
            "//evil.invalid/api/status",
        ]:
            with self.subTest(path=path):
                status, _, body = self.request("GET", path)
                self.assertEqual(status, 404)
                self.assertNotIn(b"root:", body)

    def test_no_execution_install_auth_or_posting_route_exists(self):
        for path in [
            "/api/run",
            "/api/publish",
            "/api/connect",
            "/api/install",
            "/api/companions",
            "/api/vm/start",
        ]:
            with self.subTest(path=path):
                self.assertEqual(self.post(path, {})[0], 405)

    def test_cross_origin_and_opaque_origin_requests_are_refused(self):
        for headers in [
            {"Origin": "https://evil.invalid"},
            {"Origin": "null"},
            {"Sec-Fetch-Site": "cross-site"},
        ]:
            with self.subTest(headers=headers):
                self.assertEqual(self.post("/api/companion-plan", {}, **headers)[0], 403)

    def test_preview_hostname_is_supported_but_arbitrary_dns_host_is_not(self):
        self.assertEqual(
            self.request("GET", "/api/status", headers={"Host": "4183-example.e2b.app"})[0], 200
        )
        for host in [
            "evil.invalid",
            "evil.e2b.app.evil.invalid",
            "evil@4183-example.e2b.app",
            "4183-example.e2b.app/evil",
        ]:
            with self.subTest(host=host):
                self.assertEqual(self.request("GET", "/api/status", headers={"Host": host})[0], 403)

    def test_json_contract_rejects_duplicate_keys_nan_and_unknown_fields(self):
        for raw in [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"provider":"xai","connected":true}']:
            with self.subTest(raw=raw):
                self.assertEqual(
                    self.request(
                        "POST", "/api/companion-plan", raw, {"Content-Type": "application/json"}
                    )[0],
                    422,
                )

    def test_http_body_limit_and_content_type(self):
        self.assertEqual(
            self.request(
                "POST", "/api/companion-plan", b"a" * 65537, {"Content-Type": "application/json"}
            )[0],
            413,
        )
        self.assertEqual(
            self.request("POST", "/api/companion-plan", b"{}", {"Content-Type": "text/plain"})[0],
            415,
        )

    def test_transfer_encoding_and_ambiguous_lengths_are_refused(self):
        for header in [
            b"Content-Length: 2\r\nContent-Length: 2\r\n",
            b"Transfer-Encoding: chunked\r\n",
        ]:
            with (
                self.subTest(header=header),
                socket.create_connection(("127.0.0.1", self.port), timeout=5) as conn,
            ):
                conn.sendall(
                    b"POST /api/companion-plan HTTP/1.0\r\nHost: localhost\r\nContent-Type: application/json\r\n"
                    + header
                    + b"\r\n{}"
                )
                result = conn.recv(1024)
                self.assertIn(b" 411 ", result.split(b"\r\n")[0])

    def test_download_is_exactly_the_fixed_public_archive_not_a_url_path(self):
        status, headers, body = self.request("GET", "/source.zip")
        self.assertEqual(status, 200)
        self.assertEqual(body, self.archive.read_bytes())
        self.assertEqual(headers["Content-Type"], "application/zip")
        self.assertIn("attachment;", headers["Content-Disposition"])
        self.assertEqual(self.request("GET", "/source.zip?path=/etc/passwd")[0], 404)

    def test_unneeded_methods_do_not_mutate_anything(self):
        for method in ["PUT", "DELETE", "PATCH", "OPTIONS"]:
            with self.subTest(method=method):
                self.assertEqual(self.request(method, "/api/companion-plan", b"{}")[0], 405)


if __name__ == "__main__":
    unittest.main()
