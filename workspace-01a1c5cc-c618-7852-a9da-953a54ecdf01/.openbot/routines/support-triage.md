---
id: support-triage
bot: growth
schedule: "0 * * * *"
timezone: Asia/Kolkata
budget_usd: 1.00
max_runtime_min: 20
retry: 1
approval: gate
initiator: routine
outputs:
  - channel: "#support"
tags: [support, growth]
---

# Triage the inbox (hourly)

## Read
1. Unread support mail and `#support` for the last hour.
2. The venture's status page and known-issues list.

## Act
- Classify each message: `question | bug | billing | churn-risk | abuse | legal`.
- **Draft** a reply for every one. Drafts only: `gmail.create_draft`, never `send`.
- `bug` → open an issue with the exact request id, and link it in the draft reply.
- `billing` or `churn-risk` → draft, mark `needs_human: billing`, and say so in `#support`.
- `legal` or `abuse` → do not draft content. Escalate immediately; a human decides.
- Two customers reporting the same thing → open a sev2 issue, not sev1 (the auditor owns sev1).

## Never
Never send, never promise a date, never offer a refund, never speak as the founder, never quote
a metric that is not in the ledger.
