---
name: postmortem
description: Turn a failure into a durable prevention rule in the ledger, so the same class of mistake cannot recur. Use after any crash, failed deploy, bad customer-facing output, budget overrun, leaked key, missed schedule, or when a subagent failed the same step three times. Also use before starting a new venture, to read the ledger.
---

# Postmortem (the self-evolution loop)

The point is not the write-up. The point is that **the next run cannot make the same mistake**,
because the rule is enforced by code, a test, or a check that fails the build.

## When it fires

- any unhandled exception in a routine, worker, or agent run;
- three consecutive failures of the same step in one run (hard stop, per the guardrails);
- a deploy that broke a health check, a test, or a customer flow;
- any audit row with `decision: gate` that was approved **and was wrong**;
- a budget overrun (even $0.01);
- a scrubbed secret, a cross-venture access attempt, a sandbox escape;
- a customer-visible error or a wrong number quoted to a customer.

## The ledger entry

Append one line to `.openbot/post_mortems/error_registry.jsonl` (never rewrite history):

```json
{"id":"pm_2026_11_10_media_api_01",
 "ts":"2026-11-10T07:13:44Z",
 "venture":"media-api",
 "run_id":"r_01J...",
 "severity":"sev2",
 "class":"dependency-version-drift",
 "symptom":"ffmpeg split endpoint 500s on files > 200MB",
 "file":"services/media-api/app/media/split.py:88",
 "error":"CalledProcessError: ffmpeg exited 1 (buffer). stderr: ...",
 "root_cause":"temp partition on the sandbox is 512MB; large splits buffer to disk",
 "detection":"health check ran 4h late; user-facing 500 first",
 "impact":{"customers_affected":1,"revenue_usd":0,"duration_min":36},
 "fix":"stream to stdout with -f segment and caps; raise sandbox tmp to 2GB",
 "prevention_rule":"media: never write intermediate media to /tmp; use --fifo or pipes. Enforced by tests/test_media_large.py (fixture 250MB synthetic).",
 "rule_kind":"test",                     // test | policy | type | lint | prompt | routine-change
 "rule_ref":"services/media-api/tests/test_media_large.py::test_250mb_split",
 "verified_at":"2026-11-10T09:02:00Z"    // only when the failing test now passes on the old code
}
```

`rule_kind` must be one of `test`, `policy`, `type`, `lint`, `prompt`, `routine-change`.
A `prompt` rule is the weakest: it is accepted only when the same guarantee cannot be expressed as
code, and it must be added to the owning agent's standing instructions **and** a eval case in
`services/evals/cases/` that a nightly run checks.

## The four questions

1. **What did we believe that was false?** (Not "what failed" — the model of the world.)
2. **Why did our detection fail?** (If a customer found it first, that is the real incident.)
3. **Which layer could have caught it, and why didn't it?** type → test → CI → staging → health
   check → audit alert. Pick the **earliest** layer that plausibly catches the *class*.
4. **What now fails, every time, if someone does this again?** If the answer is "nothing", keep
   working. "Careful review" is not a prevention rule.

## Wiring the rule (the part people skip)

| rule_kind | Where it lands | Must also |
|---|---|---|
| `test` | the owning service's tests, failing on the pre-fix commit | the test name appears in the ledger entry |
| `policy` | `services/sentinel/policy/ventures/*.yaml` + a table test | reviewed by a human, never auto-merged |
| `type` | the narrowest type or schema that makes the bug unrepresentable | note the before/after signature |
| `lint` | a rule in the repo's biome/ruff config | applies to the whole repo, not one file |
| `prompt` | the agent's instructions **and** an eval case | the eval must fail on the old prompt |
| `routine-change` | the routine's front-matter/body | explain why the schedule, budget, or scope was wrong |

Then run `.claude/skills/postmortem/check.sh` (it verifies every ledger line has an id, a
`rule_kind`, a `rule_ref` that exists, and that `rule_ref` is green).

## Reading the ledger before new work

Before a new venture, a new agent, or a big refactor:

```sh
# classes that repeated, worst first
jq -r '.class' .openbot/post_mortems/error_registry.jsonl | sort | uniq -c | sort -rn | head
# rules a new agent must inherit
jq -r 'select(.rule_kind!="prompt") | "\(.class): \(.prevention_rule)"' .openbot/post_mortems/error_registry.jsonl
```

Put those rules into the new venture's `AGENTS.md` before writing feature code. An autonomous
company that repeats a mistake is not autonomous — it is unattended.

## Sev levels and who gets woken

| sev | Meaning | Response |
|---|---|---|
| sev1 | money lost, key leaked, customer data exposed, production down | page the human immediately (channel + email), auto-pause the venture, halt all routines for that venture |
| sev2 | one customer affected, or a venture's primary flow broken | pause that routine/goal, continue others, entry within 1h |
| sev3 | degraded or wrong output, no customer harm | entry within 24h, fix in next scheduled window |

Auto-pause is mandatory for sev1 and is implemented by the worker flipping
`ventures[x].status: paused` in Redis + writing the audit row. Never rely on the agent to stop
itself.
