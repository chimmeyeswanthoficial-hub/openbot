"""Usable owned-sample reproducer, not a real human acceptance fixture."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REAL = pytest.mark.skipif(
    os.environ.get("OPENBOT_TEST_NAMESPACE") != "1",
    reason="explicit fixed namespace profile required",
)


def run(*args):
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts/owned-work-demo.py"), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )


def test_demo_requires_explicit_synthetic_review_and_new_cache_only_output(tmp_path):
    foreign = tmp_path / "must-not-write"
    assert run("--output", str(foreign)).returncode == 2
    assert run("--approve-synthetic-fixture", "--output", str(foreign)).returncode == 2
    assert not foreign.exists()
    existing = ROOT / ".cache" / ("preserve-demo-" + uuid.uuid4().hex)
    existing.mkdir(parents=True)
    canary = existing / "canary"
    canary.write_text("must remain")
    assert run("--approve-synthetic-fixture", "--output", str(existing)).returncode == 2
    assert canary.read_text() == "must remain" and list(existing.iterdir()) == [canary]


@REAL
@pytest.mark.parametrize(
    "fixture,failed",
    [("invoice-good-v1", 0), ("invoice-discount-defect-v1", 3), ("invoice-docs-defect-v1", 1)],
)
def test_actual_demo_exports_readback_and_leaves_artifact_for_human_review(fixture, failed):
    output = ROOT / ".cache" / ("owned-demo-test-" + uuid.uuid4().hex)
    reply = run("--approve-synthetic-fixture", "--fixture", fixture, "--output", str(output))
    assert reply.returncode == bool(failed), reply.stderr
    summary = json.loads(reply.stdout)
    assert summary["counts"] == {
        "passed": 7 - failed,
        "failed": failed,
        "skipped": 0,
        "collected": 7,
    }
    assert summary["test_sessions_revoked"] and not summary["qualified_human_acceptance"]
    assert not summary["paid_providers_enabled"] and not summary["server_started"]
    artifact = json.loads((output / "outbox.json").read_text())
    assert artifact["status"] == "review" and artifact["destination"] == "local-review:demo"
    assert artifact["sha256"] == summary["artifact_sha256"]
    assert json.loads((output / "report.json").read_text())["observed"]["doctest_executed"]
    assert "Qualified human review is **not recorded**" in (output / "REPORT.md").read_text()
