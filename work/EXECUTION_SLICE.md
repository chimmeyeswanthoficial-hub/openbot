# Fixed local execution — supported scope and reproduction

**Installed code:** `services/gateway/src/local_executor.py`, `local_tool_worker.py`; tests in
`services/gateway/tests/test_local_executor.py`. Uses existing GatewayAdapter/mapper and Sentinel
policy/Store. Store.audit_tail now supports optional run/action filtering without changing defaults.
This is original first-party fixed tooling, not a running Rakazo/OpenDots/OpenBot model engine.

## Newer separate namespace profile

`NAMESPACE_EXPERIMENT.md` documents the explicit `NamespaceExecutor` experiment, using a pinned
non-setuid Bubblewrap binary and reviewed fixed worker. The older LocalExecutor contract below
remains same-user trusted-host code. The new experiment adds mandatory namespaces/denied egress/
read-only mounts and real process probes, but does not make HQ/HTTP/Worker generic execution safe
or complete AG1. `make isolation-install`, `make isolation-test`, `make isolation-demo` reproduce it.
The legacy dispatcher is separately repaired/default-off; an injected reply remains an unverified
draft with unknown settled cost and no stop/delivery receipt. See the current progression receipt.

## Run and inspect

After `bash scripts/bot-hq.sh install`, activate the locked Python environment:

```sh
export PATH="$PWD/.venv/bin:$PWD/.cache/openbot-toolchains/node-v24.22.3-linux-x64/bin:$PATH"
python -m pytest services/gateway/tests/test_local_executor.py -p no:cacheprovider
python scripts/execution-demo.py
```

The demo creates fresh disposable state under excluded `.cache` and prints a credential-free
receipt. It really launches fixed workers, consumes seven correlated SSE pipe events, checks an
actual output, reopens SQLite and proves replay without child/redelivery, leaves a reviewed task
**pending**, refuses an unregistered browser tool, cancels/reaps a child, enforces a real deadline,
and SIGKILLs a disposable parent then independently reaps its guarded child. It does not sign a
human approval, call a model/provider, send externally, deploy or edit primary company databases.
The generated `.cache` state is transient, not part of the continuation's business backup.

## Trusted-host API contract

`LocalExecutor(state, Authority(actor, venture, initiator, initiator_id), capacity=3, timeout_s=2)`
is a Python host entry point, not HTTP authentication. `Authority` is frozen; its values are set
by the trusted host, never by model JSON. `Owner('human:owner')` is a **host capability convention**,
not an authenticated remote owner. Only a real human-authorized host process may construct it to
call `resolve(request_id, expected_digest, approved_or_denied, owner=...)`. Do not give agents
that constructor or mount a route accepting the string as proof. Tests use synthetic owner fixtures.

Accepted request shape (fresh canonical UUID required):

```json
{"request_id":"a-canonical-uuid","tool":"local.wordcount","arguments":{"text":"one two three","output":"count.json","delay_ms":0}}
```

The UUID text above is descriptive, not an executable sample. Exact fields only; tools are
`local.wordcount` and `local.reviewed_wordcount`. No URLs, commands, payments, identity or approval
fields. Text is at most 8,192 UTF-8 bytes and refuses known secret patterns; this heuristic is **not**
complete secret/PII detection. `delay_ms`0–3000 is only a bounded cancellation fixture. Filename is
a simple scoped lowercase JSON name. Output derives from current state/venture/request, never an
absolute stored destination. Do not use sensitive/customer input: request/approval text persists.

## Enforced in this narrow profile

1. Explicit audited allow through existing mapping/policy before launching fixed work. Deny/gate/
   malformed verdict or failed audit cannot authorize it. Review expires after 15 minutes and binds
   full request, identity and hashes of executor/worker/adapter/mapper/policy/repository sources.
2. SQLite BEGIN IMMEDIATE claim+attempt reservation across executor instances. Capacity is
   persisted per venture and cannot be silently widened on restart. Units are **reserved execution
   attempts**, not USD, daily spend or revenue. Ambiguous/failed reservations are not refunded.
3. Linux Python `-I -S`, minimal child environment, parent-death guard and CPU/address-space/file/
   descriptor rlimits. Actual stdout SSE run/tool/message correlation, byte/event bounds and
   result validation; process-group SIGKILL and wait before cancelled/timed_out is reported.
4. Execution audit binds exact output and event hashes; outbox keeps a request-bound relative
   path. Delivery uses bounded regular-file checks, symlink refusal, exclusive create, fsync and
   matching-content recovery. Replays verify request/authority/implementation, audited bytes,
   returned result/events and delivery evidence; corruption is refused, never silently overwritten.
5. Running/preparing/uncertain markers without trusted completion require reconciliation. A
   source/policy/mapper upgrade changes request digest; inspect/migrate evidence, do not remove
   markers or choose a new ID to repeat uncertain work. Relocated restore replays in its new scope.

## Explicit non-goals / remaining risks

- **Not wired into HQ, HTTP, Worker daemon or AG-UI model transport.** Existing generic dispatcher
  semantics are not upgraded merely by this separate module. AG1/AG2 must supply mandatory wiring.
- Same-user trusted code, **not hostile-code/OS/network/tenant isolation**. No arbitrary program
  interface exists, but Linux could still allow syscalls if the worker/source were compromised.
  Private dirs/O_NOFOLLOW checks do not solve hostile same-user TOCTOU races or source replacement.
- Source hashes/audit in writable local SQLite are corruption/replay checks, not signatures,
  tamper-proof records, protected evaluators, remote owner auth or comprehensive supply-chain proof.
- The two SQLite databases are not one distributed atomic transaction. Crash between completion
  audit/outbox/delivery can conservatively require reconciliation. Local exclusive artifact write
  is not exactly-once external sending, provider cancellation or hard paid-spend enforcement.
- No genuine revenue or deployment. Keep provider-disabled defaults and the private 1–6-month
  pilot/human release gate. See `ANTIGRAVITY_WORK_ORDERS.md` for the production-sized next steps.
