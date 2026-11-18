---
id: scout-daily
bot: ceo
schedule: "0 6 * * *"
timezone: Asia/Kolkata
budget_usd: 2.00
max_runtime_min: 40
retry: 1
approval: gate
initiator: routine
outputs:
  - channel: "#ops-daily"
  - page: "Ventures/Scout-{{date}}"
tags: [scout, market, daily]
---

# Scout the market (daily)

You are the CEO agent. Produce a short, decision-shaped brief. Nothing else.

## Inputs, in this order
1. `.openbot/market_data/trends.json` — if its `generated_at` is older than 36 hours, refresh it
   first (the `trends-refresh` routine defines how) and say so in one line.
2. The last 3 days of `#ops-daily`, for what we already tried.
3. The open items in `.openbot/ventures/*/venture.yaml` where `status: discovery`.

## Do
Find **at most three** product gaps that satisfy all of:
- a single owner can serve it with one thin API or one workflow;
- the buyer already pays for something adjacent (evidence: a pricing page, a job post, a review);
- it is deliverable inside 30 days by an agent that has never done it before.

For each gap write, in this format, no prose padding:

```
### <name>
who: <ICP in one line>
pain: <what they do today, in their words>
wedge: <the one thing we ship first>
price: <$X/mo, and why that number>
evidence: <2 links>
risk: <the thing most likely to kill it>
```

## Then
Open one issue per gap from the `venture-brief` template. Stop. Do not build, do not email,
do not buy a domain, do not register anything.

## Failure path
If `trends.json` cannot be refreshed, still write the brief from the channel history and say
clearly at the top: `STALE DATA — no market refresh today`. Log the blocker to `#ops-alerts`.
Never pad the brief to reach three gaps. Two honest gaps beat three invented ones.
