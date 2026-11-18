"""Mapping table tests for OpenBot substrate actions (T2).

Tests each row in the mapping table from substrate tool call to Sentinel Action.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from mapper import map_substrate_action


def test_map_shell_exec():
    res = map_substrate_action("bash", {"command": "ls -la"}, bot_id="cto-bot")
    assert res["kind"] == "shell.exec"
    assert res["command"] == "ls -la"
    assert res["actor"] == "agent:cto-bot"


def test_map_file_write():
    res = map_substrate_action("save_file", {"path": "/workspace/test.txt", "content": "hello"}, bot_id="dev-bot")
    assert res["kind"] == "file.write"
    assert res["path"] == "/workspace/test.txt"
    assert res["payload"] == "hello"


def test_map_file_read():
    res = map_substrate_action("read_file", {"path": "/workspace/config.yaml"})
    assert res["kind"] == "file.read"
    assert res["path"] == "/workspace/config.yaml"


def test_map_browser_navigation():
    res = map_substrate_action("open_browser", {"url": "https://api.stripe.com/v1/prices"})
    assert res["kind"] == "browser.action"
    assert res["name"] == "navigate"
    assert res["url"] == "https://api.stripe.com/v1/prices"


def test_map_browser_click():
    res = map_substrate_action("click", {"selector": "#submit-btn"})
    assert res["kind"] == "browser.action"
    assert res["name"] == "click"


def test_map_money_charge():
    res = map_substrate_action("stripe.charge", {"amount": 25.50}, bot_id="cmo-bot")
    assert res["kind"] == "money"
    assert res["cost_usd"] == 25.50
    assert res["actor"] == "agent:cmo-bot"


def test_map_money_refund():
    res = map_substrate_action("refund_customer", {"amount": 19.00})
    assert res["kind"] == "money"
    assert res["cost_usd"] == 19.00


def test_map_http_request():
    res = map_substrate_action("http.request", {"url": "https://example.com/api", "method": "POST", "body": "data"})
    assert res["kind"] == "http.request"
    assert res["url"] == "https://example.com/api"
    assert res["method"] == "POST"
    assert res["payload"] == "data"


def test_map_mcp_send_email():
    res = map_substrate_action("gmail.send_message", {"body": "hello world"}, initiator="routine", initiator_id="scout-daily")
    assert res["kind"] == "mcp.call"
    assert res["name"] == "gmail.send_message"
    assert res["payload"] == "hello world"
    assert res["initiator"] == "routine"
    assert res["initiator_id"] == "scout-daily"


def test_map_mcp_slack_post():
    res = map_substrate_action("slack.post_message", {"channel": "#general", "message": "status update"})
    assert res["kind"] == "mcp.call"
    assert res["name"] == "slack.post_message"
    assert res["payload"] == "status update"

