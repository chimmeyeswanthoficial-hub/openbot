---
id: health-sweep
bot: cto
schedule: "*/15 * * * *"
timezone: Asia/Kolkata
budget_usd: 0.50
max_runtime_min: 10
retry: 1
approval: gate
initiator: routine
outputs:
  - channel: "#ops-alerts"
tags: [ops, health, cto]
---

# Health sweep (every 15 minutes)

## Read
1. Every active venture's `/healthz` and `/readyz`, plus p95 from the last 15 minutes.
2. Disk, memory, and container restart counts on the host (the sandbox is 80 GB; a full disk takes
   every venture down at once).
3. Backup age (`.openbot/state/backups.json`) — anything older than 26 hours is sev2.

## Act
- One failed health check → retry once after 60s. Two → restart the service, record sev2.
- Disk > 80% → delete the oldest sandbox artefacts only, record sev2, never touch Postgres or
  object storage.
- Anything that requires a code change → open an issue for the CTO, do not fix it here.

## Never
No deploys, no migrations, no `docker system prune -a`, no touching `.openbot/immutable/`.
