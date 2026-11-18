"""Sentinel HTTP Client for Worker dispatch boundary.

Guarantees fail-closed semantics: on timeout, network error, or 5xx,
returns a deny decision with rule 'sentinel.unreachable'.
"""

from __future__ import annotations

import os
from typing import Any

import httpx


class SentinelClient:
    """Client for querying the Sentinel governance policy service."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 5.0,
        token: str | None = None,
    ) -> None:
        self.base_url = (base_url or os.environ.get("SENTINEL_URL") or "http://127.0.0.1:8090").rstrip("/")
        self.timeout = timeout
        self.token = token or os.environ.get("SENTINEL_UI_TOKEN")

    def decide(self, action: dict[str, Any]) -> dict[str, Any]:
        """Judge an outward action via Sentinel POST /v1/decide. Fail closed on error."""
        url = f"{self.base_url}/v1/decide"
        headers: dict[str, str] = {}
        if self.token:
            headers["X-OpenBot-Token"] = self.token

        try:
            resp = httpx.post(url, json=action, headers=headers, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code >= 500:
                return {
                    "decision": "deny",
                    "rule": "sentinel.unreachable",
                    "reason": f"Sentinel error ({resp.status_code}): {resp.text[:100]}",
                }
            return {
                "decision": "deny",
                "rule": "sentinel.error",
                "reason": f"Sentinel rejected decision request ({resp.status_code}): {resp.text[:100]}",
            }
        except (httpx.TimeoutException, httpx.NetworkError, Exception) as err:
            return {
                "decision": "deny",
                "rule": "sentinel.unreachable",
                "reason": f"Sentinel request failed: {err}",
            }

