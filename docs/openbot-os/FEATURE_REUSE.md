# Did we reuse everything? No — explicit reuse and gap ledger

We should reuse **everything useful, legally compatible and actually tested**, not
merge four incompatible products blindly. Duplicate backends/authorities, noncommercial
code, dangerous defaults and enterprise-only services would undermine the fully OSS goal.
This is not a whole-code audit or a claim every function/design has been adopted.

## Source decisions

| Source | Actual position |
|---|---|
| nightly-labs/OpenBot current reviewed pin | **No code/artwork imported**: PolyForm Noncommercial. Public features/security warnings compared, not copied into MIT core. |
| nightly-labs/OpenBot v0.1.11 | Exact historical LICENSE is **Apache-2.0**, verified at `e9cae2ac7c83936a6e7d22c820e9d7ec0726d880`. A possible historical donor, but its modules/NOTICE/dependencies/functions are not yet reviewed or integrated. It does not license newer code. |
| CopilotKit/OpenBot | Selected earlier MIT source retained. Source/control-flow/frontend review performed; observed backend-image matching source/terms/reproducibility still unproved. No whole upstream replacement. |
| CopilotKit SDK + copilotkit.ai | Optional MIT SDK/runtime/local runners evaluated, **not integrated**. Marketing site/enterprise Intelligence/learning/channels are not one blanket OSS grant. No logo/artwork/website design copy or service activation. |
| AG-UI | **Actual new adoption:** exact MIT protocol 1.0 JSON schema + original license/provenance for offline CUSTOM-event validation. Not a full installed engine/stream/runner. |
| Existing OpenBot OS | Keep our governance/work kernel, original light design, real new authenticated history and bounded attributed OpenMuse CSV adoption. Do not throw working source/history away. |

Immutable pins/individual feature states are in
[FEATURE_REUSE_LEDGER.json](FEATURE_REUSE_LEDGER.json). Original upstream review:
[UPSTREAM_REVIEW.md](UPSTREAM_REVIEW.md). Current measured integration:
[AUTHENTICATED_HISTORY.md](AUTHENTICATED_HISTORY.md). Owner's actual real-use sequence:
[REAL_WORLD_ROLLOUT.md](REAL_WORLD_ROLLOUT.md).

## Feature-by-feature states (not a completion score)

| ID | Capability | Actual state | What is still required |
|---|---|---|---|
| F01 | Companion roster and editable roles | **existing-local-ui** — Original light local blueprints; not live agents. | Actual authenticated persistent roster/editor, bounded config/permissions and UI-to-server tests. |
| F02 | Durable scoped conversation history | **implemented-tested-api** — Real signed-device API + SQLite, not connected to Studio chat or a provider. | Remaining UI/reconnect/export/deletion and live adapter contracts; no simulated assistant. |
| F03 | AG-UI event compatibility | **adopted-test-contract** — Exact MIT schema validates our CUSTOM envelope offline. | Pinned full lifecycle/run/message/tool/cancel/resume adapter and interop corpus before claiming protocol support. |
| F04 | CopilotKit TypeScript SDK/runtime/local SQLite runner | **reviewed-not-integrated** — OSS runtime/local runners exist; do not reinvent them or require Intelligence. | Choose compatible versions and authoritative-state ownership; legacy unowned-thread migration reviewed/tested. |
| F05 | Live multi-provider agent sessions | **not-connected** — No paid/local model or external agent session accepted. | One authorized capped provider first; real usage/stream/cancel/reconcile evidence, then reviewed adapters. |
| F06 | Local OpenAI-compatible model endpoints | **planned** — No local model discovery/connection in current runtime. | Eligible explicit endpoint, SSRF/egress/model/version controls and actual owner-approved run. |
| F07 | Durable queue, pause/resume and retries | **existing-bounded-kernel** — Existing work occurrence/fence/reservation/serial queue components; no general live conversation queue. | Reuse these, not a second authority; real provider crash/restart/uncertain-effect queue tests. |
| F08 | Stop/cancel and uncertain external effects | **existing-bounded-kernel** — Owned-QA slice only; stopped UI is not proof of remote cancellation. | Actual remote stop/reap and cost reconciliation, no blind external retries. |
| F09 | Context monitoring and compaction | **planned** — No accepted live provider thread/compaction. | Bounded context, durable checkpoints, pinned summarization/provenance, consent and real cost/quality checks. |
| F10 | Agent-to-agent messages and shared channels | **planned** — No genuine inter-agent delegation/chat execution. | Single owner/fence per task, scoped recipients, bounded fanout, loop/cost caps, durable transfer/recovery. |
| F11 | Attachments and managed file transfers | **planned** — No new general chat file import or arbitrary host path exposure. | Size/type/path/symlink/archive-bomb/markup bounds, scoped recipients, immutable hashes and actual data lifecycle. |
| F12 | Controlled embedded browser | **planned** — No privileged browser session connected. | Isolated guest browser, egress and secret boundary, exact-effect approvals, human takeover, prompt-injection tests. |
| F13 | Real per-bot virtual PCs | **required-not-implemented** — Folders/containers/screen placeholders are not real VMs. | Real VM/microVM IDs, resource/disk/egress/credential/cross-bot/stop/recovery and independently witnessed host tests. |
| F14 | Claude Code / Antigravity / T3 Code integration | **required-not-connected** — No direct authenticated IDE session or external agent team. | Reviewed install/license/auth/session in real guest, owner permission and actual returned artifact evidence. |
| F15 | Signed device authentication | **existing-tested-plus-extension** — Existing P-256 request proofs now protect explicit history capabilities too. | Actual platform key storage/native trust/production host acceptance remain open. |
| F16 | Organization and hosted multi-tenancy | **not-implemented** — Host-issued actor/venture scope is not a full identity provider/org tenancy system. | Authenticated memberships/roles/revocation, hostile tenant/load/abuse/privacy tests and deployment acceptance. |
| F17 | Pre-effect policy, human approval, audit and budgets | **existing-bounded-kernel** — Owned-QA controls preserved; history adds content-free durable attempts before access. | Every actual new executor must prove non-bypass, stale-grant/approval/epoch/TOCTOU negatives and real caps. |
| F18 | Server-owned interrupts and reconnect | **reviewed-not-integrated** — Earlier source patterns inspected; no full live approval reconnect adapter. | One authoritative interrupt/decision, stored-vs-live merge and disconnect/replay tests on pinned framework. |
| F19 | Generative UI and frontend tools | **reviewed-not-integrated** — No model-generated code/HTML or frontend effect authority enabled. | Sandbox/CSP/origin/egress/bridge review; server revalidation for every tool, no approval authority in a card. |
| F20 | Shared state between app and agent | **planned** — No general AG-UI state-patch runtime. | Versioned/validated patches with authority-owned state excluded, concurrency/scope/size adversarial tests. |
| F21 | Long-term memory and learning | **planned-not-intelligence-copy** — History is not learning; enterprise services not silently imported or activated. | Consent/provenance/retention/export/delete, scoped retrieval, human-reviewed skill adoption and independent outcomes. |
| F22 | Skills/plugins/marketplace | **reference-only** — No broad marketplace auto-install or arbitrary privileged plugin execution. | Per-module license/pin/signature/capability review, sandboxing, revocation/update/rollback; opt-in only. |
| F23 | Routines/check-ins/schedules | **existing-bounded-kernel** — Existing schedule/work metadata and governed local work; no autonomous external schedule active. | Timezone/occurrence/dedup/approval/cap/expiry and real provider execution with stop/read-back. |
| F24 | Desktop/mobile light interface | **existing-original-design** — Owner-approved light design/original artwork preserved; no upstream product screenshot or website reskin. | Qualified keyboard/zoom/screen-reader/device lifecycle acceptance; truthful state over cosmetic parity. |
| F25 | Windows / Android / iOS native products | **required-blocked** — Old EXE/APK unchanged, Windows startup blocked, iOS source only. | Root-cause proof, current rebuilt payload, real devices/Mac/signing/update/uninstall and manual interactions. |
| F26 | Internationalization/theme/accessibility | **reference-partial** — Light theme and one measured text contrast fix; not all locales/full WCAG. | Semantic strings, RTL, keyboard/focus, contrast/reflow, reduced motion and real screen-reader/native acceptance. |
| F27 | Historical vs live computer frames and takeover | **reviewed-not-integrated** — No connected computer frames or real takeover. | Source/freshness identity, human/bot wheel, stopped hidden polling and old-frame evidence never substituted by live view. |
| F28 | Remote desktop / WebRTC / team access | **planned** — No copied tunnel/account backend, shared credentials or public remote-control endpoint. | Independent crypto/auth/consent/network/tenant/session audit; actual peer/guest revocation and native acceptance. |
| F29 | Slack / Teams / WhatsApp and other channels | **optional-not-integrated** — Website channel claims do not imply every adapter is OSS or connected here. | Per-adapter source/license/provider scopes/consent/terms, brokered actions and real platform test. |
| F30 | Official X / Instagram / YouTube | **required-not-connected** — Draft/planning only; no OAuth, posting or real account operation. | Current official policies/scopes, vault, exact action/data/rights consent, bounded private tests and read-back/stop. |
| F31 | Signed updates, rollback and recovery | **existing-local-prototypes** — Local verified-update/ops tests exist, not an accepted native/cloud rollout. | Actual signed native updates/rollback/off-host restore, alerts and named on-call witnessed independently. |
| F32 | Privacy-safe diagnostics and exports | **partial-tested** — New Windows capture is opt-in/fake-tested; payloads can contain secrets, not auto-redacted. | Actual native probe, ACLs, separate sanitization/publication permission and backup-aware data controls. |
| F33 | Credentials, DLP and retention | **partial-not-comprehensive** — New human text rejects several known credential patterns; not full DLP/encryption/secure erase. | Vault/rotation/redaction, threat review, consent/export/delete/backup/provider retention and real incident drills. |
| F34 | Usage/quality/learning analytics | **planned-real-only** — No copied illustrative website metrics or invented users/revenue/quality improvements. | Consented measured outcomes, failures/denominators/uncertainty, actual usage/cost and opt-in telemetry only. |
| F35 | Real-world phased pilot | **planned-not-started** — Owner requests >=30 consecutive real days then six additional calendar months; accepted 0. | Read REAL_WORLD_ROLLOUT.md; independently witnessed evidence, proper versioned phase admission and owner gates. |
| F36 | Better-than-upstream comparison | **not-established** — No quality superiority from copying features or passing more unit tests. | Freeze deployable licensed baseline and >=20 held-out tasks; qualified independent measured safety/quality/cost comparison. |
| F37 | OpenMuse finance workflow | **existing-attributed-adoption** — MIT CSV parser/vectors actually adapted; read-only local preview, no bank authority. | Real account/book operations remain separate permission/integration/reconciliation gates. |
| F38 | Fully OSS credential-free core build | **requirement-not-yet-proved** — First-party MIT and exact MIT contract adoption, not transitive/binary/brand clearance. | Complete notices/SBOM/clean reproducible build/egress audit; proprietary integrations optional outside core startup. |
| F39 | Current Noncommercial source imports | **excluded-license** — No current nightly source/artwork copied; source-available is not permissive OSS. | Only separately reviewed rights/compatible older code could change intake; no silent commercial-license purchase. |
| F40 | Unrestricted agent full-access / never-approve defaults | **rejected-policy** — Not adopted. Its README warns about broad local authority; copying that would contradict our governed-PC vision. | Governed isolated per-effect authority remains mandatory, not waived for feature parity. |

## Primary license/source references

- [Current nightly license](https://github.com/nightly-labs/openbot/blob/daab0074f48c6531a42791d7a18ffd4d7c54d184/LICENSE) and [its README warning/features](https://github.com/nightly-labs/openbot/blob/daab0074f48c6531a42791d7a18ffd4d7c54d184/README.md).
- [Verified historical Apache-2.0 license](https://github.com/nightly-labs/openbot/blob/e9cae2ac7c83936a6e7d22c820e9d7ec0726d880/LICENSE); resolved annotated tag/byte/blob proof in `evidence/openbot-os-history/NIGHTLY_LEGACY_LICENSE.json`.
- [CopilotKit/OpenBot MIT](https://github.com/CopilotKit/OpenBot/blob/30a40979a93062b29f8592cef173601b354474b4/LICENSE) and [SDK MIT](https://github.com/CopilotKit/CopilotKit/blob/567211b7edff7dde57cfc9b617655344004253c0/LICENSE).
- [AG-UI schema](https://github.com/ag-ui-protocol/ag-ui/blob/3416b86da4b3288e87f827c7f2759a7fa18b5231/spec/1.0/schema.json) and [MIT license](https://github.com/ag-ui-protocol/ag-ui/blob/3416b86da4b3288e87f827c7f2759a7fa18b5231/LICENSE).
- [CopilotKit website](https://www.copilotkit.ai/) was read as a product description; its own learning curves/values are illustrative, not OpenBot OS measured performance.

A permissive historical root license is not clearance for every included third-party
file, logo, dependency or current code change. Do not claim clean-room legal certification,
commercial service rights or universal compatibility. Root notices remain authoritative.
**Overall product unfinished; public release false; accepted genuine pilot days 0.**
