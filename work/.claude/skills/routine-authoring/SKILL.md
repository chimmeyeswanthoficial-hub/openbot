---
name: routine-authoring
description: Write, parse, schedule and review markdown "routines" — standing instructions stored as plain .md in an Obsidian vault that the FastAPI/OpenBot worker converts into governed agent loops. Use when writing a routine file, building the markdown parser, wiring the vault watcher, choosing a schedule, or debugging a routine that fired but did not do the right thing.
---

# Routine authoring

Rakazo's best user-facing idea is that an instruction is a **document**, not a YAML form.
OpenBot's best engineering idea is that a scheduled run is **governed, audited and attributable**.
We take both: markdown is the interface, the worker is the scheduler, the gateway is the boundary.

## File anatomy

Every routine is one `.md` file inside `.openbot/routines/` (symlinked into the Obsidian vault).
The front-matter is the machine contract; the body is the prompt the model actually receives.

```markdown
---
id: venture-scout-daily                  # stable, kebab-case, never reused
bot: ceo                                 # which persona runs it (see .openbot/agents/)
schedule: "0 6 * * *"                    # cron, 5 fields, min interval 15 min
timezone: Asia/Kolkata
budget_usd: 2.50                         # hard ceiling for this run; abort above it
max_runtime_min: 45
approval: gate                           # gate | auto | never (default gate)
outputs:
  - channel: "#ops-daily"
  - page: "Ventures/Scout-{{date}}"
initiator: routine                       # never "person" — a routine runs with nobody watching
tags: [scout, market, daily]
---

# Scout the market for this week

You are the CEO agent. Read `.openbot/market_data/trends.json` and last week's
`#ops-daily` thread. Identify **at most three** product gaps that:

1. can be served by a single-owner software product inside 30 days,
2. have a buyer who pays monthly (not one-off),

For each, open a Venture Brief issue using the `venture-brief` template, and stop. Do not
build anything in this run.

## Rules of engagement
- Never contact anyone outside the company.
- Never spend money. If a tool asks for a key, log the blocker and continue.
- If `trends.json` is older than 36 hours, refresh it first and say so.
```

## Hard rules

1. **`initiator: routine` is mandatory** and flows into the audit row, so an unattended run is
   always findable (`Nobody watching` filter). Never label a scheduled run as a person.
2. **`budget_usd` is mandatory.** The worker refuses to start a run whose declared budget exceeds
   the venture's remaining daily allowance in `.openbot/state/budget.json`.
3. **The body is a prompt, not a script.** If it needs branching, it belongs in a skill or a
   Python skill-fn, not in a 400-line markdown file.
4. **One outcome per routine.** "Research and publish and email" is three routines or one routine
   plus a goal — publishing and emailing are gated humans care about.
5. **Idempotence.** Every routine writes to a dated/idempotency-keyed destination so a re-run
   after a crash does not duplicate posts, invoices or outreach.
6. **Every routine states its own failure path**: what to log, whom to wake (channel), and
   whether to retry once (`retry: 1`) or stop.

## Parser contract (what we build in services/worker)

```text
watch .openbot/routines/**/*.md
  parse YAML front-matter  -> RoutineSpec (pydantic v2, strict, unknown key = error)
  validate                 -> cron parses, interval >= 15m, bot exists, budget present
  hash(body)               -> if unchanged since last run, skip re-embedding
  materialize              -> routine row + goal link (if `goal:` present)
  fire                     -> POST /runs with {routine_id, initiator: "routine", budget_usd}
  stream                   -> AG-UI events to the routine's channel
  on failure               -> append to error_registry.jsonl (see postmortem skill)
```

Front-matter schema lives in `services/worker/src/spec.py`. Any new key needs a migration note in
`STACK_DECISIONS.md` and a test in `services/worker/tests/test_spec.py`.

## Schedule grammar

| Need | Use | Don't |
|---|---|---|
| Daily market scan | `0 6 * * *` | `@daily` (not portable, no timezone clarity) |
| Every 15 min health sweep | `*/15 * * * *` | sub-15min (worker floor refuses) |
| Weekday standup | `30 9 * * 1-5` | separate Mon–Fri files |
| "Whenever something happens" | a **goal with a trigger**, not a cron | a 1-minute cron that polls |

A routine fires the work; a **goal** owns whether the work is finished. Repeating goals are never
completed by one of their runs — record progress with `report_goal_progress` and let a person
close it.

## Review checklist (before you commit a routine file)

- [ ] `id` unique across the vault (`grep -r "^id: <id>$" .openbot/routines`)
- [ ] `budget_usd` ≤ remaining venture allowance for the day
- [ ] Body names its inputs and its single outcome
- [ ] Body names the failure path and the channel to wake
- [ ] Nothing in the body sends, pays, publishes or deletes without `approval: gate`
- [ ] Dry run once: `python services/worker/tools/dry_run.py <file>` prints the run plan, the
      tools it would call, and the cost estimate. Paste that output into the PR.

## Anti-patterns seen in the wild

- **The infinite researcher**: a routine that reads all day and produces nothing a customer sees.
  Cap it: `max_runtime_min` plus "stop after N findings".
- **The hidden spend**: a browser tool that signs up for a free trial. Egress filter + `budget_usd`.
- **The silent zombie**: a routine whose channel was archived; its output goes nowhere. The worker
  warns when the destination channel is archived or the page path's parent does not exist.
- **The prompt-shaped script**: `if`/`else` chains in markdown. Move to a skill.
