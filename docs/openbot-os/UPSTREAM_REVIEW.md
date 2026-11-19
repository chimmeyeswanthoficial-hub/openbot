# Pinned upstream review — foundation with successor status

The history successor is documented in [FEATURE_REUSE.md](FEATURE_REUSE.md) and
[AUTHENTICATED_HISTORY.md](AUTHENTICATED_HISTORY.md). It now implements an optional
signed-device human-history API and actually reuses the exact MIT AG-UI 1.0 schema
for tests; no live UI/provider/runner is implied. The original foundation review
and raw remote timestamps remain scoped evidence, not a calendar-latest claim.

## Executive decision

1. **CopilotKit/OpenBot is our retained upstream**, not nightly-labs/openbot.
2. CopilotKit's OSS frontend/runtime/agent interfaces are useful MIT components;
   they are **not the entire application backend**. Intelligence is a separately
   licensed platform and is not necessary for the SDK's TypeScript OSS mode.
3. The observed OpenBot remote head has a materially different source boundary:
   its public tree carries frontends/contracts/harnesses while Compose starts
   server/computer/supervisor from published images. Matching backend build source
   is absent from **that reviewed tree**. This does not prove no source exists
   elsewhere, or establish an unreviewed image's license, safety or reproducibility.
4. Keep our independent kernel and retained MIT source; selectively reuse reviewed
   patterns/components. Do not upgrade by replacing it with an image dependency,
   silently importing proprietary services or removing standing product scope.
5. OpenBot OS is not yet better overall or feature-complete. The architecture
   defines measurable comparison gates; this change supplies bounded real code.

## Evidence and scope

The review uses public repository metadata, complete **nontruncated path/blob
lists** for the compared OpenBot trees, pinned raw source/package/license files,
selected function/control-flow inspection, docs and our existing implementation.
It does not claim to execute every upstream function, audit every dependency,
decompile closed images, bypass licensing, run upstream native apps or certify
its current backend. Full source-tree enumeration is not a whole-code security audit.

Retrieved-source identities, Git-blob checks, review-depth labels and tree-count
comparisons are in `evidence/openbot-os-foundation/UPSTREAM_SOURCES.json`. Raw
research downloads are regenerable cache, not a second retained upstream checkout.
No upstream application code was copied into the journal or diagnostic helper. The successor separately retains the exact MIT AG-UI test schema/license with provenance.

### Immutable research pins

| Project | Pin / source fact | Use |
|---|---|---|
| CopilotKit/OpenBot observed remote head | `30a40979a93062b29f8592cef173601b354474b4`; root MIT; package 1.1.0; 4,961 blobs | Selected returned-ref source, frontend and deployment-boundary review. |
| CopilotKit/OpenBot configured-date cutoff comparison | `882c68e222bbb603c67855764facd4ebbb9778c8`; package 1.0.0; 3,658 blobs | Historical source-rich backend control flow; not misrepresented as the observed head. |
| CopilotKit/CopilotKit observed remote head | `567211b7edff7dde57cfc9b617655344004253c0`; root MIT; runtime package 1.89.0 | Optional SDK/runtime architecture and local runner review. |
| ag-ui-protocol/ag-ui observed remote head | `3416b86da4b3288e87f827c7f2759a7fa18b5231`; root MIT | Exact schema/license now adopted for CUSTOM-envelope tests; full protocol suite not run. |
| nightly-labs/openbot observed remote head | `daab0074f48c6531a42791d7a18ffd4d7c54d184`; PolyForm Noncommercial 1.0.0 | Identity/license comparison only; **not an OSS-core code donor**. |

**Clock qualification:** the configured session reference date is 2026-11-10.
The remote APIs returned heads whose Git committer metadata says November 17–19.
Those remote timestamps are retained as metadata, not used to advance the session
date or prove release order. “Observed head” here means the returned immutable ref,
not a promise that it was released by the configured date or will remain latest.
The separate date-cutoff pin was queried explicitly; no ancestor relationship is
assumed merely from dates. Pinned source content supports the conclusions below.

Source URLs use `https://github.com/CopilotKit/OpenBot/blob/<pin>/<path>` and the
analogous SDK URL. The source index records exact paths/hashes for reproduction.

## What actually changed in the compared OpenBot trees

A path/blob-ID comparison from `882c68e…` to `30a4097…` finds **2,911 added paths,
1,608 removed, 987 changed-content and 1,063 unchanged**. Many additions are
**generated API clients/models**, not distinct user features. These are exact
content/tree differences, not an executed upgrade or an assertion that all changes
are compatible. In particular:

- Compared earlier tree: `server/` 1,234 files, `agent-computer/` 152,
  `toolkit/` 29, `supervisor/` 23, `worker/` 7. Those paths are absent at the
  observed head. Root workspaces changed from app/server/worker/shared/toolkit/
  extension to app/shared/extension/management-agent.
- Observed Compose `docker-compose.yml:70–88` names a published server image and
  `/app/bin/openbot server`; computer/supervisor are images too. `backend-images.env`
  pins their input tag/source labels, but labels are not matching build source or
  reproducible-build proof. `docs/development.md:103–138` confirms the image-based
  server and migrations. We have not pulled or executed those images.
- API v2 OpenAPI/AsyncAPI and generated web/mobile/extension clients are prominent
  additions. That API version is different from both CopilotKit SDK “v2” imports
  and our existing gateway wire API v1/client 0.2.0. Do not conflate them.
- The observed app requests `@copilotkit/react-core` **1.88.0** while the cutoff
  server requested runtime **1.85.0**, and the observed SDK repo is **1.89.0**.
  Reading the SDK head does not prove a safe drop-in dependency upgrade.

Our retained selected reference is **3,475 files**, not either entire compared
remote tree. Against the observed head: 977 byte-identical Git blobs, 964 changed
paths and 1,534 retained paths absent there. Its original upstream commit has not
been independently established in this review, so these are content/path
comparisons, **not** a fabricated chronological diff from an invented old SHA.
Retain its licensed source and known provenance until intake is fully reconciled.

## CopilotKit: exact responsibilities

Official architecture describes **frontend → application-server runtime → agent**
over AG-UI. The runtime brokers auth/tools/streams; the selected agent runs the
loop. An in-process BuiltInAgent can avoid a separate agent service. This does
not supply the entire product's auth database, VM isolation, official social
permissions, accounting, operations or legal release authority.
[1](https://docs.copilotkit.ai/angular/concepts/architecture)

Official OSS/service guidance says MIT SDKs and TypeScript runtime can work
without a CopilotKit service and can use application/framework persistence;
Intelligence adds platform-backed streams/memory/learning/analytics/channels with
separate terms. Service-independence is not identical across all language runtimes.
[2](https://docs.copilotkit.ai/a2a/concepts/oss-vs-enterprise)

Pinned SDK source corroborates this: `packages/runtime/src/v2/runtime/core/runtime.ts`
contains `CopilotSseRuntime` with `intelligence=undefined` and an in-memory runner
(default), distinct from `CopilotIntelligenceRuntime`. It also exposes identity/
thread-ownership settings. `packages/sqlite-runner` is MIT **@copilotkit/sqlite-runner
1.89.0**, using `better-sqlite3`; `SqliteAgentRunner` has ownership/claim/stop/history
logic. **We must evaluate/reuse it where appropriate, not pretend local persistence
is our invention.** Its legacy-thread compatibility behavior needs an explicit
migration decision; opening old unowned histories must not make them publicly
claimable in our product. Selected code/tests were inspected, not executed here.

In contrast, the earlier OpenBot `server/src/copilot.ts:148–153,3051–3153` explicitly
uses Intelligence mode and passes an Intelligence client to its runtime. That is
an **application choice**, not proof the OSS SDK requires Intelligence. The observed
OpenBot README separately documents Intelligence licensing and account/license
requirements; fully local hosting and fully OSS are different questions.
[3](https://github.com/copilotkit/openbot)

## Feature/function review and adoption decisions

“Present” below means source/contract/documented capability at the named pin, not
independently proven end-to-end behavior. Observed backend-image behavior is not
inferred from earlier MIT server source.

| Area | Pinned evidence / notable functions | OpenBot OS action and current gap |
|---|---|---|
| Shared workspace and bot roster | Observed `app-sidebar.tsx`, `bot-profile/page.tsx`, routes under `_authed/_app/bots.*` | Keep companion-first light layout and truthful status; do not copy branding. Existing roster is mainly local planning. |
| Conversation history and reconnect | Observed `channel-chat.tsx`: `historyIsLoading`, `channelHistoryNotice`, `mergeStoredMessages`, `toMessageContent`, `ChannelChat`; `useAgent` uses channel thread ID | Adopt explicit loading/error/retry and stored-vs-live merge contracts, not a copy of the monolithic component. Optional signed-device human-history API now exists; no Studio/live stream connection. |
| Server-owned interrupt recovery | Observed `server-owned-interrupts.ts`: `serverOwnedInterrupt`, `releaseServerOwnedInterrupts` | Avoid duplicate approvals/restarts after reconnect. Add actual adapter fixtures; don't clear arbitrary framework interrupts. |
| SDK wiring | Observed `CopilotProvider`: relative `/api/copilotkit`, cookie credentials, organization headers, no browser Intelligence key | Reuse relative-URL/secret separation. Our pairing and authority remain kernel-owned; no SDK runtime installed by this change. |
| API-generated clients | Observed `api/openapi/*.yaml`, `api/asyncapi.yaml`, `app/src/lib/api/request.ts`: `apiRequest`, `idempotencyKey`, `organizationId` | Specify/version our own narrow contracts first, use stable write idempotency across retries. Do not paste API v2 clients over our wire v1. |
| Per-bot authorization | Observed `shared/agent-authorisation.ts`: `matchesToken`, `hasManagedAgentToken`; cutoff `auth/guards.ts`: `createRequireUser`, `requireAdmin` | Require server-derived roles/scopes and revocation. A token comparison helper or UI route guard isn't full isolation; no timing/security certification here. |
| Pre-effect policy and audit | Cutoff `computer/gateway.ts`: `createComputerGateway`, `govern`; policy decision before `write` then `run(address)`; failure rows share attempt ID | Useful MIT reference for mandatory broker. Our existing no-audit/no-action invariant must hold on *every actual executor*. Observed image implementation not audited. |
| Fail-closed rule evaluation | Cutoff `computer/policy.ts`: `evaluateActionPolicy`, `evaluateBoundaryRules`, `checkPolicyRule`; deny precedes allow and broken expressions deny | Reuse tests/patterns selectively, preserving our budget/approval epochs. Check actual deployed defaults, not only library behavior. |
| Human approvals | Observed `InlineApproval`, inbox queries and `decideApproval`: allow once/conversation/always, deny or handled | Keep exact-action review and revocation; persistent grants need bounded scope/expiry. “Exactly once” in a UI comment is not proof of exactly-once external effects. |
| Computer screen and terminal | Observed `ComputerViewPanel`, `LiveComputerPanel`, `ComputerView`, `ComputerTerminal`, `useComputerControl` | Good truthful no-computer state, one human/bot wheel, view-follow rules, lazy terminal mount and hidden-screen polling controls. Our computer pane remains a request/placeholder. |
| Historical versus live frames | Observed `computer-view.tsx` retained-turn frame state, stored screenshot reads and live polling | Never show today's live screen as evidence of an old action. No live screenshot integration is implemented here. |
| Isolation | Observed architecture says per-bot **containers**; `agents/isolation.ts` warns public-bot users share the computer/logins | Do not call those full VMs. Our standing scope requires actual VM/microVM provider and hostile-host evidence, currently absent. |
| Supervisor authority | Observed Compose mounts engine socket and itself notes root-equivalent authority even with `:ro` | Keep supervisor/engine API and secrets outside guests, with narrow authenticated host service; don't treat read-only socket mount as a security boundary. |
| Multiple agent frameworks | Observed `shared/harnesses.json`, separate framework directories including Antigravity and Claude SDK | Reuse audited adapters/protocol patterns selectively. Folder presence is not an authenticated live IDE session; ours still zero. |
| Routines/check-ins/responsibilities | Observed `docs/routines.md` and routes; cutoff `worker/src/index.ts` | Preserve durable occurrence/fence/reservation logic in our kernel. Model-proposed schedule must be validated, timezone-aware and approved. No scheduler activated here. |
| Memory and learned skills | Observed `shared/learning.ts`, `docs/automatic-learning.md`; cutoff memory/Intelligence client | Separate consented reviewed memory/skill publication from history. Observed docs note recording-deletion API limits; require backup-aware deletion/provenance. Not implemented by our journal. |
| Gen-UI / components | Observed `SandboxedTools`, `parametersFor`, `SandboxedTool`; server grants + SDK renderer | Keep code/HTML sandbox, egress/CSP and host authority separate. Permissive client schema fallback must never weaken server validation. SDK sandbox itself not audited here. |
| Connections/MCP and social | Observed connector/provider docs and API contracts; gateway policies in cutoff source | MCP/open connector does not automatically satisfy official X/Instagram/YouTube scopes, consent or platform rules. Our official social integration remains unconnected. |
| Desktop/mobile/extension | Observed desktop scripts, Expo mobile package/routes and browser extension | Useful API/UX references, not reusable signing identities or proof of Windows/iOS acceptance. Keep our shared light source; current native artifacts are older tests. |
| Updates/telemetry | Observed `desktop-updates.ts`, desktop update docs, `docs/TELEMETRY.md`; optional product telemetry in examples | Require signed manifests, verified rollback and explicit opt-in telemetry. Never enable a service because its README advertises it. No telemetry/updates enabled here. |

## Frontend design/code assessment

**Stack at observed head:** React 19, Vite, TanStack Router/Query, Tailwind/Base UI,
CopilotKit React v2 imports, API-generated clients, xterm and motion. `theme.css`
uses semantic OKLCH tokens for light/dark surfaces and an Inter/system font stack;
`styles.css` includes reduced-motion branches. Component presence is not a complete
accessibility, privacy or performance audit.

Useful design lessons to implement within our requested light design:

- Capability-driven empty/error/loading states instead of an endless “starting”
  computer spinner when no computer capability exists.
- One conversation identity across chat, approvals and screenshots, with source/
  freshness labels. Explicit human-vs-bot control and clear takeover transitions.
- Server-authoritative decisions with disabled pending mutation states and visible
  failure text; do not optimistically label an effect successful before read-back.
- Hidden-screen/polling and terminal socket lifetimes tied to visibility; stop work
  on unmount, scope switch and lifecycle pause. Bound retained history/frame caches.
- Component decomposition: the observed ~92 KB `channel-chat.tsx` and ~59 KB
  `computer-view.tsx` are coordination hot spots. Borrow contracts, not whole
  monoliths with unrelated runtime dependencies.
- Our inherited light UI's very small/muted typography needs measured WCAG AA
  contrast/focus/reflow review. Do not equate matching a screenshot with accessibility.

This foundation preserves our shared layout, updates identity/truthfulness strings
and corrects one measured selected-contact contrast issue; it does not copy the
upstream frontend. It does not implement new live conversations,
computer control, learned skills, connectors or account permissions merely because
those features appear in this reference review.

## Licensing/security conclusions and remaining work

The root MIT license and retained donor notices support selective reuse, not
blanket relicensing of Intelligence, WebView2 redistributables, brands or other
third-party dependencies. `THIRD_PARTY_NOTICES.md` records our explicit boundary.
The separate nightly-labs project remains noncommercial-licensed at its reviewed
pin; it was not imported or treated as the same product.

Before saying “fully OSS and better,” deliver a credential-free reproducible core
build, dependency/SBOM/notice audit, real provider/VM/IDE/social integration through
the broker, native/device proof and qualified held-out comparison on a frozen
baseline. R01–R13, genuine pilot and human release approval remain unwaived.
