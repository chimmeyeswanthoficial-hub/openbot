"""Real disposable SQLite + signed-device HTTP history contract tests.

Most are ASGI HTTP tests, not TLS/device acceptance. One bounded real TLS socket
case verifies a synthetic CA normally. No provider, VM, IDE/social account,
production migration or genuine pilot observation is involved.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import conversation_journal as journal_module
import pytest
from control_api import (
    ControlAuthority,
    ControlBridge,
    ControlError,
    DeviceStore,
    create_control_app,
    sha,
)
from conversation_api import HISTORY_SCOPES, PREFIX, ConversationAPI
from conversation_journal import ConversationJournal
from fastapi.testclient import TestClient
from repository import Store
from test_control_api import DeviceClient
from work_service import WorkService
from work_store import WorkStore

THREAD = "c" + "1" * 32
MESSAGE = "m" + "1" * 32
ROOT = Path(__file__).resolve().parents[3]
CLIENT_FILE = ROOT.parent / "control/web/index.html"


def create_body(thread=THREAD, title="Private history"):
    return {"thread_id": thread, "title": title}


def message_body(message=MESSAGE, text="An actual stored human message.", previous=0):
    return {"message_id": message, "text": text, "expected_sequence": previous}


def data(reply):
    assert reply.status_code == 200, reply.text
    return reply.json()["data"]


@pytest.fixture
def history(tmp_path):
    now = [time.time()]
    stacks = []

    def stack(*, initialize):
        owner = Store(str(tmp_path / "work.sqlite"), initialize=initialize)
        provision = WorkStore(owner, initialize=initialize, clock=lambda: now[0])
        runtime = Store(str(tmp_path / "work.sqlite"), initialize=False)
        work = WorkStore(runtime, clock=lambda: now[0])
        issuer, service = WorkService(provision, enabled=True), WorkService(work, enabled=True)
        devices = DeviceStore(
            tmp_path / "devices.sqlite",
            sha(b"synthetic-history-host"),
            initialize=initialize,
            clock=lambda: now[0],
        )
        authority = ControlAuthority(devices, issuer) if initialize else None
        connection = sqlite3.connect(
            tmp_path / "history.sqlite", isolation_level=None, check_same_thread=False
        )
        journal = ConversationJournal(connection, initialize=initialize)
        bridge = ControlBridge(
            devices,
            service,
            None,
            book=None,
            book_scopes={},
            authority=authority,
            history=ConversationAPI(journal),
        )
        app = create_control_app(
            bridge,
            origin="https://history.test",
            client_file=CLIENT_FILE,
            client_sha256=sha(CLIENT_FILE.read_bytes()),
            enabled=True,
        )
        value = SimpleNamespace(
            client=TestClient(app, base_url="https://history.test"),
            app=app,
            bridge=bridge,
            devices=devices,
            authority=authority,
            journal=journal,
            connection=connection,
            issuer=issuer,
            work=work,
            runtime=runtime,
            owner_store=owner,
        )
        stacks.append(value)
        return value

    h = stack(initialize=True)
    h.now, h.path, h.reopen = now, tmp_path, lambda: stack(initialize=False)
    h.pair = lambda actor="human:alice", venture="alpha", role="owner", scopes=None: DeviceClient(
        h,
        h.authority.issue_pairing(
            actor=actor,
            venture=venture,
            role=role,
            scopes=scopes or ["read", "revoke-self", *sorted(HISTORY_SCOPES)],
        ),
    )
    h.alice = h.pair()
    h.bob = h.pair(actor="human:bob")
    h.other = h.pair(venture="beta")
    yield h
    for s in stacks:
        s.client.close()
        s.connection.close()
        s.runtime._conn.close()
        s.owner_store._conn.close()


def create(h, device=None, thread=THREAD):
    return (device or h.alice).request("POST", PREFIX + "/create", create_body(thread))


def append(h, device=None, **kwargs):
    return (device or h.alice).request(
        "POST", PREFIX + "/" + THREAD + "/messages", message_body(**kwargs)
    )


def read(h, device=None, after=0, limit=50):
    return (device or h.alice).request(
        "POST", PREFIX + "/" + THREAD + "/read", {"after": after, "limit": limit}
    )


def row_count(h):
    return h.connection.execute("SELECT COUNT(*) FROM os_conversation_v1_events").fetchone()[0]


def raw_request(device, path, raw):
    headers, error = device.headers("POST", path, raw)
    return (
        error
        if error is not None
        else device.client.request("POST", path, content=raw, headers=headers)
    )


def test_opt_in_only_no_default_store_or_http_setup_route(history):
    h = history
    h.bridge.history = None
    reply = create(h)
    assert reply.status_code == 404 and reply.json()["detail"] == "history_not_configured"
    assert h.client.post("/api/v1/conversations/setup", json={}).status_code == 404
    assert row_count(h) == 0
    with pytest.raises(ControlError):
        ControlBridge(h.devices, h.bridge.work, None, book=None, book_scopes={}, history=object())


def test_actual_signed_human_create_append_read_and_retry(history):
    h = history
    assert data(create(h))["thread_id"] == THREAD
    first = data(append(h, text="నిజమైన local history 🙂"))
    assert first["sequence"] == 1 and first["agent_executed"] is False
    assert data(append(h, text="నిజమైన local history 🙂"))["sequence"] == 1
    result = data(read(h))
    event = result["events"][0]["event"]
    assert event["type"] == "CUSTOM" and event["name"] == "openbot.user_message.v1"
    assert event["value"]["author"] == "human:alice"
    assert event["value"]["role"] == "user"
    assert event["value"]["text"] == "నిజమైన local history 🙂"
    assert row_count(h) == 1
    assert result["history_only"] is True and result["agent_executed"] is False
    for header in [
        "cache-control",
        "content-security-policy",
        "referrer-policy",
        "strict-transport-security",
    ]:
        assert header in read(h).headers


@pytest.mark.parametrize("who", ["bob", "other"])
def test_other_principal_or_venture_has_same_refusal_as_missing(history, who):
    h = history
    data(create(h))
    data(append(h))
    device = getattr(h, who)
    denied = read(h, device)
    missing = device.request("POST", PREFIX + "/c" + "9" * 32 + "/read", {"after": 0, "limit": 50})
    assert denied.status_code == missing.status_code == 404
    assert denied.json() == missing.json() == {"detail": "thread_not_found"}
    assert (
        data(device.request("POST", PREFIX + "/list", {"after": "", "limit": 50}))["threads"] == []
    )
    assert append(h, device).status_code == 404
    assert device.request("POST", PREFIX + "/" + THREAD + "/delete", {}).status_code == 404
    assert row_count(h) == 1


def test_same_authenticated_actor_can_reopen_history_on_second_device(history):
    h = history
    data(create(h))
    data(append(h))
    second = h.pair()
    assert second.identity != h.alice.identity
    assert data(read(h, second))["head_sequence"] == 1


def test_new_gateway_identity_does_not_open_other_server_history(history):
    h = history
    data(create(h))
    data(append(h))
    old = h.devices.server_id
    h.devices.server_id = sha(b"different-history-host")
    try:
        assert read(h).status_code == 404
    finally:
        h.devices.server_id = old


@pytest.mark.parametrize(
    "operation,capability",
    [("create", "history-write"), ("list", "history-read"), ("delete", "history-delete")],
)
def test_old_generic_grants_do_not_acquire_history_authority(history, operation, capability):
    h = history
    old = h.pair(scopes=["read", "propose", "revoke-self"])
    path, body = (
        (PREFIX + "/create", create_body())
        if operation == "create"
        else (PREFIX + "/list", {"after": "", "limit": 50})
        if operation == "list"
        else (PREFIX + "/" + THREAD + "/delete", {})
    )
    assert old.request("POST", path, body).status_code == 403
    assert capability not in old.paired["scopes"] and row_count(h) == 0


def test_viewer_cannot_be_issued_history_write_or_delete(history):
    h = history
    for capability in ["history-write", "history-delete"]:
        with pytest.raises(ControlError):
            h.authority.issue_pairing(
                actor="human:viewer", venture="alpha", role="viewer", scopes=["read", capability]
            )
    viewer = h.pair(actor="human:viewer", role="viewer", scopes=["read", "history-read"])
    assert (
        data(viewer.request("POST", PREFIX + "/list", {"after": "", "limit": 50}))["threads"] == []
    )
    assert create(h, viewer).status_code == 403


@pytest.mark.parametrize(
    "field", ["actor", "principal", "tenant", "venture", "role", "event", "tool", "approval"]
)
def test_json_never_selects_authority_role_event_or_tool(history, field):
    h = history
    data(create(h))
    body = {**message_body(), field: "untrusted"}
    reply = h.alice.request("POST", PREFIX + "/" + THREAD + "/messages", body)
    assert reply.status_code == 422 and row_count(h) == 0


@pytest.mark.parametrize(
    "raw",
    [
        b'{"thread_id":"' + THREAD.encode() + b'","title":"a","title":"b"}',
        b'{"thread_id":"' + THREAD.encode() + b'","title":NaN}',
        b'{"thread_id":"' + THREAD.encode() + b'","title":Infinity}',
        b"[" * 1500 + b"]" * 1500,
        b"\xff",
    ],
)
def test_duplicate_keys_non_json_numbers_nesting_and_invalid_encoding_refused(history, raw):
    h = history
    reply = raw_request(h.alice, PREFIX + "/create", raw)
    assert reply.status_code == 422
    assert (
        h.connection.execute("SELECT COUNT(*) FROM os_conversation_v1_threads").fetchone()[0] == 0
    )


@pytest.mark.parametrize(
    "text,status",
    [
        ("", 422),
        (" \n", 422),
        ("bad\x00value", 422),
        ("\ud800", 422),
        ("అ" * 3000, 413),
        ("sk-" + "z" * 30, 422),
        ("-----BEGIN PRIVATE KEY-----", 422),
    ],
)
def test_text_validation_and_credential_pattern_rejection_without_echo(history, text, status):
    h = history
    data(create(h))
    reply = append(h, text=text)
    assert reply.status_code == status and row_count(h) == 0
    assert len(reply.content) < 150


def test_gateway_request_bound_precedes_any_history_write(history):
    h = history
    data(create(h))
    reply = raw_request(h.alice, PREFIX + "/" + THREAD + "/messages", b" " * 16385)
    assert reply.status_code == 413 and row_count(h) == 0


@pytest.mark.parametrize(
    "attack", ["body", "path", "key", "replay", "nonce-expiry", "device-revoke", "session-revoke"]
)
def test_history_uses_real_signed_nonce_body_path_key_expiry_and_revocation(history, attack):
    from cryptography.hazmat.primitives.asymmetric import ec
    from test_control_api import p256_sign

    h = history
    path = PREFIX + "/create"
    raw = json.dumps(create_body(), separators=(",", ":")).encode()
    headers, error = h.alice.headers("POST", path, raw)
    assert error is None
    if attack == "body":
        raw += b" "
    elif attack == "path":
        path = PREFIX + "/list"
    elif attack == "key":
        with h.devices.tx() as conn:
            msg = conn.execute(
                "SELECT message FROM control_v1_challenges WHERE id=?",
                (headers["X-OpenBot-Challenge"],),
            ).fetchone()[0]
        headers["X-OpenBot-Signature"] = p256_sign(ec.generate_private_key(ec.SECP256R1()), msg)
    elif attack == "replay":
        assert h.client.post(path, content=raw, headers=headers).status_code == 200
    elif attack == "nonce-expiry":
        h.now[0] += 61
    elif attack == "device-revoke":
        h.authority.revoke(h.alice.identity)
    elif attack == "session-revoke":
        with h.devices.tx() as conn:
            token = h.devices.device(conn, h.alice.identity)["token"]
        h.issuer.revoke_session(token)
    reply = h.client.post(path, content=raw, headers=headers)
    assert reply.status_code == 403
    assert h.connection.execute("SELECT COUNT(*) FROM os_conversation_v1_threads").fetchone()[
        0
    ] == (1 if attack == "replay" else 0)


@pytest.mark.parametrize("change", ["scope", "role"])
def test_current_device_scope_and_session_role_are_rechecked_after_auth(history, change):
    h = history
    path = PREFIX + "/create"
    raw = json.dumps(create_body()).encode()
    headers, _ = h.alice.headers("POST", path, raw)
    device = h.devices.authenticate({k.lower(): v for k, v in headers.items()}, "POST", path, raw)
    with h.devices.tx() as conn:
        if change == "scope":
            conn.execute(
                "UPDATE control_v1_devices SET scopes=? WHERE id=?",
                (json.dumps(["read"]), device["id"]),
            )
        else:
            conn.execute("UPDATE control_v1_devices SET role='viewer' WHERE id=?", (device["id"],))
    with pytest.raises(ControlError):
        h.bridge.dispatch(device, "POST", path, raw)
    assert row_count(h) == 0


@pytest.mark.parametrize(
    "headers,url,status",
    [
        ({"Origin": "https://attacker.invalid"}, None, 403),
        ({"Host": "attacker.invalid"}, None, 403),
        ({}, "http://history.test/api/v1/conversations/create", 403),
        ({}, PREFIX + "/create?actor=other", 422),
        ({}, "/api/v1/conversations/%63reate", 422),
    ],
)
def test_tls_origin_host_and_canonical_path_boundaries(history, headers, url, status):
    assert (
        history.client.post(
            url or PREFIX + "/create", json=create_body(), headers=headers
        ).status_code
        == status
    )
    assert row_count(history) == 0


def test_stale_and_conflicting_retries_fail_without_duplicate(history):
    h = history
    data(create(h))
    data(append(h))
    assert append(h, text="changed").status_code == 409
    assert append(h, previous=1).status_code == 409
    assert append(h, message="m" + "2" * 32).status_code == 409
    assert data(append(h))["sequence"] == 1 and row_count(h) == 1


def test_pagination_and_compare_and_swap_across_two_signed_devices(history):
    h = history
    data(create(h))
    data(append(h))
    data(append(h, message="m" + "2" * 32, previous=1))
    first = data(read(h, limit=1))
    assert first["head_sequence"] == 2 and first["next_after"] == 1
    assert data(read(h, after=1))["events"][0]["sequence"] == 2
    assert read(h, after=3).status_code == 422
    second = h.pair()

    def send(item):
        device, mid = item
        return append(h, device, message=mid, previous=2).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(send, [(h.alice, "m" + "3" * 32), (second, "m" + "4" * 32)]))
    assert sorted(replies) == [200, 409] and row_count(h) == 3


def test_listing_is_scoped_and_keyset_paginated(history):
    h = history
    for n in (1, 2, 3):
        data(create(h, thread="c" + str(n) * 32))
    first = data(h.alice.request("POST", PREFIX + "/list", {"after": "", "limit": 2}))
    assert len(first["threads"]) == 2
    last = data(
        h.alice.request("POST", PREFIX + "/list", {"after": first["next_after"], "limit": 2})
    )
    assert len(last["threads"]) == 1 and last["next_after"] is None
    assert data(h.bob.request("POST", PREFIX + "/list", {"after": "", "limit": 2}))["threads"] == []


def test_journal_quota_storage_failure_and_audit_precondition_are_fail_closed(history, monkeypatch):
    h = history
    data(create(h))
    data(append(h))
    monkeypatch.setattr(journal_module, "MAX_EVENTS_PER_THREAD", 1)
    assert append(h, message="m" + "2" * 32, previous=1).status_code == 413
    assert row_count(h) == 1

    def fail(_stage):
        raise OSError("synthetic private audit path")

    h.work.fault_hook = fail
    try:
        reply = append(h, message="m" + "2" * 32, previous=1)
        assert reply.status_code == 503 and "private" not in reply.text
    finally:
        h.work.fault_hook = None
    assert row_count(h) == 1


def test_storage_failure_rolls_back_and_does_not_echo_sqlite_error(history):
    h = history
    data(create(h))
    h.connection.execute(
        "CREATE TRIGGER fail_event BEFORE INSERT ON os_conversation_v1_events BEGIN SELECT RAISE(ABORT,'private synthetic trigger'); END"
    )
    reply = append(h)
    assert reply.status_code == 503 and reply.json()["detail"] == "conversation_storage_unavailable"
    assert row_count(h) == 0 and "trigger" not in reply.text


def test_attempt_persists_before_history_and_lost_completion_is_reconciled_by_id(history):
    h = history
    data(create(h))
    commits = []

    def fail_second(stage):
        if stage == "before_commit":
            commits.append(stage)
            if len(commits) == 2:
                raise OSError("synthetic after-history audit failure")

    h.work.fault_hook = fail_second
    try:
        assert append(h).status_code == 503
    finally:
        h.work.fault_hook = None
    assert row_count(h) == 1
    assert data(append(h))["sequence"] == 1 and row_count(h) == 1
    rows = h.runtime._conn.execute(
        "SELECT kind,payload_json FROM work_v1_history WHERE kind LIKE 'conversation_history_%'"
    ).fetchall()
    assert sum(row[0] == "conversation_history_attempt" for row in rows) == 3
    assert sum(row[0] == "conversation_history_complete" for row in rows) == 2
    assert "An actual stored human message" not in str([tuple(row) for row in rows])


@pytest.mark.parametrize("revocation", ["device", "session"])
def test_revocation_serializes_after_inflight_history_commit(history, monkeypatch, revocation):
    h = history
    data(create(h))
    entered, release, revoked = threading.Event(), threading.Event(), threading.Event()
    original = h.journal.append

    def blocked(*args, **kwargs):
        entered.set()
        assert release.wait(4)
        return original(*args, **kwargs)

    monkeypatch.setattr(h.journal, "append", blocked)
    with h.devices.tx() as conn:
        token = h.devices.device(conn, h.alice.identity)["token"]

    def revoke():
        (
            h.authority.revoke(h.alice.identity)
            if revocation == "device"
            else h.issuer.revoke_session(token)
        )
        revoked.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        request = pool.submit(append, h)
        assert entered.wait(4)
        revoke_future = pool.submit(revoke)
        try:
            assert not revoked.wait(0.05)
        finally:
            release.set()
        assert request.result(timeout=5).status_code == 200
        revoke_future.result(timeout=5)
    assert revoked.is_set() and row_count(h) == 1
    assert read(h).status_code == 403


def test_logical_delete_is_owner_scoped_and_does_not_delete_audit(history):
    h = history
    data(create(h))
    data(append(h))
    data(create(h, h.bob))
    data(append(h, h.bob))
    before = h.runtime._conn.execute("SELECT COUNT(*) FROM audit").fetchone()[0]
    reply = data(h.alice.request("POST", PREFIX + "/" + THREAD + "/delete", {}))
    assert reply["deleted"] and reply["secure_erasure"] is False
    assert read(h).status_code == 404 and data(read(h, h.bob))["head_sequence"] == 1
    assert h.runtime._conn.execute("SELECT COUNT(*) FROM audit").fetchone()[0] > before


def test_all_three_stores_reopen_without_ddl_and_stored_message_survives(history):
    h = history
    data(create(h))
    data(append(h))
    # Restart the entire server-side graph, preserving only files and client key.
    h.client.close()
    h.connection.close()
    h.runtime._conn.close()
    h.owner_store._conn.close()
    reopened = h.reopen()
    h.alice.client = reopened.client
    assert data(read(h))["events"][0]["event"]["value"]["text"] == message_body()["text"]
    assert data(append(h))["sequence"] == 1


def test_pg_history_profile_is_explicitly_not_accepted(history):
    h = history
    h.work.pg = True
    try:
        assert create(h).status_code == 503
    finally:
        h.work.pg = False
    assert row_count(h) == 0


def test_official_pinned_agui_contract_accepts_only_expected_custom_envelope(history):
    from jsonschema import Draft202012Validator
    from referencing import Registry

    h = history
    folder = ROOT / "third_party/ag-ui-contract"
    raw = (folder / "schema-1.0.json").read_bytes()
    provenance = json.loads((folder / "PROVENANCE.json").read_text())
    assert hashlib.sha256(raw).hexdigest() == provenance["sha256"]
    schema = json.loads(raw)
    Draft202012Validator.check_schema(schema)
    custom = {**schema, "$ref": "#/$defs/CustomEvent"}
    validator = Draft202012Validator(custom, registry=Registry())
    data(create(h))
    data(append(h))
    event = data(read(h))["events"][0]["event"]
    assert list(validator.iter_errors(event)) == []
    for bad in [
        {"type": "CUSTOM", "name": "openbot.user_message.v1"},
        {**event, "authority": "approve"},
    ]:
        assert list(validator.iter_errors(bad))


def test_bounded_real_tls_socket_uses_normal_certificate_verification(history, tmp_path):
    import ipaddress
    import socket
    import ssl
    from datetime import UTC, datetime, timedelta

    import httpx
    import uvicorn
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    h = history
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Synthetic history TLS fixture")])
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(hours=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
            critical=False,
        )
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(key, hashes.SHA256())
    )
    certfile, keyfile = tmp_path / "synthetic-ca.pem", tmp_path / "synthetic-key.pem"
    certfile.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    keyfile.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    keyfile.chmod(0o600)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(8)
    origin = "https://127.0.0.1:" + str(sock.getsockname()[1])
    app = create_control_app(
        h.bridge,
        origin=origin,
        client_file=CLIENT_FILE,
        client_sha256=sha(CLIENT_FILE.read_bytes()),
        enabled=True,
    )
    ready = threading.Event()

    class Server(uvicorn.Server):
        async def startup(self, sockets=None):
            await super().startup(sockets=sockets)
            ready.set()

    server = Server(
        uvicorn.Config(
            app,
            ssl_certfile=str(certfile),
            ssl_keyfile=str(keyfile),
            log_config=None,
            access_log=False,
            lifespan="off",
        )
    )
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        assert ready.wait(5)
        context = ssl.create_default_context(cafile=str(certfile))
        with httpx.Client(base_url=origin, verify=context, trust_env=False, timeout=5) as client:
            fixture = SimpleNamespace(client=client, devices=h.devices)
            code = h.authority.issue_pairing(
                actor="human:alice",
                venture="alpha",
                role="owner",
                scopes=["read", *sorted(HISTORY_SCOPES)],
            )
            device = DeviceClient(fixture, code)
            assert (
                data(device.request("POST", PREFIX + "/create", create_body()))["thread_id"]
                == THREAD
            )
            assert (
                data(device.request("POST", PREFIX + "/" + THREAD + "/messages", message_body()))[
                    "sequence"
                ]
                == 1
            )
            result = data(
                device.request("POST", PREFIX + "/" + THREAD + "/read", {"after": 0, "limit": 50})
            )
            assert result["events"][0]["event"]["value"]["text"] == message_body()["text"]
            assert (
                client.post(
                    PREFIX + "/create",
                    json=create_body(),
                    headers={"Origin": "https://attacker.invalid"},
                ).status_code
                == 403
            )
        with (
            httpx.Client(base_url=origin, trust_env=False, timeout=5) as untrusted,
            pytest.raises(httpx.ConnectError),
        ):
            untrusted.get("/api/v1/identity")
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        sock.close()
    assert not thread.is_alive()
