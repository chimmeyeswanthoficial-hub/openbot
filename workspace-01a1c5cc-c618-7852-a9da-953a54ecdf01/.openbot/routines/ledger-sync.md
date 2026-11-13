---
id: ledger-sync
bot: ops
schedule: "*/30 * * * *"
timezone: Asia/Kolkata
budget_usd: 0.25
max_runtime_min: 10
retry: 2
approval: auto
initiator: routine
outputs:
  - channel: "#finance"
tags: [finance, ledger, ops]
---

# Sync the books (every 30 minutes)

## Act
1. Pull provider events since the last cursor. For each, write one `venture_ledger` row with the
   provider event id as `idempotency_key`. Replays must be no-ops.
2. Pull the infra bill for yesterday and write one `cogs` row per venture (idempotent by date+venture).
3. Compute `mrr`, `gross_margin`, `agent_cost` and write `.openbot/state/pnl.json`.
4. Reconcile: sum of revenue rows must equal the provider's reported gross, to the cent. If it
   does not, write one line with both numbers and raise sev2. Never adjust a row to make it match.

## Never
Never move money, never refund, never mark an invoice paid by hand, never edit a past row.
The ledger is append-only; a correction is a new `kind: adjustment` row with a reason.
