# advantages.md

**The positive case, stated precisely enough to be falsifiable.** Every advantage names its
mechanism, what it is measured against, and what it costs. If a claim here cannot be traced to a file
in this workspace, it is marketing and should be deleted.

---

## 1. Why this combination is different

The four products we studied each solve one slice. None of them is a company:

| Product | Its one great idea | What it lacks for running a business |
|---|---|---|
| **OpenBot** | Governance: every action resolved, policied, audited; per-bot computers; routines | No notion of a *business* — no P&L, no venture, no kill criteria |
| **Rakazo** | Markdown-first routines, memory, group chats, Pages, real clients | Personal-productivity shaped; governance is lighter |
| **OpenDots** | Review-before-save, per-tool permissions, Spaces | A template, not an operating company |
| **Grok Bot** | Teach-a-task by demonstration; always-on cloud computer | Closed; no audit, no policy, no ledger |
| **Muse Code** | Multi-agent by default + replayable event log | A coding harness only |

**OpenBot OS = OpenBot's governance + Rakazo's routine ergonomics + OpenDots' review gate + a venture
layer nobody has** (manifest → P&L ledger → kill criteria) **+ Muse's replayable traces** as the
evidence trail. The compounding asset is not the features; it is the **post-mortem ledger**, because
it is the only part that makes the company get *better* rather than just *busier*.

---

## 2. Advantages with a mechanism and a measurement

| # | Advantage | Mechanism (where it lives) | Measured against | Cost / catch |
|---|---|---|---|---|
| 1 | **Nothing acts without a decision that can be read later** | `policy.py` decide() → audit row, on every action | a human's memory of what they approved | ~10–20 ms per action; a policy file to maintain |
| 2 | **It cannot quietly spend money** | safety rules always gate money; `auto_spend_usd=0` pre-revenue; caps per venture/day/month | the usual failure of autonomous systems | you approve every charge until revenue exists |
| 3 | **It cannot leak a key it was never given** | protected paths denied; secrets scrubbed + escalated; per-run TTL credentials (M1) | .env on a laptop, keys in a repo | key injection adds a hop at the edge |
| 4 | **Failures become tests, not apologies** | post-mortem ledger → `rule_kind: test/policy/type/lint` → `check.sh` fails CI | a "lessons learned" doc nobody reads | honest root-cause work, ~30 min per incident |
| 5 | **Unattended work is distinguishable from attended work** | `initiator.kind` on every row; `Nobody watching` filter | a log that says "user did it" for a cron | none — it is one column |
| 6 | **Ventures cannot contaminate each other** | write roots, egress modes, separate ledgers and credentials per venture | one repo, one key, one blast radius | more setup per venture |
| 7 | **It works the hours you do not** | routines with a 15-minute floor, retries, health sweeps, incident watch | one person's working day | it must be *watched*, not trusted blindly |
| 8 | **It tells you it is dying** | two-signal dead-man's switch (control plane + routine completion) | "it was fine when I left" | an external monitor (~$5/mo) |
| 9 | **It can be fired in one command** | `scripts/pause-all.sh` + sev1 auto-pause | the alternative, a kill switch you never tested | you must rehearse it |
| 10 | **Your stack, your data, your exit** | self-hosted OpenBot + Postgres; AG-UI means any agent can be swapped in | lock-in to a hosted agent vendor | you operate it |
| 11 | **It gets cheaper per unit as it learns** | learned skills published after human approval; prevention rules stop repeat work | re-solving the same bug every month | skill review time |
| 12 | **It is auditable enough to sell** | role mandates, prohibitions, cost ceilings, audit rows, incident ledger | a customer's security questionnaire | you must actually read the audit |

---

## 3. Where it beats a human hire (honestly)

| Dimension | OpenBot OS | A human employee |
|---|---|---|
| Availability | 24/7, no burnout, no holidays | ~40 h/week, needs sleep |
| Consistency | same policy every time, no mood, no favourites | varies with stress and relationships |
| Auditability | every action has a row and a rule | memory, Slack, and goodwill |
| Ramp on documented work | hours (read the skill) | weeks |
| Cost at one-venture scale | ~$100–150/mo + 12 h of your time | one part-time operator + a contractor |
| Scale-out | duplicate the role, no hiring | hiring, onboarding, management |
| Context switching | unlimited | expensive |
| **Judgement under ambiguity** | **worse — it follows the spec** | **better** |
| **Relationships, negotiation, trust** | **absent** | **the whole point** |
| **Legal accountability** | **impossible** | **the reason companies exist** |

**Verdict:** it replaces the *recurring, documented, checkable* 60–70% of an operator's week — and
none of the 30% that needs a person. A company that swaps the first 60% for $150/mo and spends the
freed hours on the 30% is strictly better off. A company that tries to swap the 30% is in for a bad
year.

---

## 4. The compounding advantages (month 6+)

These are the reasons to build this rather than buy a hosted chatbot:

1. **The ledger of mistakes is an asset.** After 200 incidents with enforced rules, the company stops
   making entire *classes* of error. No hosted product can learn your specific failures.
2. **Playbooks become routines.** Every process you explain once is a markdown file that runs forever.
   Marginal cost of the next process approaches zero.
3. **Ventures share a spine.** The second venture reuses the policy engine, the worker, the ledger,
   the deploy pipeline. Launch cost drops by an order of magnitude.
4. **Evidence is sellable.** Enterprise buyers ask "what controls do you have?" — you can show roles,
   prohibitions, audit rows, cost ceilings, incident rules. That is a sales asset, not just hygiene.
5. **You can leave.** The 30-day dress rehearsal at the end of Phase 3 is the real product demo.

---

## 5. The three things that would make this a bad idea

Stated plainly so you can watch for them:

1. **If you do not clear the approvals queue**, it is an expensive idle company. The advantage
   evaporates in week two.
2. **If there is no channel**, it will build excellent products nobody buys. Agents cannot invent
   demand; budget and a human can.
3. **If you run three ventures at once**, none of them gets the attention, and the review becomes
   theatre. One until it pays.

If any of the three becomes true, stop and fix *that*, not the software.
