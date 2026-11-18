"""Test-only profile. Never discovers/inherits a production DSN or destroys history."""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest
from repository import Store
from work_store import WorkStore

LIMITS = {"run": 1000, "company_day": 300, "company": 10000, "venture_day": 300, "venture": 10000}


@pytest.fixture(params=["sqlite", "pg"])
def durable_backend(request, tmp_path):
    clock = [time.time()]
    admin = None
    role, schema = None, None
    if request.param == "sqlite":
        dsn = str(tmp_path / "governed.sqlite3")
        owner = Store(dsn)
        owner_work = WorkStore(owner, initialize=True, clock=lambda: clock[0])
    else:
        dsn = os.environ.get("OPENBOT_TEST_POSTGRES_DSN", "")
        if not dsn or os.environ.get("OPENBOT_TEST_POSTGRES_ALLOW_WRITES") != "1":
            pytest.skip("explicit disposable PostgreSQL DSN and write opt-in required")
        parsed = urlsplit(dsn)
        query = dict(parse_qsl(parsed.query))
        socket = query.get("host", "")
        if (
            parsed.scheme not in {"postgres", "postgresql"}
            or not parsed.path.lstrip("/").startswith("openbot_fixture")
            or not socket.startswith("/")
            or Path(socket).stat().st_mode & 0o777 != 0o700
        ):
            pytest.fail(
                "refusing PG mutation before connection: private synthetic fixture required"
            )
        import psycopg2
        from psycopg2 import sql

        token = uuid.uuid4().hex[:16]
        schema, role = "ws_" + token, "wa_" + token
        admin = psycopg2.connect(dsn)
        admin.autocommit = True
        with admin.cursor() as cur:
            cur.execute("SELECT current_user,current_database()")
            user, database = cur.fetchone()
            cur.execute(
                sql.SQL("CREATE SCHEMA {} AUTHORIZATION {}").format(
                    sql.Identifier(schema), sql.Identifier(user)
                )
            )
            cur.execute(
                sql.SQL(
                    "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT"
                ).format(sql.Identifier(role))
            )
            # Catalog REVOKE is not safe to race across independent pytest invocations.
            cur.execute("SELECT pg_advisory_lock(5711232095842487862)")
            try:
                cur.execute(
                    sql.SQL("REVOKE CREATE,TEMPORARY ON DATABASE {} FROM PUBLIC").format(
                        sql.Identifier(database)
                    )
                )
            finally:
                cur.execute("SELECT pg_advisory_unlock(5711232095842487862)")
        query["options"] = "-csearch_path=" + schema
        owner_dsn = urlunsplit(("postgresql", user + "@", parsed.path, urlencode(query), ""))
        dsn = urlunsplit(("postgresql", role + "@", parsed.path, urlencode(query), ""))
        owner = Store(owner_dsn)
        owner_work = WorkStore(owner, initialize=True, clock=lambda: clock[0])
        with admin.cursor() as cur:
            cur.execute(
                sql.SQL("REVOKE ALL ON SCHEMA {} FROM PUBLIC").format(sql.Identifier(schema))
            )
            cur.execute(
                sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                    sql.Identifier(schema), sql.Identifier(role)
                )
            )
            for table in [
                "audit",
                "ledger",
                "work_v1_history",
                "work_v1_legacy",
                "work_v1_usage",
                "work_v1_events",
            ]:
                cur.execute(
                    sql.SQL("GRANT SELECT,INSERT ON {}.{} TO {}").format(
                        sql.Identifier(schema), sql.Identifier(table), sql.Identifier(role)
                    )
                )
            for table in [
                "runs",
                "approvals",
                "work_v1_tasks",
                "work_v1_sessions",
                "work_v1_outbox",
            ]:
                cur.execute(
                    sql.SQL("GRANT SELECT,INSERT,UPDATE ON {}.{} TO {}").format(
                        sql.Identifier(schema), sql.Identifier(table), sql.Identifier(role)
                    )
                )
            for table in ["work_v1_schema", "work_v1_limits"]:
                cur.execute(
                    sql.SQL("GRANT SELECT ON {}.{} TO {}").format(
                        sql.Identifier(schema), sql.Identifier(table), sql.Identifier(role)
                    )
                )
            cur.execute(
                sql.SQL("GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA {} TO {}").format(
                    sql.Identifier(schema), sql.Identifier(role)
                )
            )
            cur.execute(
                sql.SQL("REVOKE ALL ON ALL FUNCTIONS IN SCHEMA {} FROM PUBLIC").format(
                    sql.Identifier(schema)
                )
            )
    for venture in ["demo", "other", "platform"]:
        owner_work.configure(venture, LIMITS)
    store = Store(dsn, initialize=False)
    work = WorkStore(store, clock=lambda: clock[0])
    try:
        yield SimpleNamespace(
            kind=request.param,
            store=store,
            work=work,
            owner=owner,
            provision=owner_work,
            dsn=dsn,
            clock=clock,
            admin=admin,
            role=role,
            schema=schema,
            path=tmp_path,
        )
    finally:
        store._conn.close()
        owner._conn.close()
        if admin is not None:
            admin.close()
