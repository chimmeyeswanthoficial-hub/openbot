# Fixed namespace experiment — narrow progress, not AG1 completion

## What changed

`NamespaceExecutor` is a separate, explicit **trusted-host Python API**. It reuses the existing
LocalExecutor's policy/mapper/audit, exact-input review, durable attempt quota and scoped local
outbox. Only `local.wordcount` and `local.reviewed_wordcount` exist. There is no command, shell,
program, URL, provider or customer-repository interface. It is not an HQ/HTTP/Worker route.

Unlike the older trusted-host worker, this opt-in experiment starts the reviewed fixed worker
inside checksum-pinned, non-setuid Bubblewrap 0.12.0:

- Mandatory user/mount/network/PID/IPC/UTS isolation, new session, parent-death protection;
  failed setup refuses. **No host-worker fallback** exists.
- Read-only root, `/usr`, libraries, fixed worker, `/proc`, minimal `/dev` and bounded empty `/tmp`.
  No home/workspace/company DB, credential directory or host-writable volume is mounted.
- Cleared environment; only fixed PATH/LANG/Python flags and Bubblewrap's fixed PWD are allowed.
  No inherited arbitrary FDs; seccomp instructions are passed in a sealed memory file.
- Zero effective capabilities, no-new-privileges and an x86_64/ABI-guarded seccomp deny filter.
  Network sockets, fork/clone, nested namespaces, mount, tracing, BPF/perf, io_uring and selected
  process-FD/kernel interfaces are denied. This is **not an audited general syscall allowlist**.
- Reviewed worker applies CPU2s, address-space128MiB, files0, descriptors16, core0 and process1
  rlimits. The launcher bounds input/stdout/stderr and observes real process exit on deadline or
  cancellation. Rlimits are applied by fixed trusted worker code, not a substitute for cgroups.
- Completion validates seven correlated fixed-worker events, observed namespace/control/rlimit
  evidence and the actual count. Request/review/replay hashes also bind the namespace launcher,
  fixed worker, shared pin checker, runtime lock and pinned executable. Legacy host completions
  cannot be promoted into namespace evidence. Changed implementation requires reconciliation.

`audit/isolation-runtime-lock.json` records the exact Debian package/download/binary hashes.
The package hash was checked against configured Debian metadata; this is **integrity pinning,
not an independent publisher or security audit**. Only an excluded-cache extraction is used.
No root, setuid or system installation is performed. Public package download is the setup's only
intended network effect. Dependencies and package/executable are not bundled in the source handoff.

## Reproduce on the measured Linux x86_64 host

After the pinned Python/Node installation in `PORTABLE_HANDOFF.md`:

```sh
export PATH="$PWD/.venv/bin:$PWD/.cache/openbot-toolchains/node-v24.22.3-linux-x64/bin:$PATH"
make isolation-install   # explicit pinned Debian download/extraction into .cache; no server
make isolation-test      # fixed namespace + setup + transport regression cases
make isolation-demo      # actual negative probes, restart and supervisor-death proof
# Whole-project measurement with actual namespace cases, not namespace skips:
OPENBOT_TEST_NAMESPACE=1 make lint
OPENBOT_TEST_NAMESPACE=1 make release-check
```

Without `OPENBOT_TEST_NAMESPACE=1`, the actual namespace cases skip rather than being fabricated
or silently run on the host. They require working rootless namespaces and the pinned tool.
Unsupported hosts fail setup; use an authorized compatible host instead of weakening controls.
The tool check never implicitly downloads; `--install` is the explicit network opt-in.

The real probe uses only a newly created **synthetic disposable canary**, never real credentials.
It tests host reads/writes (including `/proc/1/root`), root/tmp writes, IPv4/IPv6/Unix/raw syscall
socket creation, io_uring, fork and nested user namespaces; the host canary must remain identical.
The parent-crash probe kills a separate supervisor, observes the real namespace process tree gone,
reaps adopted children and confirms the interrupted request/attempt is not reexecuted/refunded.
BPF-unit evaluation is a distinct structural check, not itself a kernel escape test.

`audit/progression-review.json` identifies measured red/green/full/independent-install evidence.
The old `audit/EXECUTION_FINAL_VERIFICATION.md` and donor/workbench receipts remain historical.
No new browser or live PostgreSQL/provider test is implied by these process probes.

## Legacy dispatcher: truthful, disabled-by-default seam

`services/worker/src/dispatch_agui.py` no longer has an enabled default HTTP transport. It refuses
unless a trusted host explicitly injects a callable and supplies persistent storage/valid scoped
run/plan. This callable is **not remote authentication or a production provider adapter**.

A database conditional claim prevents two connections/restarts from attempting the same stored
run twice. A confirmed positive audit row precedes the callable. Unknown outcomes, overspend,
malformed/ambiguous output, invalid costs and post-effect persistence failure require reconciliation.
The same run cannot be automatically retried. A new run ID does not authorize repeating uncertain
external work; a human must reconcile it. Scheduler occurrence deduplication remains AG3 work.

A well-formed reply is only `response_received`, with local **draft-only** destinations:
`delivery_confirmed=false`, `stop_confirmed=false`, `reservation_enforced=false`,
`runtime_deadline_enforced=false`, `automatic_retry_allowed=false`. `reported_cost_usd` is not
settlement; `cost_usd=null`. No ledger row or actual delivery is produced. The old numeric runs
column remains zero as a schema placeholder; bounded JSON detail explicitly says cost is unknown.
Do not sum that zero as proof of zero provider spend. The callable timeout is advisory, not a kill.
No fabricated default success text, fake remote-stop receipt or exception-secret echo remains.

## Why wider execution stays blocked

The cgroup filesystem is not writable/delegated here. This experiment supplies **no delegated
per-job cgroup CPU/RAM/PID/disk accounting, protected secret service, mandatory authenticated live
runtime hook, hostile tenant separation, remote provider stop or independent security review**.
The host kernel and read-only `/usr`/libraries remain trusted and are not a hermetic pinned image.
Same-user source/path replacement and local audit tampering are outside its security guarantees.

Do not enable arbitrary/customer programs, HQ shell/browser/MCP/models, paid providers or a
public service from these tests. Antigravity AG0 must reproduce the import, then an authorized
staging host and independent reviewer must complete AG1 before AG2 provider/cost/stop work.
Human legal/accounts/spend/sensitive-outbound/release authority and the private 1–6-month
observed pilot remain. No technical delegation transfers business accountability.
