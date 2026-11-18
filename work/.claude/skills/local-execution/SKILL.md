---
name: local-execution
description: Work on the fixed trusted-host local executor, real process/SSE proof, exact draft review, attempt quota, scoped outbox and conservative crash replay. Use before exposing a tool route, changing execution/replay/cancellation, or claiming runtime/budget/isolation completion.
---

# Fixed execution safety / promotion

Read EXECUTION_SLICE.md, PROJECT_MEMORY.md, sentinel-gate, postmortem and the applicable
ANTIGRAVITY_WORK_ORDERS.md order. The local slice is fixed same-user code, not hostile isolation,
remote authentication, a live AG-UI model server or financial hard-limit enforcement.

1. Host supplies frozen actor/venture/original initiator. Never promote JSON owner/identity/cost/
   approval/program fields into authority. Owner('human:owner') is not a remote credential.
2. Persist audited explicit allow before effect; unknown/gate/deny/store-down refuses. Bind review
   to exact normalized draft/destination/identity/relevant source/policy hashes and TTL. Changed
   draft or implementation needs fresh review, never silently replace stored previews.
3. Reserve before work in a real transaction. Here units are attempts, not money. Preserve used
   units on uncertain failure; never delete quota/job rows to retry or widen a cap.
4. Consume actual bounded correlated events. Kill and wait/reap before claiming stopped. An HTTP
   timeout/AbortSignal or returned cost is not remote cancellation/spend control.
5. Completion binds output/result/events. Derive scoped delivery from validated original request,
   verify relative routing, regular files and audit hashes; refuse symlinks/nonregular/oversize.
   Restored output belongs to current restored state, not an old absolute path.
6. Interrupted/partial/ambiguous work needs reconciliation, not automatic rerun/new-ID retry.
   External effects require provider idempotency/reconciliation; local outbox is not proof.
7. Add red regressions for every discovered corruption/race, preserve traces, then run focused
   tests, execution-demo, full gates and restored-source proof. Keep primary business DB untouched.

```sh
python -m pytest services/gateway/tests/test_local_executor.py -p no:cacheprovider
python scripts/execution-demo.py
```

## New fixed namespace experiment and truthful legacy transport

Read `NAMESPACE_EXPERIMENT.md` and the progression receipt. Rootless namespaces work with a
pinned cache-only non-setuid Bubblewrap tool; absence of Docker is not proof no fixed experiment
is possible. Run `make isolation-install`, `make isolation-test`, `make isolation-demo`; actual
namespace whole-suite profile uses `OPENBOT_TEST_NAMESPACE=1`. Never add a host fallback or
arbitrary program interface. Keep the profile/relevant source/tool hashes in exact review/replay.

Check ABI/x32, alternate socket/io_uring/process-FD paths, no host writable mounts/env/FDs, fixed
rlimit evidence, cancellation/deadline and actual supervisor death plus interrupted replay. These
are scoped negative probes, NOT independent hostile security review or cgroup enforcement.
Legacy transport stays default-off/single-attempt; a draft reply cannot mean remote killed,
settled spend or delivered work. A timeout argument to a callable is not a forced deadline.

Before enabling broader tools: AG1 OS/egress/credential separation and real authenticated owner,
AG2 real transport/cost/stop proof, independent review and human approval. No shortcut through
upstream raw shell/browser/provider startup. Read-only donors remain evidence, not permission.
