# Roadmap

Ordered by **what unblocks the most**, not by what is most fun. Each item names the check that will
prove it done. `[owner]` is the agent role from `company/company.yaml` that does the work.

## Now — M1 (weeks 1–4): make the substrate real

| # | Item | Proof it is done | Owner |
|---|---|---|---|
| 1 | Wire OpenBot's gateway to the Sentinel `decide()` (adapter, ~200 lines) | a gated send inside OpenBot appears in `/v1/approvals`, and approving it resumes the run | cto |
| 2 | Connect routine dispatch → OpenBot Bot over AG-UI | a routine fires at its cron time, a Bot answers, the output lands in its channel | cto |
| 3 | Deploy the compose stack on a Docker VPS (`BLOCKERS.md` B1–B8) | `make smoke` passes against the deployed host; `app:3010` reachable behind TLS | cto |
| 4 | Move the store to Postgres (one file: `repository.py`) | the same tests pass against Postgres; audit stays append-only | cto |
| 5 | Dead-man's switch on two signals | kill the control plane; an external monitor emails within the hour | ops |
| 6 | Approvals daily digest | one message per day listing what is waiting, with counts | growth |

## Next — M2 (weeks 5–10): the first venture, end to end

| # | Item | Proof | Owner |
|---|---|---|---|
| 7 | Venture SDK validation wired into the worker | a venture that fails `validate` cannot start | cto |
| 8 | Payment webhooks → ledger rows (Stripe test mode) | a test payment appears as a row; a replay is ignored; reconcile drift is $0.00 | ops |
| 9 | Media API: one endpoint, tests, status page | a real file converts; a 250 MB file does not hit the `/tmp` failure class | cto |
| 10 | Deploy pipeline: build → migrate → canary → rollback | a deliberate rollback executed once, successfully | cto |
| 11 | Support triage live (drafts only) | ten drafts in the queue, zero sends without an approval | growth |

## Later — M3 (weeks 11–20): reliability and the second engine

| # | Item | Proof | Owner |
|---|---|---|---|
| 12 | Eval harness for prompts and models | a prompt change is promoted only after ≥20 cases and no safety regression | cto |
| 13 | Restore drill (monthly, automated) | restored database into staging, conformance suite green, logged | ops |
| 14 | Ops console: cost per venture, incident rate, pause-all | one screen answers "is the company healthy" without SQL | cto |
| 15 | Second venture from the scout feed | it reaches `status: build` with an approved price | ceo |

## Later — M4/M5: scale, then leave

| # | Item | Proof | Owner |
|---|---|---|---|
| 16 | Teach-a-task with masking, in `deny_all` until reviewed | a recorded workflow becomes a routine that runs with no secrets captured | cto |
| 17 | Ticket board + webhook-triggered routines (Rakazo ports) | work arrives by event, not only by cron | cto |
| 18 | 30-day dress rehearsal | you leave for 30 days at ~$1k MRR and come back to a company | owner |

## Deliberately not on the roadmap

- **Autonomous entity formation, legal filings, tax positions.** `[human]` by law (`disadvantages.md` §2).
- **Autonomous price changes.** The highest-blast-radius decision in a company.
- **Agents sending mail or publishing without an approval.** Every queue-noise fix makes the queue
  faster; none removes the human from the send.
- **A marketplace of third-party skills.** Learning a skill is fine; shipping someone else's
  instructions into a company with a bank account is not, until there is a review process.
