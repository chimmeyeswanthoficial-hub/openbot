# Security — intended invariant versus demonstrated boundary

## Do not confuse policy code with mandatory enforcement

The intended rule is **no persisted audit row, no action**. `services/sentinel/policy.py`
provides deterministic safety/venture/budget decisions. A policy result, UI card, prompt or
separate home directory does **not** prove every execution path is intercepted. Generic runtime,
HTTP/Worker/model and hostile-tenant integration remain open under AG1/AG2. The former claim
that no repository path could bypass policy was too broad and is withdrawn.

Current bounded paths:

- Provider-disabled local HQ has an authenticated fixed company-report bridge to independent
  policy/audit. Raw model/computer/browser/shell/MCP/voice/provider routes remain unavailable.
- `LocalExecutor` is reviewed fixed same-user tooling, not an OS/network sandbox.
- Explicit opt-in `NamespaceExecutor` adds pinned non-setuid Bubblewrap, mandatory rootless
  namespaces, read-only mounts, minimal environment, dropped caps, no-new-privileges, seccomp
  and fixed-worker rlimits. It is **not** a general-purpose or independently reviewed sandbox.
  See `NAMESPACE_EXPERIMENT.md` for exactly which negative/process probes actually ran.
- The legacy AG-UI dispatcher has no enabled default HTTP transport. An injected trusted-host
  callable is not authentication, remote-stop control, enforced spend or actual delivery.
  Unknown outcomes require reconciliation; a client timeout never becomes a kill receipt.

## Known boundaries still missing

1. Mandatory authenticated server-to-runtime authority/ownership/tenant binding before every
   enabled side effect; protected reads, approvals, cancellation and exact review/revocation.
2. Delegated per-job resource/cgroup controls, protected secret service, read-only pinned runtime
   images, hostile tenant/path/FD/egress tests and independent security review. Rlimits alone
   do not meet this gate. The current host has no writable delegated cgroup hierarchy.
3. Actual provider liability reservation, independent usage/settlement and stop acknowledgment;
   exact-draft authorized external delivery/reconciliation. A reported cost is not a ledger fact.
4. Durable scheduler occurrences, PostgreSQL application-role append-only grants/restore/crash
   evidence, protected evaluator/deployment access and real staging/backup/alert drills.

Generic policy-only network checks can be bypassed by a process opening a raw socket; they are
not a firewall. The fixed namespace profile denies sockets and isolates its network, but does
not upgrade every other process/runtime. No arbitrary customer programs are permitted here.

The control plane trusts its source/config/filesystem and host administrator. Source digests
and local SQLite evidence detect accidental drift/replay; they are not publisher signatures or
tamper-proof logs. Store exposes no audit update/delete method, but without database grants this
is an API convention, not proof the application role cannot alter SQL directly. Prompts are not
security boundaries; untrusted repository/skill/browser/model content never grants authority.

## Reporting and repair

Report privately to the accountable owner through an authorized channel; do not publish secrets
or file sensitive details in public issues. Supply a minimal synthetic input, expected boundary,
actual observation and redacted logs. No incident channel or on-call response is implied merely
by this document existing.

Reproduce as a failing regression, implement a bounded repair, retain red/green evidence and
append a unique prevention rule to `.openbot/post_mortems/error_registry.jsonl`. Never replace
historical entries. Run the referenced test plus full gates; independent review is required
before widening execution, money, deployment or evaluator authority.

## Secret handling

- Never put credentials into chat, routine text, Git or deliverable logs. `.gitignore` and the
  known-pattern scrubber are helpful but incomplete, not a vault or comprehensive DLP.
- Protected-path policy checks do not prove hostile filesystem isolation. Keep company/secret
  storage separate from agent-writable runtimes; use synthetic/owned inputs for development.
- The private continuation omits credential files and sanitizes only exported HQ auth rows;
  original business/history records stay. Treat the remaining transcripts/state as private.
- The OpenBot substrate's `KEY_ENCRYPTION_KEY` and any future secret/recovery keys belong in an
  owner-controlled secure manager with off-host recovery, not ordinary token-text columns.
  Encryption-at-rest does not itself separate a compromised process from plaintext access.

Human accounts/legal/spend/sensitive outbound/release authority and the private 1–6-month
observed pilot remain mandatory. Green local checks are not production authorization.
