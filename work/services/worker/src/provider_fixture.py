"""Controllable LOOPBACK-ONLY synthetic provider for tests. Never a live account.

Runs only inside an explicit context manager and shuts down/joins on exit. Its
separate SQLite meter is synthetic evidence, NOT money/real-provider settlement.
"""

from __future__ import annotations

import json
import secrets
import socket
import sqlite3
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from sse_protocol import encode_event
from work_store import canonical, digest


class ProviderFixture:
    def __init__(self, path, *, mode="normal", max_minor=10):
        if mode not in {
            "normal",
            "duplicate",
            "gap",
            "bad_utf8",
            "oversize",
            "wrong_run",
            "drop",
            "slow",
            "trickle",
            "oversize_receipt",
            "malformed_receipt",
            "accept_disconnect",
            "unconfirmed_stop",
        }:
            raise ValueError("unknown fixture mode")
        self.path, self.mode, self.max_minor = str(path), mode, max_minor
        self.token = secrets.token_urlsafe(32)
        self.started = threading.Event()
        self.stop_event, self.done = threading.Event(), threading.Event()
        self.lock = threading.Lock()
        with sqlite3.connect(self.path) as db:
            db.execute(
                "CREATE TABLE requests(id TEXT PRIMARY KEY, request_digest TEXT, upper_minor INTEGER, amount_minor INTEGER, status TEXT, accept_count INTEGER, http_calls INTEGER)"
            )

    def row(self, task_id):
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM requests WHERE id=?", (task_id,)).fetchone()
            return dict(row) if row else None

    def accept(self, body):
        if (
            not isinstance(body, dict)
            or set(body) != {"id", "upper_minor", "prompt"}
            or not isinstance(body["id"], str)
            or not 1 <= len(body["id"]) <= 96
            or type(body["upper_minor"]) is not int
            or not 0 <= body["upper_minor"] <= self.max_minor
            or not isinstance(body["prompt"], str)
            or len(body["prompt"].encode()) > 2048
        ):
            raise ValueError("fixture cannot enforce requested bounds")
        with self.lock, sqlite3.connect(self.path) as db:
            row = db.execute(
                "SELECT request_digest FROM requests WHERE id=?", (body["id"],)
            ).fetchone()
            if row and row[0] != digest(body):
                raise ValueError("provider idempotency conflict")
            db.execute(
                "INSERT OR IGNORE INTO requests VALUES(?,?,?,?,?,1,0)",
                (
                    body["id"],
                    digest(body),
                    body["upper_minor"],
                    min(2, body["upper_minor"]),
                    "accepted",
                ),
            )
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE requests SET http_calls=http_calls+1 WHERE id=?", (body["id"],))
        self.started.set()

    def finish(self, task_id, status):
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE requests SET status=? WHERE id=?", (status, task_id))
        self.done.set()

    def events(self, task_id):
        common = {"runId": task_id, "threadId": "thread_" + task_id}
        return [
            {"type": kind, "seq": i + 1, **common, **extra}
            for i, (kind, extra) in enumerate(
                [
                    ("RUN_STARTED", {}),
                    ("TEXT_MESSAGE_START", {"messageId": task_id + ":message"}),
                    (
                        "TEXT_MESSAGE_CONTENT",
                        {
                            "messageId": task_id + ":message",
                            "delta": "Owned local fixture says hello ₹.",
                        },
                    ),
                    ("TEXT_MESSAGE_END", {"messageId": task_id + ":message"}),
                    ("RUN_FINISHED", {}),
                ]
            )
        ]

    def handler(self):
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass  # no tokens/headers/content in logs

            def reply(self, code, value):
                if self.path.startswith(("/usage/", "/stop/")) and code == 200:
                    if fixture.mode == "oversize_receipt":
                        value = {"untrusted_padding": "x" * 20000}
                    elif fixture.mode == "malformed_receipt":
                        value = ["not a usage or stop record"]
                data = canonical(value).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def authenticated(self):
                if not secrets.compare_digest(
                    self.headers.get("Authorization", ""), "Bearer " + fixture.token
                ):
                    self.reply(403, {"error": "fixture_auth_required"})
                    return False
                return True

            def do_GET(self):
                if not self.authenticated():
                    return
                if not self.path.startswith("/usage/") or "?" in self.path:
                    return self.reply(404, {})
                row = fixture.row(self.path[len("/usage/") :])
                if not row or row["status"] not in {"completed", "stopped"}:
                    return self.reply(409, {"usage_final": False})
                self.reply(
                    200,
                    {
                        "fixture": True,
                        "usage_final": True,
                        "receipt_id": "fixture:" + row["id"],
                        "id": row["id"],
                        "request_digest": row["request_digest"],
                        "amount_minor": row["amount_minor"],
                        "upper_minor": row["upper_minor"],
                        "status": row["status"],
                    },
                )

            def do_POST(self):
                if not self.authenticated():
                    return
                if self.path.startswith("/stop/") and "?" not in self.path:
                    task_id = self.path[len("/stop/") :]
                    if not fixture.row(task_id):
                        return self.reply(404, {})
                    fixture.stop_event.set()
                    if fixture.mode != "unconfirmed_stop":
                        fixture.done.wait(1)
                    row = fixture.row(task_id)
                    return self.reply(
                        200,
                        {
                            "id": task_id,
                            "stop_confirmed": row["status"] == "stopped",
                            "status": row["status"],
                            "fixture": True,
                        },
                    )
                if self.path != "/turn":
                    return self.reply(404, {})
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 1 <= length <= 4096:
                        raise ValueError("body bound")
                    body = json.loads(self.rfile.read(length))
                    if self.headers.get("Idempotency-Key") != body.get("id"):
                        raise ValueError("idempotency key required")
                    fixture.accept(body)
                except (ValueError, TypeError, KeyError):
                    return self.reply(422, {"error": "fixture_contract_refused"})
                task_id = body["id"]
                if fixture.mode == "accept_disconnect":
                    fixture.finish(task_id, "completed")
                    self.connection.shutdown(socket.SHUT_RDWR)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                frames = fixture.events(task_id)
                if fixture.mode == "wrong_run":
                    frames[0]["runId"] = "wforged"
                    frames[0]["threadId"] = "thread_wforged"
                if fixture.mode == "gap":
                    frames[1]["seq"] = 3
                try:
                    self.wfile.write(encode_event(frames[0]))
                    self.wfile.flush()
                    if fixture.mode == "trickle":
                        for byte in b": heartbeat\n\n" * 5:
                            if fixture.stop_event.wait(0.1):
                                return
                            self.wfile.write(bytes([byte]))
                            self.wfile.flush()
                        return
                    if fixture.mode in {"slow", "unconfirmed_stop"}:
                        until = time.monotonic() + 1.5
                        while time.monotonic() < until:
                            if fixture.mode == "unconfirmed_stop":
                                time.sleep(0.02)
                            elif fixture.stop_event.wait(0.02):
                                fixture.finish(task_id, "stopped")
                                return
                    if fixture.mode == "bad_utf8":
                        self.wfile.write(b"\xff\n\n")
                    elif fixture.mode == "oversize":
                        self.wfile.write(b"data: " + b"x" * 40000 + b"\n\n")
                    else:
                        for frame in frames[1:]:
                            self.wfile.write(encode_event(frame))
                            self.wfile.flush()
                            if fixture.mode == "duplicate" and frame["seq"] == 3:
                                self.wfile.write(encode_event(frame))
                                self.wfile.flush()
                            if fixture.mode == "drop" and frame["seq"] == 2:
                                return
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    if fixture.mode != "drop" and fixture.row(task_id)["status"] != "stopped":
                        fixture.finish(task_id, "completed")

        return Handler


@contextmanager
def serve_fixture(path, *, mode="normal", max_minor=10):
    fixture = ProviderFixture(path, mode=mode, max_minor=max_minor)
    server = ThreadingHTTPServer(("127.0.0.1", 0), fixture.handler())
    server.daemon_threads = False
    server.timeout = 2
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    fixture.endpoint = "http://127.0.0.1:" + str(server.server_port)
    thread.start()
    try:
        yield fixture
    finally:
        fixture.stop_event.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        if thread.is_alive():
            raise RuntimeError("fixture did not stop")
