"""AG-UI Routine Dispatcher for OpenBot OS (T3).

Executes scheduled routines against real or remote AG-UI Bot runtimes
(agent-bot, agent-langgraph, agent-mastra, agent-computer), enforces hard
runtime limits (max_runtime_min) and budget caps (budget_usd), delivers outputs
to specified channels/pages, and transitions run state (queued -> running -> succeeded).
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any, Callable

logger = logging.getLogger("worker.dispatch_agui")

DEFAULT_BOT_IMPL: dict[str, str] = {
    "ceo": "agent-bot",
    "growth": "agent-bot",
    "cto": "agent-langgraph",
    "ops": "agent-mastra",
    "auditor": "agent-computer",
}

DEFAULT_ENDPOINTS: dict[str, str] = {
    "agent-bot": "http://127.0.0.1:4200/ag-ui",
    "agent-langgraph": "http://127.0.0.1:4201/ag-ui",
    "agent-mastra": "http://127.0.0.1:4202/ag-ui",
    "agent-computer": "http://127.0.0.1:4203/ag-ui",
}


class AGUIDispatchError(Exception):
    pass


class AGUIDispatcher:
    def __init__(
        self,
        store: Any | None = None,
        endpoint_url: str | None = None,
        transport: Callable[[str, dict[str, Any], float], dict[str, Any]] | None = None,
    ) -> None:
        self.store = store
        self.endpoint_url = endpoint_url
        self._transport = transport or self._default_http_transport

    @staticmethod
    def resolve_impl(bot: str) -> str:
        return DEFAULT_BOT_IMPL.get(bot, "agent-bot")

    def endpoint_for(self, agent_impl: str) -> str:
        return self.endpoint_url or DEFAULT_ENDPOINTS.get(agent_impl, "http://127.0.0.1:4200/ag-ui")

    @staticmethod
    def _default_http_transport(url: str, payload: dict[str, Any], timeout_s: float) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "OpenBot-AGUI-Dispatcher/0.2.2"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise AGUIDispatchError(f"AG-UI HTTP {e.code}: {body}") from e
        except urllib.error.URLError as e:
            raise AGUIDispatchError(f"AG-UI unreachable at {url}: {e.reason}") from e

    def execute_turn(
        self,
        spec: Any,
        run_id: str,
        *,
        timeout_override_s: float | None = None,
    ) -> dict[str, Any]:
        """Dispatch a routine turn over AG-UI with strict limits and audit persistence."""
        venture = getattr(spec, "venture", None) or "platform"
        agent_impl = self.resolve_impl(spec.bot)
        endpoint = self.endpoint_for(agent_impl)
        max_timeout_s = timeout_override_s if timeout_override_s is not None else float(spec.max_runtime_min * 60)

        # 1. Transition run: queued -> running
        if self.store:
            self.store.end_run(run_id, "running", 0.0, f"dispatched to {agent_impl} at {endpoint}")

        payload = {
            "thread_id": f"routine_{spec.id}_{run_id}",
            "run_id": run_id,
            "bot": spec.bot,
            "agent_impl": agent_impl,
            "prompt": spec.body or f"Execute routine {spec.id}",
            "budget_usd": float(spec.budget_usd),
            "max_runtime_min": spec.max_runtime_min,
            "outputs": [dict(o) for o in getattr(spec, "outputs", [])],
        }

        started = time.time()
        try:
            resp = self._transport(endpoint, payload, max_timeout_s)
        except (TimeoutError, urllib.error.URLError) as e:
            elapsed = time.time() - started
            detail = f"killed: exceeded max_runtime_min ({spec.max_runtime_min}m)"
            if self.store:
                self.store.end_run(run_id, "killed", 0.0, detail)
                self.store.audit({
                    "run_id": run_id,
                    "venture": venture,
                    "action": "routine.run",
                    "decision": "deny",
                    "rule": "runtime.timeout_killed",
                    "reason": detail,
                    "initiator": {"kind": "routine", "id": spec.id},
                    "latency_ms": round(elapsed * 1000, 2),
                })
            return {
                "ok": False,
                "code": "routine.timeout",
                "run_id": run_id,
                "status": "killed",
                "reason": detail,
            }
        except Exception as e:
            elapsed = time.time() - started
            detail = f"failed: {e}"
            if self.store:
                self.store.end_run(run_id, "failed", 0.0, detail)
                self.store.audit({
                    "run_id": run_id,
                    "venture": venture,
                    "action": "routine.run",
                    "decision": "deny",
                    "rule": "runtime.error",
                    "reason": str(e),
                    "initiator": {"kind": "routine", "id": spec.id},
                    "latency_ms": round(elapsed * 1000, 2),
                })
            return {
                "ok": False,
                "code": "routine.failed",
                "run_id": run_id,
                "status": "failed",
                "error": str(e),
            }

        elapsed = time.time() - started
        reported_cost = float(resp.get("cost_usd") or 0.0)

        # Budget hard stop: check if cost exceeded routine budget
        if reported_cost > spec.budget_usd:
            detail = f"killed: budget exceeded (${reported_cost:.2f} > ${spec.budget_usd:.2f})"
            if self.store:
                self.store.end_run(run_id, "killed", reported_cost, detail)
                self.store.audit({
                    "run_id": run_id,
                    "venture": venture,
                    "action": "routine.run",
                    "decision": "deny",
                    "rule": "budget.exceeded_killed",
                    "reason": detail,
                    "cost_usd": reported_cost,
                    "initiator": {"kind": "routine", "id": spec.id},
                })
            return {
                "ok": False,
                "code": "budget.exceeded",
                "run_id": run_id,
                "status": "killed",
                "cost_usd": reported_cost,
                "reason": detail,
            }

        # Format delivered outputs
        raw_output = resp.get("output") or resp.get("message") or "routine executed successfully"
        delivered_outputs = []
        for o in getattr(spec, "outputs", []):
            d = dict(o)
            d["content"] = raw_output
            delivered_outputs.append(d)

        # 2. Transition run: running -> succeeded
        if self.store:
            self.store.end_run(run_id, "succeeded", reported_cost, f"completed in {elapsed:.1f}s")
            self.store.audit({
                "run_id": run_id,
                "venture": venture,
                "action": "routine.run",
                "decision": "allow",
                "rule": "routine.success",
                "reason": f"routine {spec.id} completed",
                "cost_usd": reported_cost,
                "initiator": {"kind": "routine", "id": spec.id},
                "latency_ms": round(elapsed * 1000, 2),
            })

        return {
            "ok": True,
            "run_id": run_id,
            "status": "succeeded",
            "bot": spec.bot,
            "agent_impl": agent_impl,
            "cost_usd": reported_cost,
            "outputs": delivered_outputs,
        }

