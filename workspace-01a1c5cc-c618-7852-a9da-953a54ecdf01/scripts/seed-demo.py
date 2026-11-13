#!/usr/bin/env python3
"""Seed a demo dataset so `make demo` shows a real, working control room without keys.

Everything below is written through the same validated paths the production code uses:
`pnl.validate_row` for money and `POST /v1/decide` for actions. Nothing is inserted with SQL, so
the demo cannot show a state the real system could not reach.

    python3 scripts/seed-demo.py                      # against http://127.0.0.1:8090
    python3 scripts/seed-demo.py --base http://host:8090
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

DECISIONS = [
    # (kind, venture, actor, initiator, initiator_id, name, kwargs)
    ("http.request", "media-api", "agent:ops", "routine", "ledger-sync", "read billing portal",
     {"url": "https://api.stripe.com/v1/invoices"}),
    ("http.request", "media-api", "agent:cto", "routine", "health-sweep", "check /healthz",
     {"url": "https://api.stripe.com/v1/health"}),
    ("mcp.call", "media-api", "agent:growth", "routine", "support-triage", "gmail.create_draft",
     {"url": "https://api.stripe.com/v1/drafts"}),
    ("mcp.call", "media-api", "agent:growth", "routine", "support-triage", "gmail.send_message",
     {"url": "https://api.stripe.com/v1/messages/send"}),
    ("file.write", "media-api", "agent:cto", "person", None, "",
     {"path": "/sandboxes/media-api/src/split.py"}),
    ("file.write", "media-api", "agent:cto", "routine", "health-sweep", "",
     {"path": "/sandboxes/other-venture/secrets.env"}),
    ("http.request", "media-api", "agent:ceo", "routine", "scout-daily", "scan IMDS",
     {"url": "http://169.254.169.254/latest/meta-data/"}),
    ("http.request", "media-api", "agent:cto", "person", None, "post charge",
     {"url": "https://api.stripe.com/v1/charges", "method": "POST",
      "payload": '{"api_key":"sk_live_THISISADEMOKEYNOTREAL0000"}'}),
    ("money", "media-api", "agent:ceo", "routine", "scout-daily", "buy a domain",
     {"cost_usd": 12.0}),
    ("http.request", "ghost-venture", "agent:unknown", "person", None, "probe",
     {"url": "https://api.stripe.com/v1/prices"}),
]

LEDGER = [
    # three settled subscriptions (one is a replay: same provider event id twice)
    {"venture": "media-api", "kind": "revenue", "amount_usd": 19.00, "source": "stripe",
     "external_id": "in_0001", "idempotency_key": "stripe:evt_0001",
     "meta": {"plan": "starter", "channel": "seo_long_tail"}},
    {"venture": "media-api", "kind": "revenue", "amount_usd": 79.00, "source": "stripe",
     "external_id": "in_0002", "idempotency_key": "stripe:evt_0002",
     "meta": {"plan": "growth", "channel": "github_readme"}},
    {"venture": "media-api", "kind": "revenue", "amount_usd": 19.00, "source": "stripe",
     "external_id": "in_0003", "idempotency_key": "stripe:evt_0003",
     "meta": {"plan": "starter", "channel": "seo_long_tail"}},
    {"venture": "media-api", "kind": "revenue", "amount_usd": 19.00, "source": "stripe",
     "external_id": "in_0001", "idempotency_key": "stripe:evt_0001", "meta": {"replay": True}},
    {"venture": "media-api", "kind": "refund", "amount_usd": 19.00, "source": "stripe",
     "external_id": "re_0001", "idempotency_key": "stripe:evt_0004"},
    {"venture": "media-api", "kind": "fee", "amount_usd": 3.42, "source": "stripe",
     "event": "balance_transactions", "idempotency_key": "stripe:evt_fees_week45"},
    {"venture": "media-api", "kind": "cogs", "amount_usd": 14.60, "source": "infra",
     "idempotency_key": "infra:2026-11-09"},
    {"venture": "media-api", "kind": "agent_cost", "amount_usd": 8.21, "source": "model-gateway",
     "idempotency_key": "models:2026-11-09"},
    {"venture": "media-api", "kind": "marketing", "amount_usd": 25.00, "source": "ads",
     "idempotency_key": "ads:2026-11-09"},
]


def call(method: str, url: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8090")
    args = ap.parse_args()
    base = args.base.rstrip("/")

    status, health = call("GET", f"{base}/healthz")
    if status != 200:
        print(f"sentinel not reachable at {base} (status {status})", file=sys.stderr)
        return 2
    if health.get("audit_rows", 0) > 0:
        print(f"already seeded ({health['audit_rows']} audit rows) — nothing to do")
        return 0

    tally = {"allow": 0, "gate": 0, "deny": 0}
    for kind, venture, actor, initiator, initiator_id, name, kw in DECISIONS:
        payload = {"kind": kind, "venture": venture, "actor": actor, "initiator": initiator,
                   "initiator_id": initiator_id, "name": name}
        payload.update(kw)
        st, out = call("POST", f"{base}/v1/decide", payload)
        if st != 200:
            print(f"  decide failed: {st} {out}", file=sys.stderr)
            continue
        tally[out["effect"]] = tally.get(out["effect"], 0) + 1

    created = replayed = 0
    for row in LEDGER:
        st, out = call("POST", f"{base}/v1/ledger", row)
        if st == 201:
            created += 1
        elif st == 200:
            replayed += 1
        else:
            print(f"  ledger refused: {st} {out}", file=sys.stderr)

    st, p = call("GET", f"{base}/v1/pnl")
    port = p.get("portfolio", {})
    print(f"seeded  decisions allow={tally['allow']} gate={tally['gate']} deny={tally['deny']}")
    print(f"        ledger  created={created} replays_ignored={replayed} rows={p.get('rows')}")
    print(f"        pnl     net=${port.get('net_revenue')} margin={port.get('gross_margin')} "
          f"contribution=${port.get('contribution')} agent_share={port.get('agent_share')}")
    print(f"open {base}/ to see it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
