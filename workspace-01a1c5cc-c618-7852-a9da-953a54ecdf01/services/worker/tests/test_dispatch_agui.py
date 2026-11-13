"""Tests for AG-UI Routine Dispatcher (T3)."""

from __future__ import annotations

import pathlib
import sys
from dataclasses import dataclass, field

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "sentinel"))

from dispatch_agui import AGUIDispatcher
from repository import Store


@dataclass
class DummySpec:
    id: str = "scout-daily"
    bot: str = "ceo"
    venture: str = "media-api"
    budget_usd: float = 2.00
    max_runtime_min: int = 40
    body: str = "Scout the market"
    outputs: list[dict] = field(default_factory=lambda: [{"channel": "#ops-daily"}])


def test_dispatch_successful_turn():
    store = Store(":memory:")
    run_id = store.start_run("scout-daily", "media-api")

    def mock_transport(url, payload, timeout):
        assert payload["bot"] == "ceo"
        assert payload["agent_impl"] == "agent-bot"
        assert payload["budget_usd"] == 2.00
        return {"output": "Scouted 3 product gaps", "cost_usd": 0.45}

    dispatcher = AGUIDispatcher(store=store, transport=mock_transport)
    spec = DummySpec()
    res = dispatcher.execute_turn(spec, run_id)

    assert res["ok"] is True
    assert res["status"] == "succeeded"
    assert res["cost_usd"] == 0.45
    assert len(res["outputs"]) == 1
    assert res["outputs"][0]["channel"] == "#ops-daily"
    assert res["outputs"][0]["content"] == "Scouted 3 product gaps"

    # Verify run row in store
    runs = store.runs(1)
    assert len(runs) == 1
    assert runs[0]["id"] == run_id
    assert runs[0]["status"] == "succeeded"
    assert runs[0]["cost_usd"] == 0.45


def test_dispatch_timeout_kills_run():
    store = Store(":memory:")
    run_id = store.start_run("scout-daily", "media-api")

    def timeout_transport(url, payload, timeout):
        raise TimeoutError("timed out waiting for bot response")

    dispatcher = AGUIDispatcher(store=store, transport=timeout_transport)
    spec = DummySpec(max_runtime_min=10)
    res = dispatcher.execute_turn(spec, run_id)

    assert res["ok"] is False
    assert res["code"] == "routine.timeout"
    assert res["status"] == "killed"

    runs = store.runs(1)
    assert runs[0]["status"] == "killed"
    assert "exceeded max_runtime_min" in runs[0]["detail"]


def test_dispatch_budget_exceeded_kills_run():
    store = Store(":memory:")
    run_id = store.start_run("scout-daily", "media-api")

    def expensive_transport(url, payload, timeout):
        return {"output": "Did too much work", "cost_usd": 15.00}  # budget is $2.00

    dispatcher = AGUIDispatcher(store=store, transport=expensive_transport)
    spec = DummySpec(budget_usd=2.00)
    res = dispatcher.execute_turn(spec, run_id)

    assert res["ok"] is False
    assert res["code"] == "budget.exceeded"
    assert res["status"] == "killed"
    assert res["cost_usd"] == 15.00

    runs = store.runs(1)
    assert runs[0]["status"] == "killed"
    assert "budget exceeded" in runs[0]["detail"]


def test_dispatch_agent_impl_resolution():
    assert AGUIDispatcher.resolve_impl("ceo") == "agent-bot"
    assert AGUIDispatcher.resolve_impl("growth") == "agent-bot"
    assert AGUIDispatcher.resolve_impl("cto") == "agent-langgraph"
    assert AGUIDispatcher.resolve_impl("ops") == "agent-mastra"
    assert AGUIDispatcher.resolve_impl("auditor") == "agent-computer"
    assert AGUIDispatcher.resolve_impl("unknown") == "agent-bot"

