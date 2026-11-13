"""OpenBot Gateway Adapter (T2).

Intercepts substrate agent tool execution before the action is executed,
queries Sentinel for a governance verdict, and formats AG-UI interrupt cards on gate.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from mapper import map_substrate_action

logger = logging.getLogger("gateway.adapter")


class GatewayAdapter:
    def __init__(
        self,
        decide_fn: Callable[[dict[str, Any]], dict[str, Any]],
        resolve_fn: Callable[[str, str, str, str | None], bool] | None = None,
    ) -> None:
        self._decide = decide_fn
        self._resolve = resolve_fn

    def intercept(
        self,
        tool_name: str,
        args: dict[str, Any] | None = None,
        *,
        bot_id: str = "default",
        venture: str = "media-api",
        initiator: str = "person",
        initiator_id: str | None = None,
    ) -> dict[str, Any]:
        """Judge an impending tool execution against Sentinel policy."""
        action = map_substrate_action(
            tool_name,
            args,
            bot_id=bot_id,
            venture=venture,
            initiator=initiator,
            initiator_id=initiator_id,
        )

        try:
            decision = self._decide(action)
        except Exception as e:
            logger.error("Sentinel decision failed closed for %s: %s", tool_name, e)
            return {
                "status": "denied",
                "rule": "gateway.error_fail_closed",
                "reason": f"governance check failed: {e}",
            }

        effect = decision.get("effect") or decision.get("decision")
        run_id = decision.get("run_id", "")
        rule = decision.get("rule", "unknown")
        reason = decision.get("reason", "")
        approval_id = decision.get("approval_id")

        if effect == "allow":
            return {"status": "allowed", "run_id": run_id, "rule": rule}

        if effect == "deny":
            return {
                "status": "denied",
                "run_id": run_id,
                "rule": rule,
                "reason": reason,
            }

        if effect == "gate":
            card = {
                "type": "card",
                "card": "approval",
                "approval_id": approval_id,
                "run_id": run_id,
                "tool": tool_name,
                "status": "pending",
                "rule": rule,
                "reason": reason,
                "cost_usd": action.get("cost_usd", 0.0),
            }
            return {
                "status": "gated",
                "run_id": run_id,
                "approval_id": approval_id,
                "rule": rule,
                "reason": reason,
                "card": card,
            }

        # Unknown effect fails closed
        return {
            "status": "denied",
            "rule": "gateway.unknown_effect",
            "reason": f"unrecognized governance effect: {effect!r}",
        }

    def resolve(
        self,
        approval_id: str,
        verdict: str,
        by: str = "human:owner",
        note: str | None = None,
    ) -> bool:
        """Resolve an approval through the Sentinel boundary."""
        if not self._resolve:
            raise RuntimeError("No resolve function provided to GatewayAdapter")
        return self._resolve(approval_id, verdict, by, note)

