---
name: ship-it
description: Take a change from green tests to running 24/7 — environments, canary order, migrations, rollback, health checks, alerts, cost, and the unattended-operation checklist. Use when deploying any service or venture, changing a schema, adding a cron/routine to production, or when setting up monitoring, backups, or incident response for a year of hands-off operation.
---

# Ship it

The goal is not "deployed". The goal is **deployed such that nobody needs to be awake for it**.

## Environments

| Env | Purpose | Data | Who can touch it |
|---|---|---|---|
| `sandbox` | throwaway per-run containers, one per venture run | synthetic only | agents, freely |
| `staging` | one shared, mirrors prod shape | anonymous snapshots | agents, with gates |
| `prod` | customers | real | humans for money/schema/secrets; agents only via gated deploys |

Never let an agent write to prod directly. It writes a **deploy request** (image sha + migration id
+ rollback sha); a deploy routine applies it after gates. That indirection is what makes 3 am safe.

## The deploy order (always this order)

1. **Build** once, tag by commit sha, push. Never build at deploy time.
2. **Migrate** with a backwards-compatible migration (expand → backfill → contract, never a
   destructive step in the same release).
3. **Canary** one instance / one computer, on the venture's least critical routine.
4. **Smoke**: health endpoint, one real read path, one gated write path (in staging), one
   acceptance test from the change's PR body.
5. **Roll to the rest**, watching error rate and p95 for 10 minutes.
6. **Tag the release** and write the sha into `.openbot/state/deployments.json`.

## Rollback that you have actually tested

- Every deploy records `{image_sha, migration_id, previous_sha}`. Rollback = redeploy previous sha;
  if a migration is not reversible, the deploy is not allowed to proceed without a human.
- Roll back on: health check failing twice, error rate > 2× baseline for 5 min, or any sev1 audit
  row. Automatic, no discussion. A pause is cheap; a bad night is not.
- Practise the rollback once per venture per quarter, in staging, with the same command.

## Health checks and alerts (minimum set per venture)

| Signal | Threshold | Action |
|---|---|---|
| `/healthz` | 2 consecutive failures | rollback + sev2 |
| error rate | > 2× 7-day baseline, 5 min | page, pause outbound |
| p95 latency | > SLO for 15 min | alert |
| queue depth / stuck runs | run older than `max_runtime_min` | kill run, postmortem |
| spend | > `budgets.day_usd` | pause venture, notify |
| auth failures | spike | possible key misuse, sev1 |
| backup age | > 26h | sev2 |
| routine didn't fire | missed by > 2× interval | sev2 |

Alerts must be **actionable and few**. An alert nobody acts on trains everyone to ignore the
channel, which is how unattended companies die.

## Backups and restore

- Postgres: nightly logical dump + PITR if available; keep 30 days; store encrypted off-host.
- **Restore drill monthly**, restore into staging, run the conformance suite, log the result to
  `.openbot/post_mortems/` as a `drill` record. An untested backup is a rumour.
- Venture sandboxes: ephemeral by design; anything a customer paid for must live in Postgres or
  object storage, never only in a container's disk.

## Cost

- Every service is labelled `venture=<slug>` so the infra bill can be split. Daily job writes COGS
  rows to the P&L ledger (see `venture-launch`).
- Cap the platform: per-venture `month_usd`, company monthly cap, and a hard
  "no new instance types / no new regions" rule for agents (that is a policy rule, not a hope).

## The unattended-operation checklist (the 1-year test)

- [ ] Every routine has `budget_usd`, `max_runtime_min`, `retry: 1`, an owner channel
- [ ] Every venture has kill criteria and a pause job that can flip `status: paused`
- [ ] Any sev1 auto-pauses the venture, not just logs
- [ ] Secrets rotate on a schedule; rotation is a routine with a test in staging
- [ ] Restore drill is green this month
- [ ] A "dead man's switch": if the control plane stops heartbeating for 2 hours, an external
      monitor emails the human (a company that cannot tell you it is dead is not running itself)
- [ ] Monthly review doc auto-generated from the ledger: revenue, margin, incidents, cost per
      venture — one page, human-readable, no adjectives
- [ ] The human's re-entry path is documented: how to pause everything in one command, and how to
      read the last 30 days in 10 minutes
