# Documentation

Public source is owner-authorized; operation remains controlled development/private pilot.
Start with [`ADOPTION_REVIEW.md`](ADOPTION_REVIEW.md) and root
[`PROJECT_MEMORY.md`](../PROJECT_MEMORY.md); [`README.md`](../README.md) has the local demo.
General product launch still requires the 1–6-month real-world pilot and human review.

| Document | Read it when |
|---|---|
| [`ADOPTION_REVIEW.md`](ADOPTION_REVIEW.md) | current-source review, foundation choice, selected reuse and limits |
| [`plan.md`](plan.md) | you want the master plan, phases, effort matrix and the 365-day path |
| [`aboutme.md`](aboutme.md) | you want to know what this system is, what it costs, and how to manage it |
| [`advantages.md`](advantages.md) | you want the case for it, with mechanisms and measurements |
| [`disadvantages.md`](disadvantages.md) | you want the limits, the legal walls, and per-industry verdicts |
| [`FEATURES.md`](FEATURES.md) | you want the reverse-engineering sheet and the build order |
| [`BLOCKERS.md`](BLOCKERS.md) | you are deploying it and need the ordered path to a running company |
| [`STACK_DECISIONS.md`](STACK_DECISIONS.md) | you want to know why a choice was made (append-only) |
| [`INSTALL_LOG.md`](INSTALL_LOG.md) | you want the exact commands and what was verified |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | you want to change something |
| [`SECURITY.md`](SECURITY.md) | you found a vulnerability |
| [`PROJECT_STATE.md`](PROJECT_STATE.md) | you are taking over and need to know what exists (measured) |
| [`PROJECT_REMAINING.md`](PROJECT_REMAINING.md) | legacy task design; read the reviewed reconciliation first |
| [`STRATEGY_ADDENDUM.md`](STRATEGY_ADDENDUM.md) | newest direction, bounded improvement, private-pilot gates and source reviews |
| [`HANDOVER_CHECKLIST.md`](HANDOVER_CHECKLIST.md) | applying unpushed local repairs and resuming safely in Antigravity |

The canonical copy of every document above lives at the repository root (that is what contributors
open); `scripts/sync-docs.sh` copies them here so a published docs site can serve this folder alone.
`make verify` fails if the two copies disagree.
