#!/usr/bin/env python3
"""Real local owned-media HTTP/lifecycle proof, with bounded synthetic files.

The child mode only instruments real process creation/cleanup; no media result is
mocked. Loopback media HTTP is separate from the TLS/device control plane. This is
not hostile-upload/cgroup acceptance. All fixture children exit before completion.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import io
import json
import os
import queue
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid
import wave
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def serve():
    sys.path.insert(0, str(ROOT / "services/media-api/src"))
    import ffmpeg_runner
    import media_app
    import uvicorn

    original = ffmpeg_runner.subprocess.Popen

    def capture(*args, **kwargs):
        proc = original(*args, **kwargs)
        command = args[0] if args else kwargs["args"]
        if len(command) > 3 and str(command[1]).endswith("media_worker.py"):
            print(
                "MEDIA_EVENT "
                + json.dumps({"kind": "child", "pid": proc.pid, "tool": Path(command[3]).name}),
                flush=True,
            )
        return proc

    ffmpeg_runner.subprocess.Popen = capture
    base = media_app.MediaEngine

    class RecordedEngine(base):
        def close(self):
            if getattr(self, "closed", True):
                return
            processes = list(self.receipts)
            directory = str(self.directory)
            super().close()
            print(
                "MEDIA_EVENT "
                + json.dumps(
                    {
                        "kind": "closed",
                        "directory": directory,
                        "removed": not Path(directory).exists(),
                        "processes": processes,
                    }
                ),
                flush=True,
            )

    media_app.MediaEngine = RecordedEngine
    uvicorn.run(
        media_app.app,
        host="0.0.0.0",
        port=int(os.environ["MEDIA_FIXTURE_PORT"]),
        proxy_headers=False,
        access_log=False,
        server_header=False,
        limit_concurrency=8,
    )


def make_wave(path, size):
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(192000)
        remaining = size
        while remaining:
            n = min(65536, remaining)
            handle.writeframesraw(b"\0" * n)
            remaining -= n


class Fixture:
    def __init__(self, profile, evidence, port, suffix):
        self.events = queue.Queue()
        self.log = (evidence / ("media-http-" + suffix + ".log")).open("w")
        ready = queue.Queue()
        env = {
            **os.environ,
            "MEDIA_API_ENABLE_EXPERIMENTAL": "1",
            "MEDIA_API_TOKEN": "synthetic-local-only-token",
            "MEDIA_SPOOL_ROOT": str(profile / "spool"),
            "MEDIA_FIXTURE_PORT": str(port),
            "MEDIA_TOOL_LOCK": str(profile / "media-tools.json"),
        }
        self.proc = subprocess.Popen(
            [sys.executable, __file__, "--serve"],
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        def drain():
            for line in self.proc.stdout:
                self.log.write(line)
                self.log.flush()
                if "Uvicorn running on" in line:
                    ready.put(True)
                if line.startswith("MEDIA_EVENT "):
                    self.events.put(json.loads(line[len("MEDIA_EVENT ") :]))

        self.thread = threading.Thread(target=drain, daemon=True)
        self.thread.start()
        ready.get(timeout=20)

    def event(self, kind, *, tool=None, timeout=8):
        deadline = time.monotonic() + timeout
        while True:
            event = self.events.get(timeout=max(0.01, deadline - time.monotonic()))
            if event["kind"] == kind and (tool is None or event.get("tool") == tool):
                return event
            if time.monotonic() > deadline:
                raise TimeoutError("Media event deadline")

    def clear(self):
        while True:
            try:
                self.events.get_nowait()
            except queue.Empty:
                return

    def stop(self):
        if self.proc.poll() is None:
            self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=3)
        self.thread.join(timeout=3)
        self.log.close()


def send_socket(port, source, *, fmt="mp3", partial=False):
    sock = socket.create_connection(("127.0.0.1", port), timeout=10)
    sock.settimeout(10)
    header = (
        f"POST /v1/audio?format={fmt} HTTP/1.1\r\nHost: localhost:{port}\r\n"
        f"X-Media-Token: synthetic-local-only-token\r\nContent-Length: {source.stat().st_size}\r\nConnection: close\r\n\r\n"
    )
    sock.sendall(header.encode())
    with source.open("rb") as handle:
        while block := handle.read(65536):
            sock.sendall(block)
            if partial:
                break
    return sock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    if args.serve:
        return serve()
    if not args.cache or not args.evidence:
        parser.error("Explicit cache/evidence paths required")
    import httpx

    cache = args.cache.resolve()
    evidence = args.evidence.resolve()
    cache.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)
    profile = cache / ("media-" + uuid.uuid4().hex)
    profile.mkdir(mode=0o700)
    (profile / "spool").mkdir(mode=0o700)
    marker = profile / "spool" / "unrelated-owner-marker"
    marker.write_text("must survive cleanup")
    shutil.copyfile(os.environ["MEDIA_TOOL_LOCK"], profile / "media-tools.json")
    large = profile / "owned-100MB.wav"
    make_wave(large, 100000000)
    small = profile / "owned-1MB.wav"
    make_wave(small, 1000000)
    with socket.socket() as sock:
        sock.bind(("0.0.0.0", 0))
        port = sock.getsockname()[1]
    checks = []
    receipts = []

    def check(name, ok):
        if not ok:
            raise AssertionError(name)
        checks.append({"name": name, "passed": True})

    headers = {"X-Media-Token": "synthetic-local-only-token"}
    client = httpx.Client(
        base_url=f"http://127.0.0.1:{port}", headers=headers, trust_env=False, timeout=15
    )
    fixture = Fixture(profile, evidence, port, "first")
    try:
        reply = client.post("/v1/audio?format=mp3", content=b"not a real file")
        check("Malformed input is 422 before output success", reply.status_code == 422)
        event = fixture.event("closed")
        receipts.append(event)
        check(
            "Malformed input process reaped and lease removed",
            event["removed"] and all(r["reaped"] for r in event["processes"]),
        )
        fixture.clear()
        reply = client.post(
            "/v1/audio", content=(b"\0" * 65536 for _ in range((260 * 1024 * 1024) // 65536 + 1))
        )
        check("Actual chunked oversized upload returns 413", reply.status_code == 413)
        event = fixture.event("closed")
        receipts.append(event)
        check(
            "Oversized spool removed without launching ffmpeg",
            event["removed"] and not event["processes"],
        )
        missing = profile / "media-tools.disabled"
        (profile / "media-tools.json").rename(missing)
        check(
            "Missing reviewed tools return 503",
            client.post("/v1/audio", content=b"not launched").status_code == 503,
        )
        missing.rename(profile / "media-tools.json")
        fixture.clear()
        sock = send_socket(port, large, partial=True)
        sock.close()
        event = fixture.event("closed")
        receipts.append(event)
        check("Upload disconnect removes partial input", event["removed"])
        fixture.clear()
        sock = send_socket(port, large)
        child = fixture.event("child", tool="ffmpeg")
        sock.close()
        event = fixture.event("closed")
        receipts.append(event)
        check(
            "Disconnect during actual FFmpeg cancels and reaps",
            event["removed"]
            and any(r["pid"] == child["pid"] and r["reaped"] for r in event["processes"]),
        )
        fixture.clear()
        sock = send_socket(port, large, fmt="wav")
        # Wait only for headers; then do not consume the 100 MB body. Real ASGI
        # backpressure must be bounded by the service's unchanged 20 second cap.
        start = time.monotonic()
        header = b""
        while b"\r\n\r\n" not in header:
            header += sock.recv(1)
        check("Slow consumer begins only after real output verification", b"200 OK" in header)
        event = fixture.event("closed", timeout=25)
        elapsed = time.monotonic() - start
        receipts.append(event)
        sock.close()
        check(
            "Real slow consumer lease expires within bounded 20s send lifetime",
            event["removed"] and 18 <= elapsed <= 24,
        )
        fixture.clear()
        # Become a subreaper so this test can observe AND reap the fixed child
        # when its supervisor is SIGKILLed. Not a production init guarantee.
        if ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) != 0:
            raise OSError("test subreaper unavailable")
        sock = send_socket(port, large)
        child = fixture.event("child", tool="ffmpeg")
        os.kill(fixture.proc.pid, signal.SIGKILL)
        fixture.proc.wait(timeout=5)
        sock.close()
        deadline = time.monotonic() + 5
        status = None
        while time.monotonic() < deadline:
            pid, result = os.waitpid(child["pid"], os.WNOHANG)
            if pid:
                status = result
                break
            threading.Event().wait(0.01)
        check(
            "Parent-death signal/race check kills fixed media child; test subreaper reaps",
            status is not None and not Path(f"/proc/{child['pid']}").exists(),
        )
        check(
            "Crash leaves an actual stale private spool to recover",
            bool(list((profile / "spool").glob("media-*"))),
        )
        fixture.stop()
        fixture = Fixture(profile, evidence, port, "restarted")
        check(
            "Startup removes abandoned media spool, not owner marker",
            not list((profile / "spool").glob("media-*")) and marker.exists(),
        )
        with small.open("rb") as handle:
            reply = client.post(
                "/v1/audio?format=mp3", content=iter(lambda: handle.read(65536), b"")
            )
        check(
            "Restarted service produces a nonempty real MP3",
            reply.status_code == 200 and len(reply.content) > 100,
        )
        event = fixture.event("closed")
        receipts.append(event)
        check(
            "Restart output is independently decoded and every process reaped",
            event["removed"]
            and len(event["processes"]) >= 4
            and all(r["reaped"] for r in event["processes"]),
        )
        fixture.clear()
        with small.open("rb") as handle:
            split = client.post(
                "/v1/split?segment_time=1&format=mp3", content=iter(lambda: handle.read(65536), b"")
            )
        check(
            "Real split endpoint returns an actual segment ZIP",
            split.status_code == 200 and split.headers["content-type"] == "application/zip",
        )
        with zipfile.ZipFile(io.BytesIO(split.content)) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            check(
                "At least two independently decoded segments actually delivered",
                len(manifest["segments"]) == 2
                and all(s["decode_readback"] for s in manifest["segments"]),
            )
            check(
                "Received segment bytes match read-back manifest digests",
                all(
                    hashlib.sha256(archive.read(s["name"])).hexdigest() == s["sha256"]
                    for s in manifest["segments"]
                ),
            )
        (evidence / "owned-segments.zip").write_bytes(split.content)
        (evidence / "owned-segments-manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        )
        event = fixture.event("closed")
        receipts.append(event)
        check(
            "Split response completes with every child reaped and spool removed",
            event["removed"] and all(r["reaped"] for r in event["processes"]),
        )
    finally:
        client.close()
        fixture.stop()
        large.unlink(missing_ok=True)
        small.unlink(missing_ok=True)
    check(
        "Owned marker remains and all job spools gone",
        marker.exists() and not list((profile / "spool").glob("media-*")),
    )
    result = {
        "schema": "openbot.media-lifecycle-proof/1",
        "checks": checks,
        "count": len(checks),
        "receipts": receipts,
        "customer_upload_security_accepted": False,
        "per_job_cgroup_available": False,
        "slow_consumer_seconds_observed": elapsed,
        "provider_started": False,
        "parent_death_note": "Fixed FFmpeg only; adopted child reaped by an explicit test subreaper. Not S09 hostile process-tree proof.",
        "server_exited": fixture.proc.poll() is not None,
        "unrelated_file_preserved": marker.exists(),
    }
    (evidence / "s06-http-lifecycle.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    print(
        json.dumps(
            {
                "passed": len(checks),
                "failed": 0,
                "slow_consumer_seconds": elapsed,
                "all_fixture_servers_stopped": True,
            }
        )
    )


if __name__ == "__main__":
    os.umask(0o077)
    main()
