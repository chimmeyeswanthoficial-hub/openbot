"""A real, zero-provider Bot HQ → independent Sentinel → bounded local report slice.

All state/input fixtures are disposable. These tests do NOT prove OS isolation or any
paid/model/browser execution path. The policy/ledger authority stays outside Bot HQ.
"""
from __future__ import annotations

import hashlib
import json
from unittest.mock import Mock

import hq_readiness as hq
import pytest
from repository import Store

REQUEST_ID = "90a22229-e876-4937-b683-265b3bdb0819"


@pytest.fixture()
def company(tmp_path):
    root = tmp_path / "company"
    (root / ".openbot/state").mkdir(parents=True)
    (root / "audit").mkdir()
    (root / "company").mkdir()
    (root / ".openbot/state/budget.json").write_text(json.dumps({
        "company_day_cap_usd": 0, "spent_today_usd": 0, "paused": True,
    }))
    (root / ".openbot/state/active_ventures.yaml").write_text(
        "ventures:\n  - slug: media-api\n    paused: true\n")
    (root / "audit/verification-current.json").write_text(json.dumps({
        "python": {"passed": 251, "skipped": 2, "failed": 0, "collected": 253},
        "scope": "historical fixture, not a new test result",
    }))
    (root / "company/hq-local-policy.json").write_text(json.dumps({
        "version": 1, "enabled": True, "egress_mode": "deny_all", "auto_spend_usd": 0,
        "allowed_actions": ["company.readiness"],
    }))
    return root


@pytest.fixture()
def state(tmp_path):
    path = tmp_path / "kernel"
    path.mkdir()
    return path


def request(action="company.readiness", **extra):
    return {"request_id": REQUEST_ID, "action": action, **extra}


def test_report_is_real_bounded_and_audited_before_reads(company, state, monkeypatch):
    original = hq.read_evidence
    seen = []

    def observed(root, rel, **kwargs):
        with hq.open_store(state / "sentinel.sqlite3") as store:
            rows = store.audit_tail()
        assert any(r["action"] == "file.read" and r["target"]["path"] == rel
                   and r["decision"] == "allow" for r in rows)
        seen.append(rel)
        return original(root, rel, **kwargs)

    monkeypatch.setattr(hq, "read_evidence", observed)
    result = hq.run_request(request(), root=company, state_dir=state)
    assert result["ok"] and result["executed"] and not result["replayed"]
    report = result["report"]
    assert report["providers_enabled"] is False
    assert report["cost_usd"] == 0
    assert report["snapshot"]["python"]["collected"] == 253
    assert report["snapshot"]["active_venture_count"] == 1
    assert set(seen) == set(hq.INPUTS)
    assert len(report["inputs"]) == 3
    for item in report["inputs"]:
        assert item["sha256"] == hashlib.sha256((company / item["path"]).read_bytes()).hexdigest()
    path = state / "reports" / f"{REQUEST_ID}.json"
    assert json.loads(path.read_text()) == report
    with hq.open_store(state / "sentinel.sqlite3") as store:
        rows = store.audit_tail()
        assert len(rows) >= 5
        assert all(r["cost_usd"] == 0 for r in rows)
        assert any(r["id"] == report["run_id"] and r["status"] == "ok" for r in store.runs())


@pytest.mark.parametrize("action", ["shell.exec", "http.request", "outbound.send", "money", "deploy"])
def test_disallowed_tools_are_audited_without_execution(company, state, action):
    result = hq.run_request(request(action), root=company, state_dir=state)
    assert not result["ok"] and not result["executed"]
    assert result["code"] == "hq.action_not_supported"
    assert not list((state / "reports").glob("*.json"))
    with hq.open_store(state / "sentinel.sqlite3") as store:
        assert store.audit_tail()[0]["decision"] == "deny"


@pytest.mark.parametrize("extra", [
    {"path": "../../.env"}, {"command": "touch /tmp/not-permitted"},
    {"url": "https://example.com"}, {"cost_usd": 1},
])
def test_client_cannot_add_targets_commands_urls_or_cost(company, state, extra):
    result = hq.run_request(request(**extra), root=company, state_dir=state)
    assert result["code"] == "hq.arguments_not_supported"
    assert not result["executed"]


@pytest.mark.parametrize("mutation", ["missing", "broken", "widened"])
def test_policy_is_required_and_cannot_be_widened_from_hq(company, state, mutation):
    policy = company / "company/hq-local-policy.json"
    if mutation == "missing":
        policy.unlink()
    elif mutation == "broken":
        policy.write_text("bad json")
    else:
        data = json.loads(policy.read_text())
        data["egress_mode"] = "allow_all"
        policy.write_text(json.dumps(data))
    result = hq.run_request(request(), root=company, state_dir=state)
    assert not result["executed"] and result["code"] == "hq.policy_unavailable"


def test_audit_failure_means_no_evidence_read(company, state, monkeypatch):
    read = Mock(side_effect=AssertionError("must not read before durable audit"))
    monkeypatch.setattr(hq, "read_evidence", read)
    monkeypatch.setattr(Store, "audit", Mock(side_effect=OSError("disk unavailable")))
    result = hq.run_request(request(), root=company, state_dir=state)
    assert not result["ok"] and not result["executed"]
    assert result["code"] == "hq.audit_unavailable"
    read.assert_not_called()


@pytest.mark.parametrize("request_id", ["../../escape", "", "A" * 200])
def test_request_id_never_becomes_an_arbitrary_path(company, state, request_id):
    result = hq.run_request({"request_id": request_id, "action": "company.readiness"},
                            root=company, state_dir=state)
    assert not result["ok"] and not result["executed"]
    assert result["code"] == "hq.invalid_request_id"
    assert not (state.parent / "escape.json").exists()


def test_input_symlink_is_refused(company, state, tmp_path):
    p = company / ".openbot/state/budget.json"
    p.unlink()
    secret = tmp_path / "outside"
    secret.write_text('{"company_day_cap_usd": 999}')
    p.symlink_to(secret)
    result = hq.run_request(request(), root=company, state_dir=state)
    assert not result["ok"] and result["code"] == "hq.evidence_unavailable"
    assert not (state / "reports" / f"{REQUEST_ID}.json").exists()


def test_oversized_evidence_is_refused(company, state):
    (company / "audit/verification-current.json").write_text(" " * (hq.MAX_INPUT_BYTES + 1))
    result = hq.run_request(request(), root=company, state_dir=state)
    assert not result["ok"] and result["code"] == "hq.evidence_unavailable"


def test_exact_replay_is_durable_and_does_not_repeat_execution(company, state, monkeypatch):
    first = hq.run_request(request(), root=company, state_dir=state)
    assert first["ok"]
    read = Mock(side_effect=AssertionError("a replay must not execute again"))
    monkeypatch.setattr(hq, "read_evidence", read)
    second = hq.run_request(request(), root=company, state_dir=state)
    assert second["ok"] and second["replayed"] and not second["executed"]
    assert first["report"] == second["report"]
    read.assert_not_called()


def test_request_id_cannot_replay_different_arguments(company, state):
    first = hq.run_request(request(), root=company, state_dir=state)
    assert first["ok"]
    result = hq.run_request(request("http.request"), root=company, state_dir=state)
    assert not result["ok"] and not result["executed"]


def test_interrupted_job_requires_reconciliation_not_automatic_rerun(company, state):
    (state / "markers").mkdir()
    (state / "markers" / f"{REQUEST_ID}.json").write_text('{}')
    result = hq.run_request(request(), root=company, state_dir=state)
    assert not result["ok"] and result["code"] == "hq.reconciliation_required"


def test_inconsistent_verification_counts_are_not_a_readiness_success(company, state):
    p = company / "audit/verification-current.json"
    p.write_text(json.dumps({"python": {"passed": 253, "skipped": 2, "failed": 0, "collected": 253}}))
    result = hq.run_request(request(), root=company, state_dir=state)
    assert not result["ok"] and result["code"] == "hq.evidence_unavailable"


def test_corrupted_completed_report_is_not_trusted_on_replay(company, state):
    first = hq.run_request(request(), root=company, state_dir=state)
    assert first["ok"]
    path = state / "reports" / f"{REQUEST_ID}.json"
    data = json.loads(path.read_text())
    data["snapshot"]["python"]["passed"] = 99999
    path.write_text(json.dumps(data))
    replay = hq.run_request(request(), root=company, state_dir=state)
    assert not replay["ok"] and replay["code"] == "hq.reconciliation_required"


def test_midrun_audit_failure_is_uncertain_and_cannot_be_auto_reexecuted(company, state, monkeypatch):
    original = Store.audit
    calls = []

    def failing_midrun(store, row):
        calls.append(row)
        if len(calls) == 3:
            raise OSError("audit disk failed after first input read")
        return original(store, row)

    monkeypatch.setattr(Store, "audit", failing_midrun)
    result = hq.run_request(request(), root=company, state_dir=state)
    assert not result["ok"] and result["code"] == "hq.audit_unavailable"
    assert result["outcome_uncertain"] is True
    assert (state / "markers" / f"{REQUEST_ID}.json").is_file()
    monkeypatch.setattr(Store, "audit", original)
    replay = hq.run_request(request(), root=company, state_dir=state)
    assert not replay["ok"] and replay["code"] == "hq.reconciliation_required"
