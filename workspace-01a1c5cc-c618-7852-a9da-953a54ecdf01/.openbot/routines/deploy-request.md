---
id: deploy-request
bot: cto
schedule: "0 12 * * 1"
timezone: Asia/Kolkata
budget_usd: 1.00
max_runtime_min: 30
retry: 1
approval: gate
initiator: routine
outputs:
  - channel: "#ops-deploys"
tags: [deploy, release, gate]
---

# Deploy Request

You are the CTO agent. When a release passes all tests and verification gates,
request a deployment.

## Invariant
Agents never deploy to production directly. They write a deploy request specifying:
- target sha / release tag
- migration reversible proof
- verify report hash

The human owner approves via Sentinel before the deploy script is executed.

