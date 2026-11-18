#!/usr/bin/env python3
"""Run one temporary real HTTPS fixture, CA negatives and actual browser workflow.

All children stop before exit. Kept private profile keys never enter the receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import socket
import ssl
import subprocess
import sys
import threading
import urllib.request
import uuid
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--client", type=Path, required=True)
    parser.add_argument("--browser-test", type=Path, required=True)
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    args.evidence.mkdir(parents=True, exist_ok=True)
    profile = args.cache / ("fixture-" + uuid.uuid4().hex)
    profile = profile.absolute()
    with socket.socket() as sock:
        sock.bind(("0.0.0.0", 0))
        port = sock.getsockname()[1]
    console = Path(__file__).with_name("control-local-fixture.py").resolve()
    common = [sys.executable, str(console)]
    init = subprocess.run(
        [
            *common,
            "init",
            "--profile",
            str(profile),
            "--port",
            str(port),
            "--client",
            str(args.client.resolve()),
            "--ack-local-synthetic",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    (args.evidence / "s08-fixture-init.json").write_text(init.stdout)
    log = (args.evidence / "s08-tls-server.log").open("w")
    proc = subprocess.Popen(
        [*common, "serve", "--profile", str(profile), "--ack-local-synthetic"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    ready = queue.Queue()

    def drain():
        for line in proc.stdout:
            log.write(line)
            log.flush()
            if "Uvicorn running on" in line:
                ready.put(True)

    thread = threading.Thread(target=drain, daemon=True)
    thread.start()
    checks = []
    try:
        ready.get(timeout=30)
        ca = profile / "tls-cert.pem"
        context = ssl.create_default_context(cafile=str(ca))
        url = f"https://localhost:{port}/api/v1/identity"
        with urllib.request.urlopen(url, context=context, timeout=5) as response:
            identity = json.load(response)
            checks.append(
                {
                    "name": "Actual TLS socket accepts explicitly trusted fixture CA",
                    "passed": response.status == 200 and identity["api_version"] == "1",
                }
            )
        try:
            urllib.request.urlopen(url, context=ssl.create_default_context(), timeout=5)
        except urllib.error.URLError:
            checks.append(
                {"name": "Untrusted fixture CA refused by default trust store", "passed": True}
            )
        else:
            raise AssertionError("Untrusted certificate was accepted")
        with socket.create_connection(("127.0.0.1", port), timeout=5) as raw:
            try:
                context.wrap_socket(raw, server_hostname="wrong-identity.invalid")
            except ssl.SSLCertVerificationError:
                checks.append(
                    {
                        "name": "Wrong server hostname refused with trusted fixture CA",
                        "passed": True,
                    }
                )
            else:
                raise AssertionError("Wrong TLS hostname accepted")
        with socket.create_connection(("127.0.0.1", port), timeout=5) as raw:
            raw.sendall(
                b"GET /api/v1/identity HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
            )
            reply = raw.recv(1024)
            assert b"200 OK" not in reply
            checks.append({"name": "Cleartext HTTP does not serve the TLS API", "passed": True})
        env = {
            **os.environ,
            "CONTROL_TEST_PROFILE": str(profile),
            "CONTROL_TEST_EVIDENCE": str(args.evidence.resolve()),
            "CONTROL_TEST_PYTHON": sys.executable,
            "CONTROL_TEST_CONSOLE": str(console),
        }
        node = subprocess.run(
            ["node", str(args.browser_test.resolve())],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
        )
        (args.evidence / "s08-browser.log").write_text(node.stdout)
        if node.returncode:
            raise RuntimeError("Browser proof failed: " + node.stdout[-2500:])
        print(node.stdout.strip())
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        thread.join(timeout=3)
        log.close()
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                stopped = False
        except OSError:
            stopped = True
        checks.append(
            {
                "name": "TLS fixture exited and listener stopped",
                "passed": stopped and proc.poll() is not None,
            }
        )
        receipt = {
            "schema": "openbot.local-tls-proof/1",
            "checks": checks,
            "certificate_sha256": hashlib.sha256(
                (profile / "tls-cert.pem").read_bytes()
            ).hexdigest(),
            "fixture_server_pid": proc.pid,
            "returncode": proc.returncode,
            "profile_private_keys_distributed": False,
            "platform_ca_native_acceptance": False,
            "native_device_evidence": False,
            "provider_started": False,
            "production_pairing": False,
        }
        (args.evidence / "s08-tls.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n"
        )
        assert stopped


if __name__ == "__main__":
    os.umask(0o077)
    main()
