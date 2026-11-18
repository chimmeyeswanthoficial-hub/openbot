"""Executable local-drill regression; never a production/witness acceptance."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/prove-operations.py"


def test_operations_drill_cli_rejects_existing_evidence_before_creating_cache(tmp_path):
    root = tmp_path / ".cache"
    root.mkdir()
    evidence = root / "existing"
    evidence.mkdir()
    (evidence / "marker").write_text("preserve")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--cache",
            str(root / "new-cache"),
            "--evidence",
            str(evidence),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=ROOT,
    )
    assert result.returncode != 0 and not (root / "new-cache").exists()
    assert (evidence / "marker").read_text() == "preserve"


def test_actual_operations_drill_survives_killed_event_users_and_serializes_measurements(tmp_path):
    if os.environ.get("OPENBOT_TEST_NAMESPACE") != "1":
        pytest.skip("explicit namespace opt-in required for actual drill")
    root = tmp_path / ".cache"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--cache",
            str(root / "private"),
            "--evidence",
            str(root / "evidence"),
        ],
        capture_output=True,
        text=True,
        timeout=25,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    report = json.loads((root / "evidence/operations-drill.json").read_bytes())
    assert report["synthetic"] is True and report["key_distributed"] is False
    assert (
        report["witnessed_operations_accepted"] is False
        and report["real_pilot_started"] is False
        and report["release_authorized"] is False
    )
    names = {c["name"] for c in report["checks"]}
    assert {
        "all_new_fixture_processes_stopped",
        "actual_sigkill_restore_before",
        "actual_sigkill_restore_after",
        "real_http_wrong_ack_not_delivery",
        "sigkilled_watchdog_restart_preserves_exact_outbox_id",
        "real_collector_durable_ack_clears_outbox",
    } <= names
    assert all(c["passed"] for c in report["checks"])
    assert type(report["facts"]["backup_microseconds"]) is int
    for c in report["checks"]:
        if c["name"] == "all_new_fixture_processes_stopped":
            for pid in c["pids"]:
                with pytest.raises(ProcessLookupError):
                    os.kill(pid, 0)
