# AG4A-01 — offline synthetic canonical capture/refund book

**Status:** local, default-off technical fixture implementation. It is not live Stripe integration, business revenue, a functional-currency/recognition/tax decision, bank-settlement proof, production database migration or release approval. Measured results are in `result.md` and `audit/verification-current.json`; a design/schema alone proves no execution.

## Qualified fixture contract

- Provider-shaped fixtures use API **`2024-06-20`**, with locally authored accepted-subset schema `services/ledger/fixtures/stripe-2024-06-20.schema.json` and source/hash catalogue `audit/fixture-profiles/stripe-2024-06-20.json`.
- Static generated type references are Stripe's MIT-licensed `stripe-python` **v10.12.0**, immutable commit **`3587026b839435d072b7d220967c476d4c6b9a9b`**. The pinned `_api_version.py` declares `2024-06-20`. Reference files and their license are preserved in the engineering evidence bundle, not imported or installed. These references do not certify complete provider conformance.
- The schema describes accepted, completed synthetic facts; executable validation is deliberately stricter about lexical integer amounts, byte/depth limits, cross-object equality, host scope and transactional invariants. No JSON-schema URL, SDK, provider or object lookup is invoked at runtime.
- Only USD/test mode is supported. Money is a non-boolean Python integer in minor units, `0..2^53−1`. That is an exact JSON representation bound, **not a spending budget**. Zero is not replaced through truthiness. Floats, strings, negatives, nonfinite values, overflow and other/missing currencies are refused. Aggregation uses integers; unsafe aggregate bounds are reported, never rounded into a believable total.

## Identity and scope

Notification identity is `(provider, host account, test environment, event ID)`. It has an immutable raw-body SHA-256 and retained processing result. Canonical posting identity is independently `(provider, host account, test environment, capture/refund kind, economic ID)`. **Amount, currency, venture and links are immutable properties, not extra deduplication keys.** A full-capture payment intent has at most one accepted charge identity in this subset; partial/multiple/changing captures are held rather than summed or guessed.

A trusted host supplies `Scope(account, venture, livemode=False, account_mode=...)`. Signed metadata is never authority to select an account or venture. A supplied metadata venture must match the host's binding at every supported expanded object. Every economic object must explicitly be in test mode.

- `account_mode='own'`: a dedicated own-account binding may omit the event's `account`; if supplied it must match.
- `account_mode='connected'`: the event's `account` is mandatory and must match. No inference from metadata or a shared signing secret is allowed.
- Transfers, `on_behalf_of`, source/destination transfer and application-fee flows are unsupported/unresolved, including malformed empty objects or zero-valued supplied flow fields. No netting/fee estimate is made.

This host API is not remote human authentication, a customer-code sandbox or AG1 authority.

## Supported evidence and recognition state

| Notification | Accepted evidence / economic identity |
|---|---|
| `invoice.paid` | Paid, not out-of-band, valid invoice ID; expanded succeeded payment intent and expanded fully captured charge; all amounts and links agree → `ch_…` |
| `checkout.session.completed` | Complete **payment-mode**, paid session; expanded succeeded intent and verified full charge; amounts/links agree → same `ch_…` |
| `payment_intent.succeeded` | Succeeded intent, exact received amount and expanded verified `latest_charge` → same `ch_…` |
| `charge.succeeded`, `charge.captured` | Explicit successful/paid/captured/non-disputed full charge with an intent ID → same `ch_…` |
| `refund.created`, `refund.updated`, `charge.refund.updated` | Explicit successful refund ID and parent charge; optional supplied intent must agree → `re_…` |
| `charge.refunded` | Complete non-truncated individual-refund list with unique IDs, successful status, matching parent/intent and exact cumulative sum. The parent capture witness must agree with the stored capture. Each `re_…` is counted once; **the cumulative amount is not a new refund**. |

Forward evidence expansions are specifically invoice/session → intent → charge. Backlinks are IDs only in v1; expanded backlinks are unresolved, not partially trusted. Missing/unsupported versions, unsupported events, incomplete links, partial captures, unknown dispute state, unpaid/processing/failed/out-of-band objects, and pending/failed refunds create no invented money. Invalid/malformed/conflicting inputs are rejected, not relabelled as successful duplicates.

A canonical `capture` is **synthetic evidence-qualified captured gross**, not recognized business revenue, MRR, fee-adjusted profit, independently settled cash or a bank balance. `net_captured_minor` is gross captures minus identified successful refunds, not a full P&L. Fees, taxes/recognition policy, disputes/reversals, payouts, FX and live settlement are not implemented. No balancing adjustment is manufactured.

## Persistence, replay, failure and reconciliation

`services/sentinel/economic_repository.py` adds only `economic_v1_*` tables/indexes/triggers when a host explicitly constructs `EconomicBook(disposable_store, experimental=True)`. Normal `Store` construction does **not** install this schema. Existing REAL ledger rows, policy/audit/approvals and owner databases are never rewritten or silently upgraded. Old manual/legacy rows remain excluded from canonical totals, with no inferred provenance.

Message claim, canonical uniqueness/postings, links and append-only transition evidence commit in one transaction. SQLite uses `BEGIN IMMEDIATE`, database primary/unique constraints, foreign keys and recursive immutable triggers (including protection against `INSERT OR REPLACE`). A Python lock alone is not the uniqueness mechanism. Separate-connection/process races are exercised locally. Administrator access can still bypass schema controls; this is not restricted-role/tamper-proof storage certification.

PostgreSQL SQL uses an advisory migration mutex, a cross-connection table lock, database constraints and append-only guards, with bounded lock/statement waits. Four new opt-in cases use **only** `OPENBOT_TEST_POSTGRES_DSN` plus `OPENBOT_TEST_POSTGRES_ALLOW_WRITES=1`; they never borrow `DATABASE_URL`/`SENTINEL_DB`, truncate or delete test history. Skipping them is **not PG proof**, and no PostgreSQL server was activated for this work.

A caller-owned existing transaction is refused **without committing or rolling it back**. Storage/audit failure before commit rolls back owned work. Commit/response uncertainty returns unavailable/uncertain, not a made-up success or a promise of no effect. Recovery replays the **same notification identity and immutable bytes**; it does not delete a claim, use a new ID or refund uncertainty away.

A complete refund received before its capture is retained as `awaiting_capture`. A later verified capture resolves waiting messages transactionally and idempotently; known over-refunds/conflicting witnesses become retained unresolved results. Inline reconciliation is bounded (default 100), reports remaining waiting work, and the host can explicitly call bounded `reconcile_waiting`. Cumulative-only/truncated/unlinked or otherwise incomplete messages remain unresolved; they are not silently marked settled when another event arrives. Their retained digest/minimal candidate evidence deliberately does not store full customer bodies. Resolving missing facts requires adequate new, legitimately identified evidence or a separately reviewed append-only reconciliation workflow, not fabricated IDs or edited old payloads.

## Boundary and compatibility

- `/webhooks/stripe` and the old one-row `map_stripe_event_to_ledger_row` **fail closed**. A `STRIPE_WEBHOOK_SECRET` environment variable alone cannot reactivate the unsafe event-ID-only writer.
- Explicitly versioned `/v2/economic/stripe` exists but has **no configured profile at startup**, no environment/HTTP configuration setter and no automatic schema migration. Trusted tests/operators may inject `SyntheticIngress` with a disposable book, frozen host scope, fake fixture secret and explicit experiment opt-in. Do not attach a live endpoint/account.
- Raw-body HMAC verifies delivery bytes/timestamp (multiple v1 signatures supported), not economic completeness or permission to move money. Streamed bodies are byte-bounded before parsing; duplicate JSON keys/nonfinite constants/malformed UTF-8 or deep JSON are refused. Secrets/raw bodies are not echoed.
- Outcomes: `201` new canonical effects, `200` known replay/linked message without new postings, `202` explicitly awaiting/unresolved; `400` bad signature/JSON, `403` scope mismatch, `409` conflict, `413` body limit, `422` invalid money/shape, `503` unconfigured/unavailable. Uncertain commit/response failures explicitly expose `outcome_uncertain=true`.
- Existing `/v1/ledger`, `/v1/pnl` and console contracts remain legacy/manual. The new book is **not** silently fed into the old float P&L. New manual writes reject booleans/nonfinite amounts at HTTP, validator and direct repository boundaries; unrelated integrity failures are no longer reported as duplicates. Legacy ledger validation errors omit raw `input` to avoid private-input echo and NaN-response HTTP 500s. Historical rows are preserved.
- Canonical `summary`, `messages`, `postings` and reconciliation are host-side experimental APIs; no unreviewed public book-reading/configuration route was exposed. Statement-fixture drift is reported exactly and never auto-corrected.

## Reproduce and retain

After installing the existing locked Linux tools **in an isolated disposable checkout**:

```sh
OPENBOT_TEST_NAMESPACE=1 python -m pytest --junitxml=NEW-evidence/full.xml
python scripts/record-verification.py NEW-evidence/full.xml
bash scripts/sync-docs.sh
python scripts/economic-demo.py --output NEW-evidence/economic-readback.json
make lint release-check
```

Use actual new paths, not the literal `NEW-evidence` placeholder. Preserve the raw XML, subprocess logs, source inventory, read-back JSON and synthetic fixture database hashes. The demo executes four independent-process races and five real abrupt process deaths/restarts on new cache-only SQLite files. Fixture record time is explicitly deterministic and distinct from the measured runner clock. A checksum/collected case count alone cannot prove execution.

Code rollback means disable/unconfigure ingress and restore reviewed code in a **new** checkout. Retain evidence and canonical/legacy history; do not drop tables, rewrite postings, infer settlement or replace a live database from a fixture backup. The rollback fixture only opens its preserved disposable pre-migration copy. Human legal/accounts/pricing/spend/outbound/release authority, default-off providers/media, `/v1/split` 501 and all other open work orders remain unchanged.
