"""PostgreSQL backend tests for Sentinel Store (T4).

Skipped by default. Requires a deliberately provisioned disposable test database;
production DATABASE_URL/SENTINEL_DB values are never used for test writes.
"""

from __future__ import annotations

import concurrent.futures
import os
import uuid

import pytest
from repository import Store

# Never borrow a production DATABASE_URL/SENTINEL_DB to execute mutating tests.
DATABASE_URL = os.environ.get("OPENBOT_TEST_POSTGRES_DSN", "")
pytestmark = pytest.mark.skipif(
    os.environ.get("OPENBOT_TEST_POSTGRES_ALLOW_WRITES") != "1"
    or not DATABASE_URL.startswith(("postgres://", "postgresql://")),
    reason="disposable OPENBOT_TEST_POSTGRES_DSN and explicit test write opt-in are required",
)


@pytest.fixture()
def pg_store():
    store = Store(DATABASE_URL)
    return store


def test_pg_audit_append_only(pg_store):
    run_id = f"test_run_{uuid.uuid4().hex[:8]}"
    seq = pg_store.audit({
        "run_id": run_id,
        "venture": "media-api",
        "actor": "agent:test",
        "action": "http.request",
        "decision": "allow",
        "rule": "test.rule",
        "reason": "testing postgres",
    })
    assert seq > 0
    tail = pg_store.audit_tail(limit=5, venture="media-api")
    assert any(r["run_id"] == run_id for r in tail)


def test_pg_resolve_approval_lost_race(pg_store):
    aid = f"ap_race_{uuid.uuid4().hex[:8]}"
    pg_store.create_approval({
        "id": aid,
        "run_id": "r_123",
        "venture": "media-api",
        "rule": "test.race",
        "reason": "testing race",
    })

    results = []

    def try_resolve(caller_id: int):
        return pg_store.resolve_approval(aid, "approved", f"human:{caller_id}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(try_resolve, i) for i in range(10)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    # Exactly one caller wins, 9 lose
    assert results.count(True) == 1
    assert results.count(False) == 9

