"""Fail-closed legacy transport seam; live network dispatch is NOT configured.

Only an explicitly injected trusted-host transport is callable. A reply is an
unverified draft, NOT AG-UI streaming, external delivery, a hard spend/runtime
limit, provider termination or settled accounting. Unknown outcomes require human
reconciliation and cannot be automatically retried under the same run ID.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit

DEFAULT_BOT_IMPL: dict[str, str] = {
    "ceo": "agent-bot", "growth": "agent-bot", "cto": "agent-langgraph",
    "ops": "agent-mastra", "auditor": "agent-computer",
}
DEFAULT_ENDPOINTS: dict[str, str] = {
    "agent-bot": "http://127.0.0.1:4200/ag-ui",
    "agent-langgraph": "http://127.0.0.1:4201/ag-ui",
    "agent-mastra": "http://127.0.0.1:4202/ag-ui",
    "agent-computer": "http://127.0.0.1:4203/ag-ui",
}


class AGUIDispatchError(Exception):
    pass


def _number(value, maximum):
    # Check the bounded range before converting a hostile huge int to float.
    return type(value) in (int, float) and 0 <= value <= maximum and math.isfinite(value)


def _identifier(value):
    return isinstance(value, str) and re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,95}", value)


class AGUIDispatcher:
    def __init__(self, store: Any | None = None, endpoint_url: str | None = None,
                 transport: Callable[[str, dict[str, Any], float], dict[str, Any]] | None = None):
        self.store, self.endpoint_url, self._transport = store, endpoint_url, transport

    @staticmethod
    def resolve_impl(bot: str) -> str:
        # Compatibility for read-only callers; execute_turn refuses unknown bots.
        return DEFAULT_BOT_IMPL.get(bot, "agent-bot")

    def endpoint_for(self, agent_impl: str) -> str:
        return self.endpoint_url or DEFAULT_ENDPOINTS[agent_impl]

    @staticmethod
    def _default_http_transport(*_args, **_kwargs):
        raise AGUIDispatchError("Live transport disabled until authenticated AG1/AG2 approval")

    @staticmethod
    def _reply(run_id, code, *, status="refused", ok=False, reported_cost=None, **extra):
        return {"ok": ok, "code": code, "run_id": run_id, "status": status,
                "cost_usd": None, "cost_basis": "unverified_or_unknown",
                "reported_cost_usd": reported_cost,
                "stop_confirmed": False, "delivery_confirmed": False,
                "delivery_status": "not_attempted", "reservation_enforced": False,
                "runtime_deadline_enforced": False, "automatic_retry_allowed": False,
                **extra}

    def execute_turn(self, spec: Any, run_id: str, *,
                     timeout_override_s: float | None = None) -> dict[str, Any]:
        """At most one stored attempt. Host injection is NOT remote authority.

        timeout is only an advisory argument to the injected callable. This seam
        cannot terminate a remote provider or even a misbehaving host callable.
        The default path refuses before any network call or attempt claim.
        """
        if self.store is None:
            return self._reply(run_id, "persistence.required")
        if not callable(self._transport):
            return self._reply(run_id, "runtime.unconfigured")
        try:
            venture = spec.venture if spec.venture is not None else "platform"
            budget, minutes = spec.budget_usd, spec.max_runtime_min
            if (not _identifier(run_id) or not _identifier(spec.id) or not _identifier(venture)
                    or not isinstance(spec.bot, str) or spec.bot not in DEFAULT_BOT_IMPL
                    or not _number(budget, 1_000_000) or not _number(minutes, 1440) or minutes == 0
                    or not isinstance(spec.body, str) or not spec.body.strip()
                    or len(spec.body.encode("utf-8")) > 65536):
                raise ValueError("invalid host plan")
            timeout = minutes * 60 if timeout_override_s is None else timeout_override_s
            if not _number(timeout, minutes * 60) or timeout == 0:
                raise ValueError("invalid advisory timeout")
            outputs = getattr(spec, "outputs", [])
            if not isinstance(outputs, list) or len(outputs) > 16:
                raise ValueError("invalid draft destinations")
            # Copy scalar destinations; no transport may alter the reviewed plan.
            destinations = []
            for output in outputs:
                if (not isinstance(output, dict) or not output or set(output) - {"channel", "page"}
                        or any(not isinstance(v, str) or not 1 <= len(v) <= 256 for v in output.values())):
                    raise ValueError("invalid draft destination")
                destinations.append(dict(output))
            impl = self.resolve_impl(spec.bot)
            endpoint = self.endpoint_for(impl)
            address = urlsplit(endpoint)
            if (address.scheme not in {"http", "https"} or not address.hostname
                    or address.username or address.password or address.fragment or address.query
                    or any(ord(c) < 33 for c in endpoint)):
                raise ValueError("invalid host endpoint")
            payload = {"thread_id": f"routine_{spec.id}_{run_id}", "run_id": run_id,
                       "bot": spec.bot, "agent_impl": impl, "prompt": spec.body,
                       "budget_usd": float(budget), "max_runtime_min": minutes,
                       # Destinations are metadata only, never a posting/delivery request.
                       "outputs": [dict(item) for item in destinations], "delivery_authorized": False}
            bound_id, bound_bot, bound_venture = spec.id, spec.bot, venture
            plan_sha = hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()
        except (AttributeError, ValueError, TypeError, OverflowError):
            return self._reply(run_id, "routine.invalid_plan")

        try:
            claimed = self.store.claim_run_dispatch(run_id, bound_id, bound_venture)
            if claimed is not True:
                return self._reply(run_id, "run.not_claimable")
            seq = self.store.audit({"run_id": run_id, "venture": bound_venture,
                                    "action": "routine.transport.attempt", "decision": "allow",
                                    "rule": "runtime.host_injected_attempt", "cost_usd": 0,
                                    "reason": "Host transport attempt; no remote stop, spend or delivery guarantee",
                                    "target": {"plan_sha256": plan_sha, "cost_basis": "unknown"},
                                    "initiator": {"kind": "routine", "id": bound_id}})
            if type(seq) is not int or seq <= 0:
                raise ValueError("unconfirmed pre-effect audit")
        except Exception:
            # The claim may already have persisted. Never clear it or guess safe retry.
            return self._reply(run_id, "persistence.unavailable", status="reconciliation_required")

        started = time.monotonic()

        def finish(code, *, reported=None, output=None):
            status = "response_received" if code == "runtime.response_received" else "reconciliation_required"
            detail = {"code": code, "cost_basis": "unknown", "reported_cost_usd": reported,
                      "stop_confirmed": False, "delivery_status": "not_attempted",
                      "automatic_retry_allowed": False, "reservation_enforced": False}
            try:
                seq = self.store.audit({"run_id": run_id, "venture": bound_venture,
                                        "action": "routine.transport.outcome",
                                        "decision": "allow" if output is not None else "deny",
                                        "rule": code, "reason": "Unverified host transport outcome; see bounded detail",
                                        "target": detail, "cost_usd": 0,
                                        "latency_ms": round((time.monotonic() - started) * 1000, 2),
                                        "initiator": {"kind": "routine", "id": bound_id}})
                if type(seq) is not int or seq <= 0 or self.store.finish_run_dispatch(
                        run_id, bound_id, bound_venture, status, json.dumps(detail, allow_nan=False)) is not True:
                    raise ValueError("outcome not persisted")
            except Exception:
                return self._reply(run_id, "persistence.outcome_unknown", status="reconciliation_required",
                                   reported_cost=reported)
            return self._reply(run_id, code, status=status, ok=output is not None,
                               reported_cost=reported, bot=bound_bot, agent_impl=impl,
                               outputs=[{**d, "content": output, "draft_only": True} for d in destinations]
                               if output is not None else [])

        try:
            response = self._transport(endpoint, payload, float(timeout))
        except TimeoutError:
            return finish("routine.timeout")
        except Exception:
            # Exception messages may contain credentials, endpoint queries or customer data.
            return finish("runtime.outcome_unknown")
        if not isinstance(response, dict):
            return finish("runtime.invalid_response")
        cost = response.get("cost_usd")
        if not _number(cost, 1_000_000):
            return finish("runtime.invalid_cost")
        reported = float(cost)
        if reported > budget:
            return finish("budget.exceeded", reported=reported)
        if time.monotonic() - started > timeout:
            return finish("routine.timeout", reported=reported)
        # Never synthesize text or accept ambiguous completion/error markers.
        output = response.get("output")
        try:
            if (not isinstance(output, str) or not output.strip() or len(output.encode("utf-8")) > 65536
                    or "message" in response or "error" in response
                    or ("ok" in response and response["ok"] is not True)
                    or ("run_id" in response and response["run_id"] != run_id)
                    or ("status" in response and (not isinstance(response["status"], str)
                                                 or response["status"] not in {"succeeded", "completed"}))):
                return finish("runtime.invalid_response", reported=reported)
        except (ValueError, TypeError):
            return finish("runtime.invalid_response", reported=reported)
        return finish("runtime.response_received", reported=reported, output=output)
