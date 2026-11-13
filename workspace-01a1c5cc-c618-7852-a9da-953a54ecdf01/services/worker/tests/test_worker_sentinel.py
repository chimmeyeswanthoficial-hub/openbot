"""Tests for SentinelClient and Worker ↔ Sentinel integration."""

from __future__ import annotations

import pathlib
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "sentinel"))

from repository import Store  # noqa: E402
from runner import Worker  # noqa: E402
from sentinel_client import SentinelClient  # noqa: E402
from spec import parse  # noqa: E402

ROOT = pathlib.Path(__file__).parents[3]
ROUTINES = ROOT / ".openbot" / "routines"
SCOUT = (ROUTINES / "scout-daily.md").read_text()
VENTURED = parse(SCOUT.replace("tags: [scout, market, daily]", "tags: [scout]\nventure: media-api"))


def test_sentinel_client_decide_success():
    client = SentinelClient(base_url="http://test-sentinel:8090")
    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"decision": "allow", "rule": "default.allow", "reason": "ok"},
        )
        res = client.decide({"kind": "routine.run", "venture": "media-api", "cost_usd": 0.5})
        assert res["decision"] == "allow"
        assert res["rule"] == "default.allow"
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "http://test-sentinel:8090/v1/decide"
        assert kwargs["timeout"] == 5.0
        assert kwargs["json"]["venture"] == "media-api"


def test_sentinel_client_timeout_fails_closed():
    client = SentinelClient(base_url="http://test-sentinel:8090", timeout=5.0)
    with patch("httpx.post", side_effect=httpx.TimeoutException("timeout")):
        res = client.decide({"kind": "routine.run", "venture": "media-api"})
        assert res["decision"] == "deny"
        assert res["rule"] == "sentinel.unreachable"


def test_sentinel_client_5xx_fails_closed():
    client = SentinelClient(base_url="http://test-sentinel:8090")
    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=503,
            text="Service Unavailable",
        )
        res = client.decide({"kind": "routine.run", "venture": "media-api"})
        assert res["decision"] == "deny"
        assert res["rule"] == "sentinel.unreachable"


def test_worker_with_sentinel_deny_leaves_run_denied_and_writes_audit():
    store = Store()
    client = SentinelClient(base_url="http://test-sentinel:8090")
    with patch.object(
        client,
        "decide",
        return_value={
            "decision": "deny",
            "rule": "isolation.write_root",
            "reason": "outside venture root",
        },
    ):
        w = Worker(store=store, sentinel=client.decide, state_dir=str(ROUTINES.parent / "state"))
        w.specs = [VENTURED]
        out = w.dispatch("scout-daily", when=datetime(2026, 11, 10, 6, 0))
        assert out["ok"] is False
        assert out["code"] == "isolation.write_root"
        audit = store.audit_tail(1)[0]
        assert audit["decision"] == "deny"
        assert audit["rule"] == "isolation.write_root"


def test_worker_with_sentinel_timeout_leaves_run_refused_with_unreachable():
    store = Store()
    client = SentinelClient(base_url="http://test-sentinel:8090")
    with patch("httpx.post", side_effect=httpx.TimeoutException("timed out")):
        w = Worker(store=store, sentinel=client.decide, state_dir=str(ROUTINES.parent / "state"))
        w.specs = [VENTURED]
        out = w.dispatch("scout-daily", when=datetime(2026, 11, 10, 6, 0))
        assert out["ok"] is False
        assert out["code"] == "sentinel.unreachable"
        audit = store.audit_tail(1)[0]
        assert audit["decision"] == "deny"
        assert audit["rule"] == "sentinel.unreachable"

