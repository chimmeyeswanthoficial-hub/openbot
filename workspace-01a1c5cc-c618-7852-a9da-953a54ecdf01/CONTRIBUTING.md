# Contributing

Thanks for looking. This project has one unusual rule that makes everything else easier:

> **Nothing merges that cannot fail a check.** A claim without a test is a rumour.

## The five-minute setup

```sh
python3 -m venv .venv && . .venv/bin/activate
make install
make test          # everything, ~2 s
make smoke         # boots the real service on a scratch DB and asserts 10 behaviours
make demo          # http://127.0.0.1:8090 with seeded rows
```

No Docker, no keys. The control plane is deliberately runnable by anyone.

## Where things live

```
services/sentinel/     the boundary: policy.py (decisions), repository.py (store), app.py (API+console)
services/ledger/       money from rows: pnl.py
services/worker/       routines: spec.py (parser), runner.py (dispatch decisions)
company/company.yaml   the org the runtime refuses to load if it is unsafe
.openbot/              runtime state: routines, ventures, post-mortems, budgets
.claude/skills/        the operating manual (read openbot-os first)
repos/                 upstream, read-only reference — never edit (see patches/)
```

## The four ways to contribute

| Kind | Where to start | What it must include |
|---|---|---|
| **A feature** | open an issue describing the *behaviour*, not the code | a test that fails before it and passes after |
| **A bug** | `make smoke` should be able to catch it — if it can't, add the check first | the failing check, in the same PR |
| **A policy rule** | `services/sentinel/policy.py` `SAFETY_RULES`, or a venture file in `policy/` | a table test for the *name shape*, not just one example |
| **A routine** | `.openbot/routines/*.md` | `budget_usd`, `max_runtime_min`, `initiator: routine`, a failure path, and `python3 -m pytest services/worker` green |

## The rules that are not negotiable

1. **No new outward action without a policy decision.** If your code calls the network, writes a
   file, spends, sends or publishes, it goes through `decide()` and produces an audit row.
2. **No new capability without a tag.** Update `aboutme.md` (`[shipped]`, `[M1–M3]`, `[human]`,
   `[never]`). `make verify` compares the tags against the tests.
3. **No incident without a rule.** `postmortem` skill: `rule_kind` must be `test`, `policy`, `type`,
   `lint`, `routine-change` — or `prompt` with an eval case. `scripts/verify.sh` enforces it.
4. **Never weaken a test to make a change pass.** That is the one thing we ask reviewers to look for
   first in a diff.
5. **Never edit `repos/`.** We keep upstream mergeable with thin seams (`upstream-merge` skill);
   `scripts/os-markers.sh --check` fails if a marker is undocumented.

## Commit and PR style

```
feat(worker): refuse a routine whose venture is paused

Why: an ignored approval must not look like work in progress.
Test: services/worker/tests/test_runner.py::test_a_paused_venture_stops_its_routines_and_says_so
Risk: none — new refusal path, no behaviour change for active ventures.
```

A PR body states **what could now go wrong**, in one sentence. "Nothing" is an acceptable answer only
if you say why.

## Reviewing

Look, in this order:

1. Does the diff touch files the description didn't name? (scope creep)
2. Does it delete or weaken a test? (`git diff --stat -- '**/tests/**'`)
3. Is there any new outward action, and does it have a policy + audit row?
4. Do the docs still tell the truth? (`make verify`)
5. Is the "what could go wrong" sentence honest?

## Reporting a vulnerability

Do not open a public issue. Email the owner with the failing case; we will add a test to
`services/sentinel/tests` and a rule to the post-mortem ledger before the fix ships.

## If you add a test, the documents notice

Every `N passed` claim in the newest `CHANGELOG` entry, `README.md` and `PROJECT_STATE.md` must equal
what `pytest --collect-only` reports; `test_contract.py` shells out to the collector and fails on a
mismatch in either direction. So when you add tests:

```sh
python3 -m pytest services packages -p no:warnings | tail -1   # the real number
# update the counts, then:
bash scripts/sync-docs.sh                                      # docs/ must not drift
make release-check
```

Do not "fix" a red count by editing the test — the number is downstream of the code, not the other
way round. Older changelog entries are left alone: they record what was true on their date.
