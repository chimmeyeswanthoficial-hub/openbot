#!/usr/bin/env python3
"""Explicit local CLI and public, stateless planning preview. No runtime wiring."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from studio_core import (
    MAX_JSON,
    VERSION,
    BlueprintStore,
    PlanError,
    canonical,
    clean_export,
    companion_plan,
    decode_json,
    host_observation,
    load_json,
    social_plan,
)

PROJECT = Path(__file__).resolve().parents[1]


def make_handler(project: Path = PROJECT, *, source_zip: Path | None = None):
    """Only fixed public assets and pure planning. No arbitrary paths or stores."""
    page = (project / "web" / "index.html").read_bytes()
    scripts = re.findall(rb"<script>(.*?)</script>", page, flags=re.S)
    import base64

    script_hashes = " ".join(
        "'sha256-" + base64.b64encode(hashlib.sha256(script).digest()).decode() + "'"
        for script in scripts
    )
    csp = (
        "default-src 'none'; script-src "
        + script_hashes
        + "; style-src 'unsafe-inline'; img-src data:; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'"
    )
    # The explicitly selected download is read once, not chosen by URL or user input.
    download = source_zip.read_bytes() if source_zip is not None else None
    if download is not None and len(download) > 64 * 1024 * 1024:
        raise PlanError("preview_download_limit")
    status = {
        "schema": "openbot.studio-preview/1",
        "version": VERSION,
        "mode": "stateless_local_planning",
        "model_connected": False,
        "accounts_connected": 0,
        "public_writes_enabled": False,
        "vm_started": False,
        "ide_sessions_running": 0,
        "source_download_available": download is not None,
        "host": host_observation(),
        "private_store_exposed": False,
    }

    class Handler(BaseHTTPRequestHandler):
        server_version = "OpenBotStudio/0.3"
        sys_version = ""
        protocol_version = "HTTP/1.0"

        def log_message(self, _format, *_args):
            # No request body, query, draft, cookies, authorization or address logs.
            return

        def _respond(
            self, code, body, content_type="application/json; charset=utf-8", *, filename=None
        ):
            raw = canonical(body) + b"\n" if type(body) is dict else body
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", csp)
            self.send_header(
                "Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()"
            )
            self.send_header("Connection", "close")
            if filename:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(raw)
            self.close_connection = True

        def _path(self):
            parsed = urlsplit(self.path)
            if (
                parsed.scheme
                or parsed.netloc
                or parsed.query
                or parsed.fragment
                or not self.path.startswith("/")
            ):
                return None
            return parsed.path

        def _host_allowed(self):
            hosts = self.headers.get_all("Host", [])
            if len(hosts) != 1 or any(c in hosts[0] for c in " /\\@\r\n\t"):
                return False
            try:
                parsed = urlsplit("//" + hosts[0])
                host = parsed.hostname
                port = parsed.port
            except ValueError:
                return False
            return bool(
                host
                and (
                    host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
                    or host.endswith(".e2b.app")
                )
                and (port is None or 1 <= port <= 65535)
            )

        def do_GET(self):
            if not self._host_allowed():
                return self._respond(403, {"error": "preview_host_not_allowed"})
            path = self._path()
            if path in {"/", "/index.html"}:
                return self._respond(200, page, "text/html; charset=utf-8")
            if path == "/api/status":
                return self._respond(200, status)
            if path == "/source.zip" and download is not None:
                return self._respond(
                    200,
                    download,
                    "application/zip",
                    filename="OpenBot-Workspace-current-source.zip",
                )
            if path == "/favicon.ico":
                return self._respond(204, b"", "image/x-icon")
            return self._respond(404, {"error": "route_not_available"})

        def do_POST(self):
            if not self._host_allowed():
                return self._respond(403, {"error": "preview_host_not_allowed"})
            origin = self.headers.get("Origin")
            expected = {
                "http://" + self.headers.get("Host", ""),
                "https://" + self.headers.get("Host", ""),
            }
            if origin is not None and origin not in expected:
                return self._respond(403, {"error": "same_origin_required"})
            if self.headers.get("Sec-Fetch-Site", "same-origin") not in {"same-origin", "none"}:
                return self._respond(403, {"error": "same_origin_required"})
            path = self._path()
            if path not in {"/api/companion-plan", "/api/social-plan"}:
                return self._respond(405, {"error": "no_execution_or_publishing_route"})
            lengths = self.headers.get_all("Content-Length", [])
            if (
                self.headers.get("Transfer-Encoding")
                or len(lengths) != 1
                or not re.fullmatch(r"[0-9]{1,7}", lengths[0])
            ):
                return self._respond(411, {"error": "single_bounded_content_length_required"})
            size = int(lengths[0])
            if size > MAX_JSON:
                return self._respond(413, {"error": "json_byte_limit"})
            if self.headers.get("Content-Type", "").lower() not in {
                "application/json",
                "application/json; charset=utf-8",
            }:
                return self._respond(415, {"error": "json_content_type_required"})
            try:
                self.connection.settimeout(5)
                raw = self.rfile.read(size)
                if len(raw) != size:
                    raise PlanError("complete_body_required")
                request = decode_json(raw)
                if path == "/api/companion-plan":
                    plan = companion_plan(request)
                else:
                    if type(request) is not dict or set(request) != {"draft", "history"}:
                        raise PlanError("exact_draft_and_history_required")
                    plan = social_plan(request["draft"], history=request["history"])
                return self._respond(200, plan)
            except PlanError as exc:
                return self._respond(422, {"error": str(exc)})
            except (TimeoutError, OSError):
                return self._respond(408, {"error": "bounded_body_read_failed"})

        def do_PUT(self):
            return self._respond(405, {"error": "method_not_allowed"})

        do_DELETE = do_PUT
        do_PATCH = do_PUT
        do_OPTIONS = do_PUT

    return Handler


class PreviewServer(ThreadingHTTPServer):
    """Bounded development server; public planning only, not deployment software."""

    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 16

    def __init__(self, address, handler):
        self.slots = threading.BoundedSemaphore(12)
        super().__init__(address, handler)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            request.settimeout(5)
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("inspect-host", help="Observe binary presence; never certify or start a VM")
    init = commands.add_parser("init-store", help="Create one NEW 0700 local blueprint root")
    init.add_argument("--root", type=Path, required=True)
    create = commands.add_parser(
        "create-companion", help="Save a private blueprint; no VM or provider starts"
    )
    create.add_argument("--root", type=Path, required=True)
    create.add_argument("--request", type=Path, required=True)
    listing = commands.add_parser("list-companions", help="Read a local blueprint root")
    listing.add_argument("--root", type=Path, required=True)
    review = commands.add_parser(
        "review-social", help="Compute a draft-only policy checklist; never post"
    )
    review.add_argument("--request", type=Path, required=True)
    export = commands.add_parser(
        "export-source", help="Create a NEW source-only ZIP from SOURCE_FILES.json"
    )
    export.add_argument("--output", type=Path, required=True)
    serve = commands.add_parser(
        "serve", help="Public stateless preview; do not use for private production data"
    )
    serve.add_argument("--port", type=int, default=4183)
    serve.add_argument("--bind", default="0.0.0.0", choices=["0.0.0.0", "127.0.0.1"])
    serve.add_argument("--source-zip", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect-host":
            result = host_observation()
        elif args.command == "init-store":
            BlueprintStore(args.root, initialize=True)
            result = {"private_blueprint_store_created": True, "vm_started": False}
        elif args.command == "create-companion":
            result = BlueprintStore(args.root).create_companion(load_json(args.request))
        elif args.command == "list-companions":
            result = {
                "companions": BlueprintStore(args.root).list_companions(),
                "vm_started": False,
            }
        elif args.command == "review-social":
            result = social_plan(load_json(args.request))
        elif args.command == "export-source":
            result = clean_export(PROJECT, load_json(PROJECT / "SOURCE_FILES.json"), args.output)
        else:
            if not 1 <= args.port <= 65535:
                raise PlanError("valid_port_required")
            server = PreviewServer((args.bind, args.port), make_handler(source_zip=args.source_zip))
            print(
                f"OpenBot Studio preview listening on {args.bind}:{args.port}; public planning only; no private store, accounts, models, VMs or publishing.",
                flush=True,
            )
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
            return 0
        sys.stdout.buffer.write(canonical(result) + b"\n")
        return 0
    except (PlanError, OSError) as exc:
        code = str(exc) if isinstance(exc, PlanError) else "local_io_failed"
        sys.stderr.write(json.dumps({"error": code}) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
