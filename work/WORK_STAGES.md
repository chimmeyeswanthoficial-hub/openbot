# S02–S05 — bounded local work checkpoint

> **Historical S02–S05 checkpoint.** The current local continuation is described in
> `STAGES_06_10.md`; historical counts/receipts and limitations below are retained, not rewritten.

This successor is **private review source, not a deployment or public release**. It starts from the frozen S01 source. The accompanying source/evidence packet records the actual measurements and clean reconstruction. Historical S01/AG0/AG4 receipts remain historical.

## Implemented local scope

| Stage | What the implementation does | Acceptance not supplied here |
|---|---|---|
| S02 | Durable venture/routine/origin/scheduled-UTC identities, original initiator/spec digest, integer whole-liability reservations, transactional claims/leases/fences, immutable history, uncertain outcomes and original-ID recovery | Production migration/HA, missed-job monitoring or automatic cron catch-up; no live spending |
| S03 | Default-off API; trusted host-issued expiring/revocable sessions; scoped reads/review/cancel; exact plan/policy/implementation/limit binding rechecked immediately before the audited effect | Real identity provider/TLS/device pairing; customer-code or hostile-host isolation |
| S04 | Narrow incremental UTF-8/SSE profile; bounded wire parsing and receipts; durable run/tool/message/sequence correlation and offsets; once-only attempts and explicit stop/independent usage contracts against a real local HTTP fixture | Full AG-UI compatibility or a live-provider hard cap/stop/usage certification |
| S05 | Complete owned QA/docs intake → exact synthetic fixture review → actual isolated tests/examples → independently read-back artifact → local review queue; real failure/restart/restore/replay tests | Qualified human usefulness/rights/quality acceptance, customer code, pricing, paid work or external delivery |

Windows/Android/iOS remain the previously delivered offline **control clients**. This code does not pair them or replace the protected Linux server architecture. No provider keys, customer programs, accounts, production database, Git push, deployment or release are activated by importing this source.

## Run and inspect the useful sample

Use the locked Linux x86-64/Python 3.13 profile described in the accompanying reproduction guide. Explicitly restore the pinned non-setuid namespace tool with `python scripts/bootstrap-isolation.py --install` from this source tree. Unsupported namespaces/resources/provenance refuse; there is no ordinary host-execution fallback.

```sh
python scripts/owned-work-demo.py --approve-synthetic-fixture \
  --fixture invoice-good-v1 --output .cache/owned-review-NEW
```

The output directory must be NEW, non-symlinked and under this source tree's `.cache`. The command opens no HTTP listener: it drives the actual authenticated API in-process, using disposable SQLite and synthetic test-role sessions. Both temporary grants are revoked on a successful demonstration; no raw credential is printed or exported. This is an explicit fixture exercise, **not an actual human approving work**.

Read `REPORT.md`, `report.json`, `owned-source.py`, `events.json`, `history.json`, `task.json` and `outbox.json`. A completed task means a report was produced, **not** that the tested sample is correct. The outbox remains `review`; human artifact review was not invented.

| Bundled first-party fixture | Expected observed result | CLI exit |
|---|---|---|
| `invoice-good-v1` | 7 passed, 0 failed (6 independent unit cases + documentation examples) | 0 |
| `invoice-discount-defect-v1` | 4 passed, 3 failed; discount/invoice assertions reproduce actual wrong values | 1 |
| `invoice-docs-defect-v1` | 6 passed, 1 failed; actual doctest contradicts the documented result | 1 |

Run each fixture with a DIFFERENT new output directory. Exit 2 means refusal/unsupported setup, not a reproduced sample defect. Reports contain source/worker/run/JUnit digests, exact traces, observed environment and namespace controls, proposed severity and human-review limits. A qualified reviewer still needs to independently reproduce the findings, assess severity/clarity, use the docs, and explicitly accept or reject the workflow. Test-role sessions and automated tests do not supply that acceptance.

## Trusted setup versus runtime

- `Store(..., initialize=True)` / `WorkStore(..., initialize=True)` are trusted **disposable setup APIs**, not JSON permissions. Only setup may create the additive `work_v1_*` profile, configure initial immutable caps, import explicitly attested legacy bounds or issue/revoke sessions. Do not pass setup/owner connections to agents or the public API.
- A runtime opens `Store(..., initialize=False)` and `WorkStore(store)` with a separate restricted role. Both fail closed on missing/incompatible schemas; work initialization does not silently ALTER an older incomplete prototype. No production migration is shipped or executed. Runtime agents receive neither connection nor provisioning credentials.
- `WorkService(work)` is disabled by default; `create_work_app` mounts no work routes until a trusted host explicitly enables this **owned-fixture-only** service. There is no grant/session/owner route, arbitrary program, shell, provider activation or legacy runtime route in that app.
- Host setup alone issues opaque scoped sessions (up to one hour). HTTP actor/venture/initiator/owner/budget/tool fields are forbidden; original identity comes from session records. Owner review is exact-digest, scoped, once-only and time-bounded. Revocation/expiry/current binding are rechecked in the pre-effect transaction.
- `scripts/work_profile_fixtures.py` documents the actual synthetic PG owner/runtime split and grants used by tests. It is a test fixture, **not a production provisioning script**. PG mutation requires explicit disposable DSN and write opt-in; the namespace tests also require explicit opt-in.
- Trusted host/source/runtime and the DB owner remain trusted. Namespaces/rlimits/seccomp for fixed owned literals are not delegated cgroups or independent hostile-code/tenant certification. No uploaded/customer program is accepted.

## Budget meaning and conservative legacy handling

All enabled reservations are USD **integer minor-unit liabilities**, never float totals or model-reported cost. Per-run, company-day/month and venture-day/month limits are persisted. A reservation atomically counts **all** outstanding/unknown liabilities across every UTC window, plus independently accepted final usage recognized in the current window. SQL aggregation has no 500-row history window and counts repeated instances of the same routine.

The original scheduled UTC day is identity metadata, not permission to book a new reservation or late usage into an old cheap window. Reservations use the current host UTC day. Final independent usage is conservatively recognized on the host UTC day it is accepted; this is **budget recognition, not the economic, processor or bank settlement date**. Unreconciled upper liability remains held across midnight/month changes. Over-bound actual usage is retained and flagged uncertain rather than hidden.

Old run rows do not contain an authoritative original upper bound. Failed/cancelled/unknown old labels are not proof of zero liability. Relevant unreviewed history blocks reservations. Only trusted offline setup can call `import_legacy({routine_id: explicit_upper_minor}, evidence_digest=<64-hex>)` after reviewing a defensible upper bound for EVERY included historical run; it never substitutes today's routine prices. The digest is an attestation reference, not cryptographic proof that a human actually reviewed it or that usage settled. Imported unknown bounds remain conservatively outstanding; releasing old liabilities needs a separately reviewed reconciliation/migration, not an automatic zeroing operation.

These local contracts cannot force an arbitrary provider to obey a budget. The literal-loopback-only fixture independently enforces its synthetic request bound and meter. Paid activation remains blocked until actual provider exposure/stop/usage controls are witnessed under owner authority.

## Recovery and cancellation

- Repeating a timer/manual/event identity returns the same immutable occurrence; a retry is not a new origin or new ID. A different manual request is explicit new work, not a hidden retry.
- `preparing` means no attempted effect. Identical intake or the same timer can resume reservation/governance on the **same ID** after a registration/reservation crash. Changed drafts/principals cannot replace it.
- An unattempted expired claim may be reclaimed with a higher fence. Stale workers cannot authorize or finish it. An attempted expired claim becomes `uncertain`; lease expiry, timeout, a missing result or restart NEVER permits automatic redrive.
- The owned workflow's actual completion, final stream events and outbox are atomic. Failure before commit leaves uncertainty/no report; lost acknowledgement after commit preserves completed state and the exact artifact. Actual supervisor death after real QA but before persistence preserves uncertainty without rerunning QA.
- A cancel request is scoped/audited and is not a stop acknowledgement. The owned supervisor reports cancellation only after terminating/reaping the actual fixed child. A local HTTP provider fixture reports a stop only after its separate acknowledgement; unconfirmed stops retain uncertainty. Even confirmed stop does not release usage liability.
- Complete SQLite backup and PG dump/restore tests compare all measured rows, authority records, history/events/artifacts and grants in separately restored synthetic stores. Same-ID replay does not create another effect. This is not encrypted production backup/HA certification.

## Streaming, artifact review and later gates

The SSE profile supports only the explicitly listed run/text/tool event types, strict UTF-8/JSON fields, bounded bytes/frames/events/text and a deadline. Incoming network chunks are processed immediately; a slow one-byte trickle cannot hide in a fixed-size buffer. Socket idle reads have a separate two-second limit; deadline refusal may include one bounded in-flight read. Receipts are bounded while reading, not after an unbounded download. Compressed fixture responses are refused.

Events are correlated and persisted before callbacks/UI delivery; reconnect reads durable offsets without initiating a new HTTP attempt. Events are DATA, never instructions to launch a tool. Reused child IDs, gaps, conflicting duplicates and wrong runs are rejected. The provider fixture is real HTTP on literal `127.0.0.1` only, deliberately not a live adapter or a general egress proxy.

The outbox is mutable review state, so its own stored digest is not authority. Read-back and local review compare content/destination/digest with the **append-only staging attestation** and derived `local-review:<venture>` destination. Editing both content and mutable digest still fails. Exact local review can only produce `ready_local`; there is no permitted external delivery adapter here.

Next technical stages remain S06 media and S07 reviewed memory/skills. S08–S11 retain real pairing, native Windows/Android/iOS acceptance/signing, independent host security, one approved real provider and operational drills. S12 still requires the 1–6-month private pilot including at least 30 consecutive observed days, then S13 needs explicit human release authority. No background pilot, provider, deployment or product release is running.
