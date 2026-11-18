"""Actual bounded owned QA + doctest workflow. No customer code or external delivery."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import isolation
from qa_catalog import CASE_NAMES, FIXTURES
from work_store import WorkError, canonical, digest
from workbench import qa_packet


def run_owned_qa(fixture, *, run_id, brief, cancelled=lambda: False):
    if fixture not in FIXTURES:
        raise WorkError("only_bundled_owned_fixtures_are_supported")
    child = isolation.run_fixed("qa", {"fixture": fixture}, timeout_s=3, cancelled=cancelled)
    if child.terminal:
        return {
            "terminal": child.terminal,
            "child_exit_confirmed": True,
            "pid": child.pid,
            "external_delivery": False,
            "provider_used": False,
        }
    try:
        observed = json.loads(child.stdout.decode("utf-8"))
        source_sha = hashlib.sha256(FIXTURES[fixture].encode()).hexdigest()
        if (
            set(observed)
            != {
                "fixture",
                "source_sha256",
                "junit",
                "runner_output",
                "cases",
                "environment",
                "exit_code",
                "doctest_executed",
                "controls",
            }
            or observed["fixture"] != fixture
            or observed["source_sha256"] != source_sha
            or observed["exit_code"] != child.returncode
            or child.returncode not in {0, 1}
            or observed["doctest_executed"] is not True
            or sorted(c["case"] for c in observed["cases"]) != sorted(CASE_NAMES)
        ):
            raise WorkError("sample_run_provenance_mismatch")
        controls = observed["controls"]
        if (
            controls["status"] != {"CapEff": "0000000000000000", "NoNewPrivs": "1", "Seccomp": "2"}
            or controls["rlimits"]
            != {
                "CPU": [2, 2],
                "AS": [134217728, 134217728],
                "FSIZE": [0, 0],
                "NOFILE": [16, 16],
                "CORE": [0, 0],
                "NPROC": [1, 1],
            }
            or controls["host_environment_absent"] is not True
            or any(
                controls["namespaces"][n] == os.readlink("/proc/self/ns/" + n)
                for n in ("net", "mnt", "pid", "user", "uts", "ipc")
            )
        ):
            raise WorkError("missing_fixed_namespace_controls")
        packet = qa_packet(
            observed["junit"].encode(),
            brief_sha256=digest(brief),
            revision=source_sha,
            run_ref=run_id,
            exit_code=child.returncode,
            required_cases=tuple("owned_qa::" + name for name in CASE_NAMES),
        )
        if packet["counts"]["collected"] != len(CASE_NAMES):
            raise WorkError("incomplete_actual_assertions")
        findings = []
        for case in observed["cases"]:
            if case["outcome"] != "passed":
                findings.append(
                    {
                        "case": case["case"],
                        "severity": "proposed-high; human review required",
                        "expected": "bundled independent assertions and documented examples",
                        "actual": case["trace"],
                        "reproduction": {
                            "fixture": fixture,
                            "tool": "owned.qa",
                            "case": case["case"],
                        },
                        "regression_evidence_sha256": packet["junit_sha256"],
                    }
                )
        report = {
            "workflow": "owned-qa-docs-v1",
            "run_id": run_id,
            "fixture": fixture,
            "scope": "bundled first-party invoice example, not customer software",
            "brief": brief,
            "bounded_plan": [
                "review exact source and permission metadata",
                "run independent fixed assertions in a fresh deny-network namespace",
                "run actual documentation examples",
                "read back counts/digests and stage report for human review",
            ],
            "source_sha256": source_sha,
            "source": FIXTURES[fixture],
            "worker_sha256": hashlib.sha256(
                Path(__file__).with_name("qa_fixture_worker.py").read_bytes()
            ).hexdigest(),
            "process": {"pid": child.pid, "exit_code": child.returncode, "exit_confirmed": True},
            "observed": observed,
            "verification": packet,
            "findings": findings,
            "qa_passed": packet["evidence_status"] == "ready_for_review",
            "delivery": "local-review-only; separate exact artifact review required",
            "provider_used": False,
            "external_delivery": False,
            "limits": [
                "fixed owned samples only; no arbitrary uploaded code",
                "fixed namespace profile is not delegated cgroup/hostile-host certification",
                "human quality/rights/delivery review remains required; no specialist-parity claim",
            ],
        }
        if len(canonical(report).encode()) > 60000:
            raise WorkError("report_output_bound")
        # Independently parse the packaged serialization, not only in-memory counters.
        readback = json.loads(canonical(report))
        if readback["source_sha256"] != hashlib.sha256(readback["source"].encode()).hexdigest():
            raise WorkError("source_readback_mismatch")
        return readback
    except (ValueError, KeyError, TypeError, UnicodeError) as exc:
        raise WorkError("invalid_owned_qa_completion") from exc
