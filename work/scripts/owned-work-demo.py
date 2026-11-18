#!/usr/bin/env python3
"""Explicit owned-fixture-only authenticated API demo; no listeners or providers.

Creates NEW disposable SQLite state and synthetic host-issued test sessions.
The --approve-synthetic-fixture flag acknowledges test-role review, not actual
human acceptance, pairing or permission for external/customer work.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / "services/sentinel"),
    str(ROOT / "services/gateway/src"),
    str(ROOT / "services/worker/src"),
]
from fastapi.testclient import TestClient  # noqa: E402
from qa_catalog import FIXTURES  # noqa: E402
from repository import Store  # noqa: E402
from work_service import WorkService, create_work_app  # noqa: E402
from work_store import WorkStore, canonical  # noqa: E402


def demo(output, fixture):
    cache = ROOT / ".cache"
    cache.mkdir(exist_ok=True)
    requested = Path(output).absolute()
    # No overlay or symlink traversal, even inside a cache-only demo directory.
    if (
        requested.exists()
        or requested.is_symlink()
        or any(p.is_symlink() for p in requested.parents)
    ):
        raise ValueError("output must be a new non-symlinked path")
    target = requested.resolve()
    if not target.is_relative_to(cache.resolve()) or target == cache.resolve():
        raise ValueError("output must be a NEW directory under this source tree .cache")
    target.mkdir(mode=0o700, parents=True, exist_ok=False)
    store = Store(str(target / "owned-fixture.sqlite3"))
    try:
        setup = WorkStore(store, initialize=True)
        setup.configure(
            "demo", {"run": 0, "company_day": 0, "company": 0, "venture_day": 0, "venture": 0}
        )
        issuer = WorkService(setup, enabled=True)
        agent = issuer.issue_session(
            actor="agent:qa",
            venture="demo",
            role="agent",
            initiator={"kind": "handoff", "id": "owned-sample-demonstration"},
        )
        owner = issuer.issue_session(
            actor="human:fixture_reviewer",
            venture="demo",
            role="owner",
            initiator={"kind": "person", "id": "synthetic-test-role-not-human-acceptance"},
        )
        service = WorkService(WorkStore(store), enabled=True)
        with TestClient(create_work_app(service)) as client:

            def request(method, path, token=agent, body=None):
                response = client.request(
                    method, path, headers={"Authorization": "Bearer " + token}, json=body
                )
                if response.status_code != 200:
                    raise RuntimeError("owned-fixture API refused: " + str(response.status_code))
                return response.json()

            task = request(
                "POST",
                "/v3/work/tasks",
                body={
                    "request_id": str(uuid.uuid4()),
                    "fixture": fixture,
                    "goal": "Inspect and reproduce this bundled first-party invoice example",
                    "acceptance": "Six independent unit tests plus real documentation examples; report defects honestly",
                    "rights_ref": "owned:first-party-seed",
                    "ai_use_approved": True,
                    "destination": "local-review",
                },
            )
            path = "/v3/work/tasks/" + task["id"]
            review = request(
                "POST", path + "/approve", token=owner, body={"digest": task["spec_digest"]}
            )
            if review != {"approved": True}:
                raise RuntimeError("exact synthetic fixture review was refused")
            completed = request("POST", path + "/execute")
            if completed["status"] != "completed":
                raise RuntimeError("owned fixture did not produce a verified report")
            artifact = request("GET", path + "/outbox")
            before = len(service.work.history(task["id"]))
            replay = request("POST", path + "/execute")
            if not replay.get("replayed") or len(service.work.history(task["id"])) != before:
                raise RuntimeError("same-ID replay contract failed")
            report = artifact["content"]
            for name, value in [
                ("report.json", report),
                ("task.json", completed),
                ("outbox.json", artifact),
                ("events.json", request("GET", path + "/events")),
                ("history.json", service.work.history(task["id"])),
            ]:
                (target / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
            (target / "owned-source.py").write_text(report["source"])
            counts = report["verification"]["counts"]
            text = [
                "# Owned QA/documentation report",
                "",
                "**Synthetic fixed-owned-fixture demo. No paid provider, listener, customer code or external delivery.**",
                "",
                "Fixture: `" + fixture + "`  ",
                "Run: `" + task["id"] + "`  ",
                "Artifact SHA-256: `" + artifact["sha256"] + "`  ",
                "Source SHA-256: `" + report["source_sha256"] + "`",
                "",
                f"Observed: **{counts['passed']} passed / {counts['failed']} failed / {counts['skipped']} skipped**.",
                "A completed task means a report was produced, not that the sample is defect-free.",
                "",
                "## Review boundary",
                "",
                "Plan approval used a synthetic test-role session. Qualified human review is **not recorded**.",
                "The scoped local outbox remains `review`; no artifact delivery approval or external adapter was enabled.",
                "Fresh namespace controls, actual test output and JUnit are in `report.json`.",
                "",
                "## Reproduce",
                "",
                "From this exact reconstructed source with the documented locked profile:",
                "",
                "```sh",
                "python scripts/owned-work-demo.py --approve-synthetic-fixture \\\n  --fixture "
                + fixture
                + " --output .cache/choose-a-NEW-review-directory",
                "```",
                "",
                "Good fixture exits 0. Discount defect exits 1 with 3 failed cases; docs defect exits 1 with 1 failed case.",
                "Unsupported isolation/output/provenance refuses instead of using a host fallback.",
                "",
                "## Actual per-case observations",
                "",
            ]
            for case in report["observed"]["cases"]:
                text += [
                    "### " + case["case"],
                    "",
                    "Outcome: **" + case["outcome"] + "**",
                    "",
                    "```text",
                    case["trace"] or "Independent assertion/example passed.",
                    "```",
                    "",
                ]
            text += [
                "## Limits",
                "",
                *["- " + limit for limit in report["limits"]],
                "",
                "Proposed defect severity is not qualified human judgment. This demo is not a public release.",
            ]
            (target / "REPORT.md").write_text("\n".join(text) + "\n")
            # Revoke both temporary grants; no reusable credential is printed or exported.
            issuer.revoke_session(agent)
            issuer.revoke_session(owner)
            summary = {
                "mode": "synthetic_owned_fixture",
                "fixture": fixture,
                "task_id": task["id"],
                "counts": counts,
                "qa_passed": report["qa_passed"],
                "artifact_sha256": artifact["sha256"],
                "report": str((target / "REPORT.md").relative_to(ROOT)),
                "outbox": "local_review_only",
                "same_id_replay_without_new_effect": True,
                "test_sessions_revoked": True,
                "qualified_human_acceptance": False,
                "paid_providers_enabled": False,
                "external_delivery": False,
                "server_started": False,
            }
            (target / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
            print(canonical(summary))
            return 0 if report["qa_passed"] else 1
    finally:
        store._conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approve-synthetic-fixture", action="store_true")
    parser.add_argument("--fixture", choices=sorted(FIXTURES), default="invoice-good-v1")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if not args.approve_synthetic_fixture:
        parser.error("explicit --approve-synthetic-fixture required; this is NOT real human review")
    try:
        return demo(args.output, args.fixture)
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(2, "owned fixture refused: " + str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
