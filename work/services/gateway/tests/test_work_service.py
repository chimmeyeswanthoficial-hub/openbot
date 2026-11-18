"""Authenticated API negatives + real owned workflow on SQLite and restricted PG.

Owner-role sessions here are test fixtures, not actual human product acceptance.
"""

from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from work_service import WorkService, create_work_app
from work_store import WorkError

REAL = pytest.mark.skipif(
    os.environ.get("OPENBOT_TEST_NAMESPACE") != "1",
    reason="explicit fixed namespace profile required",
)


def intake(fixture="invoice-good-v1"):
    return {
        "request_id": str(uuid.uuid4()),
        "fixture": fixture,
        "goal": "Validate the owned invoice sample",
        "acceptance": "Independent assertions and documentation examples; report any defect",
        "rights_ref": "owned:first-party-seed",
        "ai_use_approved": True,
        "destination": "local-review",
    }


@pytest.fixture
def api(durable_backend):
    b = durable_backend
    issuer = WorkService(b.provision, enabled=True)
    tokens = {}
    for name, actor, venture, role in [
        ("agent", "agent:qa", "demo", "agent"),
        ("owner", "human:fixture_reviewer", "demo", "owner"),
        ("other", "human:other_reviewer", "other", "owner"),
        ("peer", "agent:peer", "demo", "agent"),
        ("viewer", "human:viewer", "demo", "viewer"),
    ]:
        tokens[name] = issuer.issue_session(
            actor=actor,
            venture=venture,
            role=role,
            initiator={
                "kind": "person" if role in {"owner", "viewer"} else "handoff",
                "id": "owned-sample",
            },
            ttl=3600,
        )
    service = WorkService(b.work, enabled=True)
    client = TestClient(create_work_app(service))
    return b, issuer, service, client, tokens


def headers(tokens, name="agent"):
    return {"Authorization": "Bearer " + tokens[name]}


def prepare(api, fixture="invoice-good-v1"):
    _b, _issuer, _service, client, tokens = api
    response = client.post("/v3/work/tasks", json=intake(fixture), headers=headers(tokens))
    assert response.status_code == 200, response.text
    return response.json()


def approve(api, row):
    _b, _issuer, _service, client, tokens = api
    reply = client.post(
        "/v3/work/tasks/" + row["id"] + "/approve",
        json={"digest": row["spec_digest"]},
        headers=headers(tokens, "owner"),
    )
    assert reply.status_code == 200 and reply.json()["approved"], reply.text


def test_default_off_app_mounts_no_work_routes(api):
    b, *_ = api
    client = TestClient(create_work_app(WorkService(b.work)))
    assert client.get("/v3/work/tasks").status_code == 404
    assert client.post("/v3/work/tasks", json=intake()).status_code == 404


@pytest.mark.parametrize(
    "field",
    [
        "actor",
        "venture",
        "owner",
        "role",
        "upper_minor",
        "budget_usd",
        "program",
        "principal",
        "tool",
    ],
)
def test_json_cannot_supply_authority_or_expand_the_tool_boundary(api, field):
    _b, _issuer, _service, c, t = api
    body = intake()
    body[field] = "human:owner"
    response = c.post("/v3/work/tasks", json=body, headers=headers(t))
    assert response.status_code == 422
    assert response.json() == {"detail": "invalid_work_request"}
    assert c.get("/v3/work/tasks", headers=headers(t)).json() == []


@pytest.mark.parametrize(
    "operation",
    ["read", "list", "approve", "execute", "cancel", "outbox", "events", "outbox_approve"],
)
def test_every_read_review_cancel_and_effect_requires_real_session(api, operation):
    _b, _issuer, _service, c, _t = api
    path = "/v3/work/tasks/fake"
    if operation == "read":
        response = c.get(path)
    elif operation == "list":
        response = c.get("/v3/work/tasks")
    elif operation in {"outbox", "events"}:
        response = c.get(path + "/" + operation)
    else:
        suffix = {"outbox_approve": "outbox/approve"}.get(operation, operation)
        response = c.post(
            path + "/" + suffix, json={"digest": "a" * 64} if "approve" in operation else None
        )
    assert response.status_code == 401


def test_forged_or_expired_credentials_never_become_owner(api):
    b, _issuer, _service, c, t = api
    assert (
        c.get(
            "/v3/work/tasks",
            headers={"Authorization": "Bearer " + "a" * 43, "X-Actor": "human:owner"},
        ).status_code
        == 403
    )
    b.clock[0] += 3601
    assert c.post("/v3/work/tasks", json=intake(), headers=headers(t, "owner")).status_code == 403


def test_cross_venture_and_peer_agent_cannot_read_approve_or_cancel(api):
    _b, _issuer, _service, c, t = api
    row = prepare(api)
    for name in ["other", "peer"]:
        assert c.get("/v3/work/tasks/" + row["id"], headers=headers(t, name)).status_code == 403
        assert (
            c.post("/v3/work/tasks/" + row["id"] + "/cancel", headers=headers(t, name)).status_code
            == 403
        )
        assert (
            c.post(
                "/v3/work/tasks/" + row["id"] + "/approve",
                json={"digest": row["spec_digest"]},
                headers=headers(t, name),
            ).status_code
            == 403
        )
    assert c.get("/v3/work/tasks/" + row["id"], headers=headers(t, "viewer")).status_code == 200
    assert (
        c.post("/v3/work/tasks/" + row["id"] + "/execute", headers=headers(t, "viewer")).status_code
        == 403
    )


def test_approval_is_exact_owner_only_once_and_never_ttl_auto_approve(api):
    b, _issuer, _service, c, t = api
    row = prepare(api)
    path = "/v3/work/tasks/" + row["id"]
    assert c.post(path + "/execute", headers=headers(t)).json()["status"] == "review"
    assert (
        c.post(
            path + "/approve", headers=headers(t), json={"digest": row["spec_digest"]}
        ).status_code
        == 403
    )
    assert not c.post(
        path + "/approve", headers=headers(t, "owner"), json={"digest": "a" * 64}
    ).json()["approved"]
    approve(api, row)
    assert not c.post(
        path + "/approve", headers=headers(t, "owner"), json={"digest": row["spec_digest"]}
    ).json()["approved"]
    assert b.work.get(row["id"])["attempted"] == 0


@pytest.mark.parametrize(
    "reason", ["review_expired", "agent_revoked", "reviewer_revoked", "changed_implementation"]
)
def test_changed_or_revoked_authority_cannot_reach_an_effect(api, reason):
    b, issuer, service, c, t = api
    calls = []
    service._invoke = lambda _row: calls.append("effect") or {"negative_test_double": True}
    row = prepare(api)
    if reason == "review_expired":
        assert service.approve(t["owner"], row["id"], row["spec_digest"], ttl=1)
        b.clock[0] += 2
    else:
        approve(api, row)
    if reason == "agent_revoked":
        issuer.revoke_session(t["agent"])
    elif reason == "reviewer_revoked":
        issuer.revoke_session(t["owner"])
    elif reason == "changed_implementation":
        service._invoke = lambda _row: calls.append("changed-effect") or {}
    actor = "owner" if reason == "agent_revoked" else "agent"
    response = c.post("/v3/work/tasks/" + row["id"] + "/execute", headers=headers(t, actor))
    assert response.status_code in {200, 409}
    assert not calls and b.work.get(row["id"])["attempted"] == 0
    assert b.work.get(row["id"])["status"] == "blocked"


def test_revocation_between_claim_and_effect_is_rechecked_in_transaction(api, monkeypatch):
    b, issuer, service, c, t = api
    calls = []
    service._invoke = lambda _row: calls.append("effect") or {}
    row = prepare(api)
    approve(api, row)
    original = b.work.before_effect

    def revoke_then_check(*args, **kwargs):
        issuer.revoke_session(t["agent"])
        return original(*args, **kwargs)

    monkeypatch.setattr(b.work, "before_effect", revoke_then_check)
    assert (
        c.post("/v3/work/tasks/" + row["id"] + "/execute", headers=headers(t, "owner")).status_code
        == 200
    )
    assert not calls and b.work.get(row["id"])["attempted"] == 0


@pytest.mark.parametrize(
    "verdict", [{"effect": "surprise", "rule": "bad"}, None, {"effect": "allow"}]
)
def test_unknown_policy_verdict_is_denied_not_default_allowed(api, verdict):
    b, _issuer, service, _c, t = api
    service.policy = lambda _plan: verdict
    row = service.prepare(t["agent"], intake())
    assert row["status"] == "denied" and b.work.get(row["id"])["attempted"] == 0


def test_rights_and_ai_use_questions_do_not_grant_execution(api):
    b, _issuer, service, _c, t = api
    body = intake()
    body["rights_ref"] = "unknown"
    body["ai_use_approved"] = False
    response = service.prepare(t["agent"], body)
    assert response["status"] == "clarify" and len(response["questions"]) == 2
    assert b.work.list("demo") == []


def test_changed_draft_cannot_replace_a_previously_reviewed_task(api):
    b, _issuer, _service, c, t = api
    body = intake()
    response = c.post("/v3/work/tasks", json=body, headers=headers(t))
    row = response.json()
    approve(api, row)
    body["fixture"] = "invoice-discount-defect-v1"
    assert c.post("/v3/work/tasks", json=body, headers=headers(t)).status_code == 409
    assert b.work.get(row["id"])["plan"]["intake"]["fixture"] == "invoice-good-v1"


def test_missing_audit_persistence_produces_no_tool_execution(api):
    b, _issuer, service, c, t = api
    calls = []
    service._invoke = lambda _row: calls.append("effect") or {}
    row = prepare(api)
    approve(api, row)
    if b.kind == "pg":
        from psycopg2 import sql

        with b.admin.cursor() as cur:
            cur.execute(
                sql.SQL("REVOKE INSERT ON {}.audit FROM {}").format(
                    sql.Identifier(b.schema), sql.Identifier(b.role)
                )
            )
    else:
        b.owner._conn.execute(
            "CREATE TRIGGER audit_down BEFORE INSERT ON audit BEGIN SELECT RAISE(ABORT,'synthetic unavailable audit'); END"
        )
        b.owner._conn.commit()
    response = c.post("/v3/work/tasks/" + row["id"] + "/execute", headers=headers(t))
    assert response.status_code == 503
    assert not calls and b.work.get(row["id"])["attempted"] == 0


@pytest.mark.parametrize(
    "fixture,failures",
    [("invoice-good-v1", 0), ("invoice-discount-defect-v1", 3), ("invoice-docs-defect-v1", 1)],
)
@REAL
def test_real_owned_qa_docs_to_verified_artifact_and_review_queue(api, fixture, failures):
    b, _issuer, _service, c, t = api
    row = prepare(api, fixture)
    approve(api, row)
    path = "/v3/work/tasks/" + row["id"]
    response = c.post(path + "/execute", headers=headers(t))
    assert response.status_code == 200, response.text
    result = response.json()
    assert (
        result["status"] == "completed"
    )  # report produced, NOT an assertion the tested sample is correct
    report = result["result"]
    assert report["process"]["exit_confirmed"] and report["process"]["exit_code"] == bool(failures)
    assert report["verification"]["counts"] == {
        "passed": 7 - failures,
        "failed": failures,
        "skipped": 0,
        "collected": 7,
    }
    assert report["observed"]["doctest_executed"] and report["qa_passed"] == (failures == 0)
    assert len(report["findings"]) == failures
    out = c.get(path + "/outbox", headers=headers(t)).json()
    assert out["status"] == "review" and out["external_delivery"] is False
    assert (
        c.post(
            path + "/outbox/approve", headers=headers(t), json={"digest": out["sha256"]}
        ).status_code
        == 403
    )
    assert not c.post(
        path + "/outbox/approve", headers=headers(t, "owner"), json={"digest": "0" * 64}
    ).json()["approved_local_only"]
    assert c.post(
        path + "/outbox/approve", headers=headers(t, "owner"), json={"digest": out["sha256"]}
    ).json()["approved_local_only"]
    assert c.get(path + "/outbox", headers=headers(t)).json()["status"] == "ready_local"
    before = len(b.work.history(row["id"]))
    assert c.post(path + "/execute", headers=headers(t)).json()["replayed"]
    assert len(b.work.history(row["id"])) == before
    assert len(c.get(path + "/events?after=2", headers=headers(t)).json()) == 5
    assert b.work.get(row["id"])["initiator"]["kind"] == "handoff"


@REAL
def test_two_concurrent_api_calls_execute_real_owned_sample_once(api):
    b, _issuer, _service, c, t = api
    row = prepare(api)
    approve(api, row)

    def call():
        with TestClient(c.app) as client:
            response = client.post("/v3/work/tasks/" + row["id"] + "/execute", headers=headers(t))
            assert response.status_code == 200, (response.status_code, response.text)
            return response.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda _: call(), range(2)))
    assert any(r["status"] == "completed" for r in replies)
    assert sum(r["kind"] == "effect_authorized" for r in b.work.history(row["id"])) == 1
    assert len(b.work.events(row["id"])) == 7
    assert b.work.get(row["id"])["result"]["verification"]["counts"]["passed"] == 7


def test_cancelled_unattempted_work_and_alternate_routes_never_execute(api):
    b, _issuer, _service, c, t = api
    row = prepare(api)
    assert c.post("/v3/work/tasks/" + row["id"] + "/cancel", headers=headers(t)).json()["requested"]
    assert (
        c.post("/v3/work/tasks/" + row["id"] + "/execute", headers=headers(t)).json()["status"]
        == "cancelled"
    )
    assert b.work.get(row["id"])["attempted"] == 0
    for path in ["/v1/decide", "/shell", "/v3/work/tool", "/v3/work/sessions", "/v3/work/provider"]:
        assert c.post(path, headers=headers(t), json={"actor": "human:owner"}).status_code == 404


def test_oversized_and_invalid_requests_do_not_echo_credentials(api):
    _b, _issuer, _service, c, t = api
    secret = "sk-" + ("x" * 32)
    body = intake()
    body["goal"] = secret
    response = c.post("/v3/work/tasks", headers=headers(t), json=body)
    assert response.status_code == 409 and secret not in response.text
    body["goal"] = "x" * 20000
    response = c.post("/v3/work/tasks", headers=headers(t), json=body)
    assert response.status_code == 413


@REAL
def test_corrupted_outbox_is_not_relabelled_verified(api):
    b, _issuer, service, c, t = api
    row = prepare(api)
    approve(api, row)
    assert (
        c.post("/v3/work/tasks/" + row["id"] + "/execute", headers=headers(t)).json()["status"]
        == "completed"
    )
    with b.provision.tx() as cur:
        b.provision.q(
            cur, "UPDATE work_v1_outbox SET content_json='{}' WHERE task_id=?", (row["id"],)
        )
    with pytest.raises(WorkError, match="readback_mismatch"):
        service.outbox(t["agent"], row["id"])


@pytest.mark.parametrize("point", ["before_commit", "after_commit"])
@REAL
def test_actual_result_events_outbox_commit_or_rollback_together_and_never_rerun(api, point):
    b, _issuer, service, c, t = api
    original = service._invoke
    calls = []

    def actual_run(row):
        calls.append(row["id"])
        return original(row)

    service._invoke = actual_run
    row = prepare(api)
    approve(api, row)
    injected, completion_pending = [False], [False]

    def result_commit_failure(stage):
        if injected[0]:
            return
        # Inspect the already-open transaction, never start a PG read transaction
        # after commit. SQLite cursors also do not implement a context manager.
        if stage == "before_commit":
            cursor = b.store._conn.cursor()
            try:
                b.work.q(cursor, "SELECT status FROM work_v1_tasks WHERE id=?", (row["id"],))
                status = cursor.fetchone()[0]
                b.work.q(
                    cursor, "SELECT count(*) FROM work_v1_outbox WHERE task_id=?", (row["id"],)
                )
                completion_pending[0] = status == "completed" and cursor.fetchone()[0] == 1
            finally:
                cursor.close()
        if stage == point and completion_pending[0]:
            injected[0] = True
            raise OSError("synthetic lost completion write/ack")

    b.work.fault_hook = result_commit_failure
    reply = c.post("/v3/work/tasks/" + row["id"] + "/execute", headers=headers(t))
    assert reply.status_code == 200 and injected[0]
    b.work.fault_hook = None
    assert len(calls) == 1
    current = b.work.get(row["id"])
    assert current["status"] == ("uncertain" if point == "before_commit" else "completed")
    assert len(b.work.events(row["id"])) == (2 if point == "before_commit" else 7)
    assert bool(service.outbox(t["agent"], row["id"])) == (point == "after_commit")
    assert c.post("/v3/work/tasks/" + row["id"] + "/execute", headers=headers(t)).json()["replayed"]
    assert len(calls) == 1


@REAL
def test_cancel_waits_for_real_owned_child_exit_not_just_request_ack(api, monkeypatch):
    import threading
    from pathlib import Path

    import isolation

    b, _issuer, _service, c, t = api
    started, release = threading.Event(), threading.Event()
    pids = []
    run = isolation.run_fixed

    def controlled(mode, body, **kwargs):
        def on_start(pid):
            pids.append(pid)
            started.set()
            assert release.wait(3)

        return run(mode, body, **kwargs, on_start=on_start)

    monkeypatch.setattr(isolation, "run_fixed", controlled)
    row = prepare(api)
    approve(api, row)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(c.post, "/v3/work/tasks/" + row["id"] + "/execute", headers=headers(t))
        try:
            assert started.wait(3)
            reply = c.post("/v3/work/tasks/" + row["id"] + "/cancel", headers=headers(t))
            assert reply.json() == {"requested": True, "stop_confirmed": False}
            assert b.work.get(row["id"])["status"] == "running"
        finally:
            release.set()
        result = future.result(timeout=5).json()
    assert result["status"] == "cancelled" and result["result"]["child_exit_confirmed"]
    assert pids and all(not Path("/proc", str(pid)).exists() for pid in pids)
    assert not _service.outbox(t["agent"], row["id"])


@pytest.mark.parametrize(
    "field,value",
    [
        ("request_id", "not-a-uuid"),
        ("request_id", "A" * 5000),
        ("fixture", []),
        ("ai_use_approved", 1),
        ("goal", {"actor": "human:owner"}),
    ],
)
def test_malformed_intake_is_sanitized_without_any_durable_work(api, field, value):
    b, _issuer, _service, c, t = api
    body = intake()
    body[field] = value
    response = c.post("/v3/work/tasks", json=body, headers=headers(t))
    assert response.status_code in {409, 422}
    assert response.json()["detail"] in {"work_contract_refused", "invalid_work_request"}
    assert b.work.list("demo") == []


@pytest.mark.parametrize("verdict", [{"effect": [], "rule": "bad"}, {"effect": {}, "rule": "bad"}])
def test_malformed_policy_types_deny_instead_of_raising_or_allowing(api, verdict):
    b, _issuer, service, _c, t = api
    service.policy = lambda _plan: verdict
    row = service.prepare(t["agent"], intake())
    assert row["status"] == "denied" and not b.work.get(row["id"])["attempted"]


@pytest.mark.parametrize("tamper", ["destination", "content_and_digest"])
@REAL
def test_artifact_review_uses_immutable_staging_attestation_not_just_mutable_outbox(api, tamper):
    from work_store import canonical, digest

    b, _issuer, service, c, t = api
    row = prepare(api)
    approve(api, row)
    assert (
        c.post("/v3/work/tasks/" + row["id"] + "/execute", headers=headers(t)).json()["status"]
        == "completed"
    )
    with b.provision.tx() as cur:
        if tamper == "destination":
            b.provision.q(
                cur,
                "UPDATE work_v1_outbox SET destination='external:unapproved' WHERE task_id=?",
                (row["id"],),
            )
        else:
            b.provision.q(
                cur,
                "UPDATE work_v1_outbox SET content_json=?,sha256=? WHERE task_id=?",
                (canonical({"forged": True}), digest({"forged": True}), row["id"]),
            )
    with pytest.raises(WorkError, match="artifact_readback_mismatch"):
        service.outbox(t["agent"], row["id"])


@pytest.mark.parametrize("change", ["implementation", "policy", "limits"])
def test_exact_binding_drift_between_claim_and_effect_still_blocks_the_frozen_tool(
    api, monkeypatch, change
):
    from work_profile_fixtures import LIMITS

    b, _issuer, service, c, t = api
    calls = []
    policy_state = {"effect": "gate", "rule": "owned.exact"}
    service.policy = lambda _plan: dict(policy_state)
    service._invoke = lambda _row: calls.append("must-not-run") or {}
    row = prepare(api)
    approve(api, row)
    actual = b.work.before_effect

    def drift(*args, **kwargs):
        if change == "implementation":
            service._invoke = lambda _row: calls.append("changed-must-not-run") or {}
        elif change == "policy":
            policy_state["effect"] = "deny"
        else:
            b.provision.configure("new-scope-after-review", LIMITS)
        return actual(*args, **kwargs)

    monkeypatch.setattr(b.work, "before_effect", drift)
    response = c.post("/v3/work/tasks/" + row["id"] + "/execute", headers=headers(t))
    assert response.status_code == 200 and response.json()["status"] == "blocked"
    assert not calls and not b.work.get(row["id"])["attempted"]


def test_implementation_bindings_are_stable_while_other_calls_hold_constant_references(api):
    _b, _issuer, service, _c, _t = api
    initial = service.bindings()
    # Marshal v3+ encodes refcount-dependent flags: another legitimate policy
    # invocation holding the SAME constants must not look like changed code.
    aliases = [list(service._invoke.__code__.co_consts), service.policy({})]
    assert service.bindings() == initial
    assert aliases
