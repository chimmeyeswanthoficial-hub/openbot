"""S08 signed device API against real work stores (SQLite + restricted PostgreSQL).

HTTPS TestClient checks are ASGI contract tests. Separate browser/TLS fixture
proofs exercise a real TLS socket and renderer WebCrypto. All humans are fixtures.
"""

from __future__ import annotations

import json
import secrets
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from control_api import (
    SCOPES,
    ControlAuthority,
    ControlBridge,
    ControlError,
    DeviceStore,
    create_control_app,
    sha,
)
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from economic import Scope
from economic_fixtures import charge, encoded, refund
from economic_repository import EconomicBook
from fastapi.testclient import TestClient
from governed_skills import ToolCatalog, file_sha
from trust_crypto import encode, sign
from work_service import WorkService


def p256_sign(key, message):
    der = key.sign(message.encode(), ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)
    return encode(r.to_bytes(32, "big") + s.to_bytes(32, "big"))


class DeviceClient:
    def __init__(self, api, code=None, label="Synthetic API fixture"):
        self.client, self.server = api.client, api.devices.server_id
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.public = encode(
            self.key.public_key().public_bytes(
                serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
            )
        )
        self.pair_body = {
            "code": code,
            "public_key": self.public,
            "label": label,
            "client_version": "0.2.0",
            "signature": p256_sign(self.key, f"openbot.pair/1\n{self.server}\n{code}"),
        }
        reply = self.client.post("/api/v1/pair", json=self.pair_body)
        assert reply.status_code == 200, reply.text
        self.paired = reply.json()["data"]
        self.identity = self.paired["device"]

    def headers(self, method, path, raw=b"", key=None):
        challenge = self.client.post(
            "/api/v1/challenge",
            json={
                "device": self.identity,
                "method": method,
                "path": path,
                "body_sha256": sha(raw),
                "api_version": "1",
            },
        )
        if challenge.status_code != 200:
            return None, challenge
        c = challenge.json()["data"]
        headers = {
            "X-OpenBot-Device": self.identity,
            "X-OpenBot-Challenge": c["id"],
            "X-OpenBot-Signature": p256_sign(key or self.key, c["message"]),
            "Content-Type": "application/json",
        }
        return headers, None

    def request(self, method, path, body=None, *, key=None):
        raw = b"" if body is None else json.dumps(body, separators=(",", ":")).encode()
        headers, error = self.headers(method, path, raw, key=key)
        if error is not None:
            return error
        return self.client.request(method, path, content=raw, headers=headers)


@pytest.fixture
def control(durable_backend, tmp_path):
    b = durable_backend
    issuer = WorkService(b.provision, enabled=True)
    work = WorkService(b.work, enabled=True)
    server = sha(b"owned-synthetic-control-fixture")
    devices = DeviceStore(
        tmp_path / "devices.db", server, initialize=True, clock=lambda: b.clock[0]
    )
    authority = ControlAuthority(devices, issuer)
    admin_key = Ed25519PrivateKey.generate()
    trusted = {
        "host": {
            "public_key": encode(admin_key.public_key().public_bytes_raw()),
            "roles": ["catalog-admin"],
            "revoked": False,
        }
    }
    root = Path(__file__).resolve().parents[3]
    lock = root / "audit/first-party-tool-catalog.json"
    auth_file = tmp_path / "catalog-authority.json"
    catalog_payload = {
        "schema": "openbot.tool-authority/1",
        "epoch": 1,
        "not_before": int(b.clock[0]) - 1,
        "expires": int(b.clock[0]) + 3600,
        "revoked": [],
        "grants": {"demo": ["owned.qa"], "other": ["owned.qa"]},
    }
    auth_file.write_text(json.dumps(sign(admin_key, "host", catalog_payload)))
    catalog = ToolCatalog(root, lock, file_sha(lock), auth_file, trusted, clock=lambda: b.clock[0])
    setup_book = EconomicBook(b.owner, experimental=True)
    scopes = {
        "demo": Scope("acct_controlfixture", "demo"),
        "other": Scope("acct_otherfixture", "other"),
    }
    for venture, scope in scopes.items():
        obj = charge(venture, 25000 if venture == "demo" else 99999)
        obj["metadata"]["venture"] = venture
        setup_book.ingest(
            encoded("charge.succeeded", obj, "evt_control_" + venture, scope.account), scope
        )
    obj = refund("control", 5000, "demo")
    obj["metadata"]["venture"] = "demo"
    setup_book.ingest(
        encoded("refund.created", obj, "evt_control_refund", scopes["demo"].account), scopes["demo"]
    )
    if b.kind == "pg":
        from psycopg2 import sql

        with b.admin.cursor() as cur:
            for table in [
                "economic_v1_schema",
                "economic_v1_messages",
                "economic_v1_postings",
                "economic_v1_links",
                "economic_v1_events",
            ]:
                cur.execute(
                    sql.SQL("GRANT SELECT ON {}.{} TO {}").format(
                        sql.Identifier(b.schema), sql.Identifier(table), sql.Identifier(b.role)
                    )
                )
    book = EconomicBook(b.store, experimental=True, initialize=False)
    bridge = ControlBridge(
        devices, work, catalog, book=book, book_scopes=scopes, authority=authority
    )
    client_file = root.parent / "control/web/index.html"
    app = create_control_app(
        bridge,
        origin="https://control.test",
        client_file=client_file,
        client_sha256=file_sha(client_file),
        enabled=True,
    )
    client = TestClient(app, base_url="https://control.test")
    fixture = SimpleNamespace(
        b=b,
        work=work,
        devices=devices,
        authority=authority,
        bridge=bridge,
        client=client,
        catalog=catalog,
        catalog_payload=catalog_payload,
        admin_key=admin_key,
        auth_file=auth_file,
        client_file=client_file,
    )
    for name, venture, role, granted in [
        ("owner", "demo", "owner", sorted(SCOPES)),
        ("viewer", "demo", "viewer", ["read", "revoke-self"]),
        ("other", "other", "owner", sorted(SCOPES)),
    ]:
        code = authority.issue_pairing(
            actor="human:fixture_" + name, venture=venture, role=role, scopes=granted
        )
        setattr(fixture, name, DeviceClient(fixture, code))
    return fixture


def intake():
    return {
        "request_id": str(uuid.uuid4()),
        "fixture": "invoice-good-v1",
        "goal": "Validate the owned invoice sample",
        "acceptance": "Independent QA and documentation assertions",
        "rights_ref": "owned:first-party-seed",
        "ai_use_approved": True,
        "destination": "local-review",
    }


def prepare(control):
    reply = control.owner.request("POST", "/api/v1/tasks", intake())
    assert reply.status_code == 200, reply.text
    return reply.json()["data"]


def test_default_off_no_legacy_grants_and_no_http_downgrade(control):
    c = control
    app = create_control_app(
        c.bridge,
        origin="https://control.test",
        client_file=c.client_file,
        client_sha256=file_sha(c.client_file),
    )
    assert TestClient(app).get("/api/v1/identity").status_code == 404
    assert c.client.post("/v3/work/tasks", json=intake()).status_code == 404
    assert c.client.post("/api/v1/grant", json={"role": "owner"}).status_code == 404
    assert c.client.get("http://control.test/api/v1/identity").status_code == 403
    assert (
        c.client.get("/api/v1/identity", headers={"Origin": "https://attacker.invalid"}).status_code
        == 403
    )
    assert c.client.get("/api/v1/identity", headers={"Host": "attacker.invalid"}).status_code == 403
    assert c.client.get("/api/v1/tasks").status_code == 403


def test_real_scoped_reads_use_the_exact_book_not_float_pnl(control):
    reply = control.owner.request("GET", "/api/v1/snapshot")
    assert reply.status_code == 200, reply.text
    envelope = reply.json()
    assert envelope["api_version"] == "1" and envelope["fresh_for_seconds"] == 15
    data = envelope["data"]
    assert data["status"]["paid_provider_enabled"] is False
    assert data["exact_book"]["source"] == "economic_v1_postings"
    assert data["exact_book"]["summary"]["net_captured_minor"] == "20000"
    assert data["exact_book"]["summary"]["capture_minor"] == "25000"
    assert data["exact_book"]["legacy_float_pnl_used"] is False
    assert data["exact_book"]["summary"]["bank_settlement_verified"] is False
    other = control.other.request("GET", "/api/v1/exact-book").json()["data"]
    assert other["summary"]["net_captured_minor"] == "99999"
    assert {p["economic_id"] for p in other["postings"]} == {"ch_other"}


def test_pairing_code_one_use_and_public_key_is_proved(control):
    assert control.client.post("/api/v1/pair", json=control.owner.pair_body).status_code == 403
    forged = {**control.owner.pair_body, "signature": encode(b"0" * 64)}
    assert control.client.post("/api/v1/pair", json=forged).status_code == 403
    assert "token" not in control.owner.paired
    assert control.owner.paired["hardware_key_bound"] is False


@pytest.mark.parametrize("attack", ["forged-key", "replay", "body", "path", "device", "expiry"])
def test_requests_are_key_nonce_body_path_device_and_time_bound(control, attack):
    client = control.owner
    path = "/api/v1/status"
    headers, error = client.headers("GET", path)
    assert error is None
    raw = b""
    if attack == "forged-key":
        headers, _ = client.headers("GET", path, key=ec.generate_private_key(ec.SECP256R1()))
    if attack == "replay":
        assert control.client.get(path, headers=headers).status_code == 200
    if attack == "body":
        raw = b'{"venture":"other"}'
    if attack == "path":
        path = "/api/v1/exact-book"
    if attack == "device":
        headers["X-OpenBot-Device"] = control.other.identity
    if attack == "expiry":
        control.b.clock[0] += 60
    reply = control.client.request("GET", path, content=raw, headers=headers)
    assert reply.status_code == 403, reply.text


@pytest.mark.parametrize(
    "field", ["role", "actor", "venture", "program", "budget_usd", "upper_minor", "provider"]
)
def test_json_cannot_grant_authority(control, field):
    body = intake()
    body[field] = "unauthorized"
    assert control.owner.request("POST", "/api/v1/tasks", body).status_code == 422
    assert control.work.work.list("demo") == []


def test_viewer_cross_venture_revoked_and_expired_devices_are_refused(control):
    assert control.viewer.request("POST", "/api/v1/tasks", intake()).status_code == 403
    task = prepare(control)
    assert control.other.request("GET", "/api/v1/tasks/" + task["id"]).status_code == 403
    assert control.other.request("GET", "/api/v1/tasks").json()["data"] == []
    control.authority.revoke(control.owner.identity)
    assert control.owner.request("GET", "/api/v1/status").status_code == 403
    control.b.clock[0] += 900
    assert control.viewer.request("GET", "/api/v1/status").status_code == 403


def test_exact_approval_needs_separate_fresh_task_and_device_bound_reauth(control):
    row = prepare(control)
    path = "/api/v1/tasks/" + row["id"]
    assert (
        control.owner.request("POST", path + "/execute", {"digest": row["spec_digest"]}).json()[
            "data"
        ]["attempted"]
        == 0
    )
    # Execution before approval can transition to blocked; use a new exact proposal.
    row = prepare(control)
    path = "/api/v1/tasks/" + row["id"]
    assert (
        control.owner.request(
            "POST", path + "/approve", {"digest": row["spec_digest"], "reauth_code": "x" * 43}
        ).status_code
        == 403
    )
    code = control.authority.issue_reauthentication(
        control.owner.identity, row["id"], row["spec_digest"], human="human:fixture_owner"
    )
    assert (
        control.owner.request(
            "POST", path + "/approve", {"digest": "0" * 64, "reauth_code": code}
        ).status_code
        == 409
    )
    assert control.owner.request(
        "POST", path + "/approve", {"digest": row["spec_digest"], "reauth_code": code}
    ).json()["data"]["approved"]
    assert (
        control.owner.request(
            "POST", path + "/approve", {"digest": row["spec_digest"], "reauth_code": code}
        ).status_code
        == 403
    )


def test_browser_contract_to_governance_artifact_readback_and_replay(control):
    row = prepare(control)
    code = control.authority.issue_reauthentication(
        control.owner.identity, row["id"], row["spec_digest"], human="human:fixture_owner"
    )
    path = "/api/v1/tasks/" + row["id"]
    assert control.owner.request(
        "POST", path + "/approve", {"digest": row["spec_digest"], "reauth_code": code}
    ).json()["data"]["approved"]
    result = control.owner.request("POST", path + "/execute", {"digest": row["spec_digest"]})
    assert result.status_code == 200, result.text
    assert result.json()["data"]["status"] == "completed"
    artifact = control.owner.request("GET", path + "/artifact").json()["data"]
    from work_store import digest

    assert digest(artifact["content"]) == artifact["sha256"]
    assert artifact["external_delivery"] is False
    replay = control.owner.request(
        "POST", path + "/execute", {"digest": row["spec_digest"]}
    ).json()["data"]
    assert replay["replayed"] is True
    assert (
        len([e for e in control.work.work.history(row["id"]) if e["kind"] == "effect_authorized"])
        == 1
    )
    assert control.other.request("GET", path + "/artifact").status_code == 403
    assert control.owner.request("GET", "/api/v1/audit").json()["data"]


def test_catalog_revocation_prevents_effect_after_review(control):
    row = prepare(control)
    code = control.authority.issue_reauthentication(
        control.owner.identity, row["id"], row["spec_digest"], human="human:fixture_owner"
    )
    path = "/api/v1/tasks/" + row["id"]
    assert (
        control.owner.request(
            "POST", path + "/approve", {"digest": row["spec_digest"], "reauth_code": code}
        ).status_code
        == 200
    )
    control.catalog_payload.update(epoch=2, revoked=["owned.qa"])
    control.auth_file.write_text(
        json.dumps(sign(control.admin_key, "host", control.catalog_payload))
    )
    assert (
        control.owner.request("POST", path + "/execute", {"digest": row["spec_digest"]}).status_code
        == 409
    )
    assert control.work.work.get(row["id"])["attempted"] == 0


def test_body_request_identity_and_challenge_capacity_are_bounded(control):
    assert control.client.post("/api/v1/pair", content=b"x" * 16385).status_code == 413
    assert control.client.get("/api/v1/status?venture=other").status_code == 422
    for i in range(32):
        reply = control.client.post(
            "/api/v1/challenge",
            json={
                "device": control.owner.identity,
                "method": "GET",
                "path": "/api/v1/status",
                "body_sha256": sha(b""),
                "api_version": "1",
            },
        )
        assert reply.status_code == 200, (i, reply.text)
    assert (
        control.client.post(
            "/api/v1/challenge",
            json={
                "device": control.owner.identity,
                "method": "GET",
                "path": "/api/v1/status",
                "body_sha256": sha(b""),
                "api_version": "1",
            },
        ).status_code
        == 429
    )


def test_failed_pair_attempts_are_rate_limited_not_rolled_back(control):
    body = {**control.owner.pair_body, "code": secrets.token_urlsafe(32)}
    body["signature"] = p256_sign(
        control.owner.key, f"openbot.pair/1\n{control.devices.server_id}\n{body['code']}"
    )
    codes = [control.client.post("/api/v1/pair", json=body).status_code for _ in range(12)]
    assert codes[-1] == 429 and 403 in codes


def test_device_schema_identity_client_pin_and_host_only_authority(control):
    with pytest.raises(ControlError):
        DeviceStore(control.devices.path, "0" * 64)
    with pytest.raises(ControlError):
        ControlAuthority(control.devices, control.work)
    with pytest.raises(ControlError):
        control.authority.issue_pairing(
            actor="human:fixture", venture="demo", role="viewer", scopes=["read", "execute"]
        )
    with pytest.raises(ControlError):
        create_control_app(
            control.bridge,
            origin="http://control.test",
            client_file=control.client_file,
            client_sha256=file_sha(control.client_file),
            enabled=True,
        )
    with pytest.raises(ControlError):
        create_control_app(
            control.bridge,
            origin="https://control.test",
            client_file=control.client_file,
            client_sha256="0" * 64,
            enabled=True,
        )
    assert control.client.get("/control/").status_code == 200
    assert (
        "frame-ancestors 'none'"
        in control.client.get("/control/").headers["content-security-policy"]
    )


def test_feedback_identity_is_derived_from_session_not_client_json(control, tmp_path):
    from governed_skills import (
        ConsentedMemory,
        GovernanceError,
        MemoryFeedbackService,
        MemoryIdentity,
    )

    memory = ConsentedMemory(
        tmp_path / "feedback.db",
        tmp_path / "deletion-authority.db",
        host_admin=True,
        clock=lambda: control.b.clock[0],
    )
    with control.devices.tx() as conn:
        owner_token = control.devices.device(conn, control.owner.identity)["token"]
        other_token = control.devices.device(conn, control.other.identity)["token"]
    identity = MemoryIdentity("demo", "human:fixture_owner", "qa:owned")
    consent = memory.grant(
        identity,
        purpose="qa-context",
        source="owned:first-party-seed",
        consent_ref="consent:scoped-fixture",
        expires=int(control.b.clock[0]) + 600,
        human="human:fixture_owner",
    )
    memory.add(
        identity,
        consent,
        purpose="qa-context",
        text="Use an independent worked example.",
        artifact_sha256="a" * 64,
        expires=int(control.b.clock[0]) + 300,
    )
    scoped = MemoryFeedbackService(control.work, memory)
    assert len(scoped.quote(owner_token)) == 1
    assert scoped.quote(other_token) == []
    with pytest.raises(GovernanceError):
        scoped.submit(owner_token, {"client": "other", "subject": "human:other", "role": "owner"})
    assert scoped.quote(owner_token)[0]["authority"] is False
