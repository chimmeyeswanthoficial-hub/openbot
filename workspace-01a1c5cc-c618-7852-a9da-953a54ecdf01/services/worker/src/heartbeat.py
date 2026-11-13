"""Dead-man's switch heartbeat client (T8).

Pings an external monitoring URL (e.g., Healthchecks.io / DEADMAN_PING_URL)
on successful tick / health sweep. If the worker stops ticking, the external
service raises an alert.
"""

from __future__ import annotations

import urllib.error
import urllib.request


def ping_deadman(url: str, *, timeout: float = 5.0) -> bool:
    """Send heartbeat ping to dead-man's switch monitor. Returns True on 2xx/3xx."""
    if not url or not url.strip():
        return False
    try:
        req = urllib.request.Request(url.strip(), headers={"User-Agent": "OpenBot-DeadMan/0.2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 400
    except (urllib.error.URLError, OSError, ValueError):
        return False

