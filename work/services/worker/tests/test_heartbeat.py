"""Tests for dead-man's switch heartbeat client (T8)."""

from __future__ import annotations

import pathlib
import sys
from unittest.mock import MagicMock, patch
from urllib.error import URLError

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from heartbeat import ping_deadman


def test_ping_empty_url_returns_false():
    assert ping_deadman("") is False
    assert ping_deadman("   ") is False


def test_ping_successful_200():
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        assert ping_deadman("https://hc-ping.com/fake-uuid") is True


def test_ping_network_failure_returns_false():
    with patch("urllib.request.urlopen", side_effect=URLError("connection refused")):
        assert ping_deadman("https://hc-ping.com/fake-uuid") is False
