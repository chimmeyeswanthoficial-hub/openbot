"""Exercise the REAL Sentinel response model through the worker HTTP-client seam.

In-process HTTP application transport; no real model, provider account or remote Bot.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from repository import Store
from runner import Worker
from sentinel_client import SentinelClient
from spec import parse


def test_real_sentinel_gate_is_not_queued_by_http_client_worker_seam():
    import app as service
    root = Path(__file__).parents[3]
    scout = (root / ".openbot/routines/scout-daily.md").read_text()
    spec = parse(scout.replace("tags: [scout, market, daily]", "tags: [scout]\nventure: media-api"))
    transport = TestClient(service.app)
    client = SentinelClient(base_url="http://in-process-sentinel")
    local_store = Store()
    with patch("httpx.post", side_effect=lambda url, **kw: transport.post("/v1/decide", json=kw["json"])):
        worker = Worker(store=local_store, sentinel=client.decide)
        worker.specs = [spec]
        reply = worker.dispatch(spec.id, when=datetime(2026, 11, 10, 6))
    assert reply["ok"] is False
    assert reply["approval_id"]
    assert local_store.runs(1)[0]["status"] == "gated"
    assert local_store.audit_tail(1)[0]["decision"] == "gate"
    assert service.store.get_approval(reply["approval_id"])["status"] == "pending"
