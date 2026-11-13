"""OpenBot tool action to Sentinel policy Action mapper (T2).

Translates substrate actions (browser navigation, computer actions, Composio tools,
shell execution, file operations) into canonical Sentinel `Action` payloads.
"""

from __future__ import annotations

import re
from typing import Any


def map_substrate_action(
    tool_name: str,
    args: dict[str, Any] | None = None,
    *,
    bot_id: str = "default",
    venture: str = "media-api",
    initiator: str = "person",
    initiator_id: str | None = None,
) -> dict[str, Any]:
    """Map a substrate/bot tool invocation to a Sentinel Action payload."""
    args = args or {}
    tool_lower = tool_name.lower().strip()
    actor = f"agent:{bot_id}"

    # 1. Shell / Command execution
    if tool_lower in ("bash", "shell", "terminal", "shell.exec", "command_run"):
        cmd = args.get("command") or args.get("cmd") or ""
        return {
            "kind": "shell.exec",
            "venture": venture,
            "actor": actor,
            "initiator": initiator,
            "initiator_id": initiator_id,
            "command": cmd,
            "name": tool_name,
        }

    # 2. File Writes
    if tool_lower in ("save_file", "file.write", "write_file", "edit_file", "append_file"):
        path = args.get("path") or args.get("filepath") or args.get("file") or ""
        payload = args.get("content") or args.get("text") or ""
        return {
            "kind": "file.write",
            "venture": venture,
            "actor": actor,
            "initiator": initiator,
            "initiator_id": initiator_id,
            "path": path,
            "payload": str(payload),
            "name": tool_name,
        }

    # 3. File Reads
    if tool_lower in ("read_file", "file.read", "cat", "view_file"):
        path = args.get("path") or args.get("filepath") or args.get("file") or ""
        return {
            "kind": "file.read",
            "venture": venture,
            "actor": actor,
            "initiator": initiator,
            "initiator_id": initiator_id,
            "path": path,
            "name": tool_name,
        }

    # 4. Browser Navigation & Actions
    if tool_lower in ("open_browser", "browser.navigate", "navigate", "browser_open"):
        url = args.get("url") or args.get("href") or ""
        return {
            "kind": "browser.action",
            "venture": venture,
            "actor": actor,
            "initiator": initiator,
            "initiator_id": initiator_id,
            "name": "navigate",
            "url": url,
        }
    if tool_lower.startswith("browser.") or tool_lower in ("click", "type", "screenshot", "scroll"):
        return {
            "kind": "browser.action",
            "venture": venture,
            "actor": actor,
            "initiator": initiator,
            "initiator_id": initiator_id,
            "name": tool_lower.replace("browser.", ""),
            "url": args.get("url"),
        }

    # 5. Financial / Money Moves
    money_words = ("charge", "payment", "pay", "refund", "transfer", "payout", "invoice.pay")
    if any(w in tool_lower for w in money_words):
        amount = float(args.get("amount") or args.get("amount_usd") or 0.0)
        return {
            "kind": "money",
            "venture": venture,
            "actor": actor,
            "initiator": initiator,
            "initiator_id": initiator_id,
            "name": tool_name,
            "cost_usd": amount,
            "url": args.get("url"),
        }

    # 6. HTTP Requests
    if tool_lower in ("http.request", "fetch", "curl", "api_call"):
        url = args.get("url") or ""
        method = args.get("method", "GET").upper()
        return {
            "kind": "http.request",
            "venture": venture,
            "actor": actor,
            "initiator": initiator,
            "initiator_id": initiator_id,
            "name": tool_name,
            "url": url,
            "method": method,
            "payload": str(args.get("body") or args.get("payload") or ""),
        }

    # 7. Generic MCP / Connected App / Composio Tool Call
    # By default, external connectors (gmail, slack, github, etc.) are treated as MCP calls
    return {
        "kind": "mcp.call",
        "venture": venture,
        "actor": actor,
        "initiator": initiator,
        "initiator_id": initiator_id,
        "name": tool_name,
        "url": args.get("url"),
        "payload": str(args.get("body") or args.get("payload") or args.get("message") or ""),
        "cost_usd": float(args.get("cost_usd") or 0.0),
    }

