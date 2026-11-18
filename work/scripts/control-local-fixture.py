#!/usr/bin/env python3
"""Explicit disposable HTTPS control fixture + TRUSTED LOCAL console commands.

No production DB/credentials discovered, no provider, no public deployment.
The fixture private directory is never included in source/evidence deliveries.
"""

from __future__ import annotations

import argparse
import datetime as dt
import ipaddress
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / part)
    for part in (
        "services/sentinel",
        "services/gateway/src",
        "services/ledger/src",
        "services/worker/src",
    )
]


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    path.chmod(0o600)


def initialize(folder, *, port, client):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
    from economic import Scope
    from economic_fixtures import charge, encoded, refund
    from economic_repository import EconomicBook
    from repository import Store
    from trust_crypto import digest, encode, sign
    from work_store import WorkStore

    if folder.exists() or any(p.is_symlink() for p in (folder, *folder.parents)):
        raise SystemExit("Refusing existing target or symlinked fixture path")
    folder.mkdir(mode=0o700, parents=True)
    client = client.resolve(strict=True)
    key = Ed25519PrivateKey.generate()
    (folder / "catalog-private.pem").write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    (folder / "catalog-private.pem").chmod(0o600)
    public = encode(key.public_key().public_bytes_raw())
    trusted = {
        "fixture-catalog": {"public_key": public, "roles": ["catalog-admin"], "revoked": False}
    }
    now = int(dt.datetime.now(dt.UTC).timestamp())
    authority = {
        "schema": "openbot.tool-authority/1",
        "epoch": 1,
        "not_before": now - 1,
        "expires": now + 3600,
        "revoked": [],
        "grants": {"demo": ["owned.qa"], "other": ["owned.qa"]},
    }
    write_json(folder / "catalog-authority.json", sign(key, "fixture-catalog", authority))
    write_json(folder / "catalog-trust.json", trusted)
    store = Store(str(folder / "work.sqlite3"))
    work = WorkStore(store, initialize=True)
    limits = {
        "run": 1000,
        "company_day": 300,
        "company": 10000,
        "venture_day": 300,
        "venture": 10000,
    }
    for venture in ["demo", "other", "platform"]:
        work.configure(venture, limits)
    book = EconomicBook(store, experimental=True)
    for venture, account, amount in [
        ("demo", "acct_controlfixture", 25000),
        ("other", "acct_otherfixture", 99999),
    ]:
        obj = charge(venture, amount)
        obj["metadata"]["venture"] = venture
        book.ingest(
            encoded("charge.succeeded", obj, "evt_control_" + venture, account),
            Scope(account, venture),
        )
    obj = refund("control", 5000, "demo")
    obj["metadata"]["venture"] = "demo"
    book.ingest(
        encoded("refund.created", obj, "evt_control_refund", "acct_controlfixture"),
        Scope("acct_controlfixture", "demo"),
    )
    store._conn.close()
    tls_key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "OpenBot disposable localhost fixture")]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(tls_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(dt.datetime.now(dt.UTC) - dt.timedelta(minutes=1))
        .not_valid_after(dt.datetime.now(dt.UTC) + dt.timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
            ),
            critical=False,
        )
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(tls_key, hashes.SHA256())
    )
    (folder / "tls-key.pem").write_bytes(
        tls_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    (folder / "tls-key.pem").chmod(0o600)
    (folder / "tls-cert.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    config = {
        "schema": "openbot.disposable-control-profile/1",
        "server_id": digest({"catalog-public": public}),
        "origin": f"https://localhost:{port}",
        "port": port,
        "source_root": str(ROOT),
        "client_file": str(client),
        "client_sha256": __import__("hashlib").sha256(client.read_bytes()).hexdigest(),
        "catalog_sha256": __import__("hashlib")
        .sha256((ROOT / "audit/first-party-tool-catalog.json").read_bytes())
        .hexdigest(),
        "minimum_catalog_epoch": 1,
        "synthetic_only": True,
        "production_authorized": False,
    }
    write_json(folder / "profile.json", config)
    profile = open_profile(folder)
    code = profile["authority"].issue_pairing(
        actor="human:local_fixture_owner",
        venture="demo",
        role="owner",
        scopes=["read", "propose", "approve", "execute", "cancel", "revoke-self"],
    )
    write_json(folder / "pairing-code.json", {"code": code, "synthetic_only": True})
    print(
        json.dumps(
            {
                "initialized": str(folder),
                "origin": config["origin"],
                "pairing_code_file": str(folder / "pairing-code.json"),
                "provider_started": False,
            }
        )
    )


def open_profile(folder):
    from control_api import ControlAuthority, ControlBridge, DeviceStore
    from economic import Scope
    from economic_repository import EconomicBook
    from governed_skills import ToolCatalog
    from repository import Store
    from work_service import WorkService
    from work_store import WorkStore

    if folder.is_symlink() or folder.stat().st_mode & 0o077:
        raise SystemExit("Private fixture directory required")
    config = json.loads((folder / "profile.json").read_text())
    if (
        config["schema"] != "openbot.disposable-control-profile/1"
        or config["synthetic_only"] is not True
        or config["production_authorized"] is not False
        or config["source_root"] != str(ROOT)
    ):
        raise SystemExit("Refusing a non-fixture or moved profile")
    setup_store = Store(str(folder / "work.sqlite3"), initialize=False)
    # Explicit fixture console path. Not a runtime migration for an external server.
    setup = WorkStore(setup_store, initialize=True)
    issuer = WorkService(setup, enabled=True)
    runtime_store = Store(str(folder / "work.sqlite3"), initialize=False)
    work = WorkService(WorkStore(runtime_store), enabled=True)
    devices = DeviceStore(folder / "devices.sqlite3", config["server_id"], initialize=True)
    authority = ControlAuthority(devices, issuer)
    catalog = ToolCatalog(
        ROOT,
        ROOT / "audit/first-party-tool-catalog.json",
        config["catalog_sha256"],
        folder / "catalog-authority.json",
        json.loads((folder / "catalog-trust.json").read_text()),
        minimum_epoch=config["minimum_catalog_epoch"],
    )
    book = EconomicBook(runtime_store, experimental=True, initialize=False)
    bridge = ControlBridge(
        devices,
        work,
        catalog,
        book=book,
        authority=authority,
        book_scopes={
            "demo": Scope("acct_controlfixture", "demo"),
            "other": Scope("acct_otherfixture", "other"),
        },
    )
    return {"config": config, "devices": devices, "authority": authority, "bridge": bridge}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=["init", "serve", "pairing", "reauth", "revoke", "devices"]
    )
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--ack-local-synthetic", action="store_true")
    parser.add_argument("--port", type=int, default=8443)
    parser.add_argument("--client", type=Path, default=ROOT.parent / "control/web/index.html")
    parser.add_argument("--device")
    parser.add_argument("--task")
    parser.add_argument("--digest")
    parser.add_argument("--venture", choices=["demo", "other"], default="demo")
    parser.add_argument("--role", choices=["owner", "viewer"], default="viewer")
    args = parser.parse_args()
    if not args.ack_local_synthetic:
        parser.error(
            "Explicit --ack-local-synthetic required; never use a production/private business profile"
        )
    folder = args.profile.absolute()
    if args.command == "init":
        if not 1024 <= args.port <= 65535:
            parser.error("Unprivileged port required")
        initialize(folder, port=args.port, client=args.client)
        return
    profile = open_profile(folder)
    if args.command == "serve":
        import uvicorn
        from control_api import create_control_app

        cfg = profile["config"]
        app = create_control_app(
            profile["bridge"],
            origin=cfg["origin"],
            client_file=cfg["client_file"],
            client_sha256=cfg["client_sha256"],
            enabled=True,
        )
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=cfg["port"],
            ssl_keyfile=str(folder / "tls-key.pem"),
            ssl_certfile=str(folder / "tls-cert.pem"),
            proxy_headers=False,
            server_header=False,
            access_log=False,
            limit_concurrency=32,
            timeout_keep_alive=5,
        )
    elif args.command == "devices":
        with profile["devices"].tx() as conn:
            print(
                json.dumps(
                    [
                        dict(r)
                        for r in conn.execute(
                            "SELECT id,actor,venture,role,expires,revoked,label FROM control_v1_devices"
                        )
                    ]
                )
            )
    elif args.command == "reauth":
        code = profile["authority"].issue_reauthentication(
            args.device, args.task, args.digest, human="human:local_fixture_owner"
        )
        print(json.dumps({"code": code, "expires_in_seconds": 120, "synthetic_only": True}))
    elif args.command == "revoke":
        print(json.dumps(profile["authority"].revoke(args.device)))
    elif args.command == "pairing":
        scopes = (
            ["read", "revoke-self"]
            if args.role == "viewer"
            else ["read", "propose", "approve", "execute", "cancel", "revoke-self"]
        )
        code = profile["authority"].issue_pairing(
            actor="human:local_fixture_owner", venture=args.venture, role=args.role, scopes=scopes
        )
        print(
            json.dumps(
                {"code": code, "role": args.role, "venture": args.venture, "synthetic_only": True}
            )
        )


if __name__ == "__main__":
    os.umask(0o077)
    main()
