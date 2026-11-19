# OpenBot OS architecture and measurable differentiation

## Decision record

Keep the existing Python Sentinel governance/work kernel as the authoritative
control plane. Keep the light shared frontend and preserve its authenticated
owner-QA path. Use AG-UI as an interoperability boundary. Treat CopilotKit's MIT
TypeScript SDK/runtime and selected MIT upstream source as replaceable adapters,
not the owner of identities, credentials, audit, budgets or authoritative state.
Do not require CopilotKit Intelligence or an image lacking reviewed matching build
source for the intended core. This is a target architecture, not all implemented.

```text
Light desktop/mobile/browser clients
  | same-origin authenticated API; no provider secrets/native authority bridge
  v
Identity/organization/role boundary -- derive scope server-side
  |
  +-- Conversations/history/export -- project-owned journal (standalone v1 exists)
  +-- Work/queue/reservations/approval epochs -- existing governed kernel
  +-- Policy + pre-effect audit + budget + revocable capability -- authoritative
  |
  +-- AG-UI transport adapter -- optional MIT TypeScript runtime or direct adapter
  |      +-- local/remote agent framework / optional model provider
  |      +-- rendering/events only; no route around the policy boundary
  |
  +-- Tool broker -- every side effect revalidates grants/policy/review/cost
         +-- real VM/microVM provider per bot (not implemented/accepted)
         +-- owner-approved IDE sessions (not connected)
         +-- official X / Instagram / YouTube APIs (not connected)
         +-- owned QA/media/local tools (existing bounded local slices)

Secrets / evaluator / deployment-signing authority: OUTSIDE bot-writable guests.
```

Frontend approval cards, model instructions, AG-UI events, MCP declarations and
a container label do not enforce these boundaries. The application server and
actual executors must make bypass impossible and leave evidence of every attempt.

## State ownership and layering

| Resource | Authoritative owner | Current versus next |
|---|---|---|
| Identity, organization membership, role | Authenticated kernel/server | Existing narrow pairing; broader org/membership model needs design, tests and review. Scope objects alone do not provide auth. |
| Conversation history | Application DB | New standalone SQLite journal; no UI/API/agent-runner integration yet. PostgreSQL and reviewed migration/backfill remain next. |
| Work/task/occurrence/fence/whole-liability reservation | Existing work kernel | Existing local implementation; no new provider, hostile-host or production readiness claim. |
| Policy, approval epochs and pre-effect audit | Kernel + mandatory executor gateway | Existing bounded owned-QA slice; every new tool/provider must prove non-bypass and revocation behavior. |
| Agent state and streams | Selected agent + transport | Current narrow local-fixture profile is not full AG-UI. Build against pinned event schemas and interop fixtures, never infer full compatibility. |
| Computer lifecycle and guest state | Explicit VM provider outside guests | Required by the owner's scope; zero accepted real per-bot PCs now. Containers remain honestly labeled containers. |
| Secrets, OAuth refresh and IDE authorization | Protected owner-side broker | Never browser localStorage, bot files, transcript, Git, iframe or public diagnostics. Actual services require explicit authority. |
| Long-term memory / learning | Optional application-owned reviewed subsystem | Not implemented by the new journal. Consent, provenance, deletion and human skill publication must precede learning claims. |

For optional CopilotKit use, select a compatible **TypeScript OSS mode** deliberately;
not every language-specific runtime has the same service independence. Review the
exact package/version and license. SDK-local runners already exist; evaluate them
before adding redundant infrastructure. Untrusted rendering must stay separate
from host/tool authority, with CSP/network/bridge enforcement and adversarial tests.

## What “better” will mean — targets, not achieved comparisons

| Dimension | Frozen acceptance target | Current evidence/gap |
|---|---|---|
| Open core | Reproduce core from audited source without cloud account/license checks; no unapproved egress after dependencies obtained; SBOM/notices | First-party MIT made explicit; full dependency/clean build/egress audit NOT complete. |
| Portable durable history | Kill/restart and reconnect across all supported clients without duplicated committed events; scoped denial tests at HTTP + storage + stream | Library replay/retry/rollback/reopen tests exist; HTTP/UI/agent reconnect not connected. |
| Isolation | Real VM/microVM identity, bounded CPU/RAM/disk/time/egress, no cross-bot file/credential access, proven stop/reap | No accepted VM provider. Container-only work cannot satisfy this row. |
| Governed actions | All tool paths deny without current policy/grant/approval/budget/pre-effect audit; stale approvals and replay/TOCTOU tests | Existing narrow kernel slices; external integration/adversarial review open. |
| Local-first privacy | No telemetry by default; visible data destinations; export/delete/retention and backup-aware deletion proof | No new telemetry/network in journal; end-to-end policy/export/erasure not implemented. |
| Light accessible clients | Preserve light reference layout; WCAG 2.2 AA contrast/focus/keyboard/reflow at 320 CSS px and 200% zoom, screen-reader/device review | Existing light UI preserved; no fresh full a11y/device acceptance. Low-contrast/small inherited text needs measured review. |
| Native reliability | Windows, Android and iOS install/launch/lifecycle/manual interactions, signing, update/rollback/uninstall on a published support matrix | Windows blocked; old EXE/APK not rebuilt; iOS source only. |
| Usable task quality | Pre-freeze ≥20 held-out tasks; same model/config/budget/hardware/allowed tools against a pinned baseline; report raw success, errors, cost, time and confidence | No qualified independent A/B result. Do not claim superior quality from code or unit counts. |
| Operability | Witnessed rollout/rollback/restore/alerts/on-call, protected independent evaluation and approved incident drill | Historical local drill evidence only; external acceptance remains open. |

Before comparative runs, freeze the baseline source **and complete deployable
runtime**; a template plus an unidentified backend image is not a reproducible
baseline. Use licensed services only with valid permission, not license bypass.
Define success/risk/cost measures before seeing test outcomes; keep the evaluator
and held-out tasks outside bot-writable source/training material.

## Delivery order

1. Review/publish this foundation, independently verify actual Windows payload
   capture, and integrate authenticated history without weakening current pairing.
2. Add one provider/AG-UI adapter through the kernel under an explicit cost cap;
   prove durable event/retry/cancel/uncertain-effect semantics before general tools.
3. Add a real VM provider and measured guest/host boundaries; then IDE and official
   social/media adapters with their specific permissions and tests.
4. Native/device/signing/update and independent security/operations/evaluation.
5. Genuine 1–6-month private pilot including ≥30 consecutive observed days, then
   exact human signing/terms/on-call/scope/release authorization.

No credentials, host change, spend, public deployment or release is authorized by
this architecture. R01–R13 remain the acceptance authority; public release false.
