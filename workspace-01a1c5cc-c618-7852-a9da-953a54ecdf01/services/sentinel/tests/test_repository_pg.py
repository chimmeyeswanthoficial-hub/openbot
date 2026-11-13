"""PostgreSQL backend tests for Sentinel Store (T4).

Skipped when DATABASE_URL is not set. Runs against live Postgres when configured.
"""

from __future__ import annotations

import concurrent.futures
import os
import uuid

import pytest

from repository import Store

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SENTINEL_DB", "")
pytestmark = pytest.mark.skipif(
    not (DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")),
    reason="DATABASE_URL not configured for PostgreSQL",
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

