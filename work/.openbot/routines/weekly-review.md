---
id: weekly-review
bot: ceo
schedule: "0 8 * * 1"
timezone: Asia/Kolkata
budget_usd: 2.00
max_runtime_min: 40
retry: 1
approval: gate
initiator: routine
outputs:
  - channel: "#ops-daily"
  - page: "Reviews/{{year}}-W{{week}}"
tags: [review, ceo, weekly]
---

# Write the weekly review (Monday 08:00)

Numbers only, one page, then exactly one decision per venture. No adjectives.

## Read
`.openbot/state/pnl.json`, the week's audit rows, the post-mortem ledger, and each venture's
`venture.yaml` kill criteria.

## Write, in this order
1. **Money** — MRR, new/churned, COGS, gross margin, agent cost per venture. From rows only.
2. **Work** — routines fired vs scheduled (%), gated actions approved/denied, incidents by class.
3. **Learning** — post-mortems filed, rules enforced, rules still missing.
4. **Decision per venture** — `continue | fix | kill | scale`, with the number that decides it.

## Then
If any venture meets a kill criterion, say so in the first line and request the owner's signature.
Do not pause or kill anything yourself: `kill_venture` belongs to the owner.

## Failure path
If `pnl.json` is older than the review window, say `LEDGER STALE — numbers withheld` and stop.
A review with invented numbers is worse than no review.
