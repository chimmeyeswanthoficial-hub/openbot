---
name: venture-launch
description: Take a business from idea to first settled revenue inside OpenBot OS — venture manifest, unit economics, offer, channel, pricing, launch checklist, P&L ledger rows and kill criteria. Use when registering a new venture, deciding what to sell, pricing, writing the go-to-market, reviewing a venture's P&L, or deciding whether to pause/kill one.
---

# Venture launch

An autonomous company fails in one of two ways: it ships things nobody pays for, or it cannot tell
whether it is making money. This skill exists to make both impossible.

## The manifest is the contract

`.openbot/ventures/<slug>/venture.yaml` — validated by `packages/venture-sdk`. Nothing runs
without it.

```yaml
slug: media-api
name: "Media API"
owner_agent: ceo
status: discovery          # discovery -> build -> launched -> scaling -> paused -> killed
thesis: >
  Small teams need one HTTP call to convert/split/compress media, and will pay monthly
  instead of operating ffmpeg. We sell reliability, not features.
icp: "indie SaaS + agencies, 1-20 people, already paying for one API"
wedge: "one endpoint, one price, no dashboard required to start"
pricing:
  model: metered_subscription
  plans: [{name: starter, usd_month: 19, included_units: 5000, overage_usd: 0.004},
          {name: growth,  usd_month: 79, included_units: 40000, overage_usd: 0.003}]
unit_economics:
  cogs_per_1k_units_usd: 0.12      # compute + storage + egress, measured not guessed
  target_gross_margin: 0.80
  cac_target_usd: 40
  payback_months_target: 3
channels: [seo_long_tail, github_readme, cold_email_readonly]
budgets:
  day_usd: 3.00
  month_usd: 60.00
  auto_spend_usd: 0.00            # anything above $0 needs a human while pre-revenue
guardrails:
  egress_mode: allowlist_only
  data_class: public             # public | customer_pii | internal
  hitl: always_money, always_outbound_message
kill_criteria:
  - "no paying customer within 45 days of launch"
  - "gross margin < 55% for two consecutive months"
  - "cogs > 40% of revenue for a week"
ledger_account: acct_media_api    # payment-provider account or sub-account id (never a key)
```

Rules: `auto_spend_usd` starts at **0** and only a human raises it. `cogs_per_1k_units_usd` is
measured from the first 100 calls, then corrected in a PR — a guessed margin is a lie that scales.

## The 10-step launch path (each step has an exit artifact)

| # | Step | Artifact that proves it | Gate |
|---|---|---|---|
| 1 | Problem evidence | 5 quotes/links from real buyers (forums, job posts, reviews) | human reads |
| 2 | Offer | one page: who, pain, promise, price, proof | — |
| 3 | Landing + checkout | live URL, a real $ test transaction refunded | human |
| 4 | Thin slice | the one endpoint/feature the offer names, with tests | CI green |
| 5 | Trust surface | status page, terms, refund policy, data handling note | — |
| 6 | Instrumentation | signup → activation → paid funnel rows in the ledger | — |
| 7 | First 20 conversations | outreach log with replies (read-only reply handling) | human per send |
| 8 | First payment | settlement row in the P&L ledger | human |
| 9 | Delivery reliability | p95 latency + error budget + on-call routine | — |
| 10 | Repeatable acquisition | one channel with CAC < payback × margin | review |

Stop at step 3 until a human approves the price. Price changes are never autonomous: they are the
single highest-leverage and highest-blast-radius decision in the company.

## What must be true before anything is "launched"

- [ ] Manifest validates (`python -m venture_sdk validate .openbot/ventures/<slug>`)
- [ ] Sentinel policy exists for the venture, with tests for the money and outbound-message paths
- [ ] The venture's sandbox path is isolated; no shared credential with another venture
- [ ] A human has approved the pricing table and the refund policy
- [ ] Refund path exists and has been exercised once in test mode
- [ ] A health-check routine exists and is ≤ 15 min cadence
- [ ] The ledger writes on **webhook**, not on the agent's claim of a sale
- [ ] Kill criteria are written, dated, and readable by the pause job

## The P&L ledger (the only source of truth)

Append-only rows in Postgres (`venture_ledger`), double-entry-ish:

```json
{"ts":"...","venture":"media-api","kind":"revenue|refund|cogs|marketing|infra|fee",
 "amount_usd":19.00,"currency":"USD","source":"stripe:evt_1Q...","external_id":"in_1Q...",
 "attribution":{"plan":"starter","channel":"seo_long_tail"},"idempotency_key":"stripe_evt_1Q..."}
```

- `idempotency_key` unique index: a replayed webhook can never double-count revenue.
- MRR = trailing 30-day recurring rows, minus refunds. Computed nightly into
  `.openbot/state/pnl.json`, which the dashboard reads. Never hand-edited.
- COGS rows come from the infra billing API daily (one routine, idempotent by date).

## Kill / scale decisions (weekly, human-signed)

| Signal | Action |
|---|---|
| 0 paying customers at day 45 post-launch | kill or re-cut the offer; do not add features |
| CAC payback > 6 months | stop the channel, not the venture |
| gross margin < 55% | raise price or cut cogs; pause outbound |
| one channel producing > 60% of new revenue | invest + build a second before scaling spend |
| a venture at 3× its month budget | auto-pause; human review |

## Anti-patterns

- **Building the dashboard first.** Ship the endpoint; the status page is the dashboard.
- **"Revenue" from free trials.** Only settled revenue counts; trials are `pipeline`, tracked
  separately and never summed into revenue.
- **The vanity venture.** A venture with no ICP and no price is a hobby with a manifest.
- **Autonomous price cuts to "get traction."** Price is gated for a reason.
