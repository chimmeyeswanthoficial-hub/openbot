# Rakazo and OpenDots — remaining value and reuse decision

**They are not useless, and they have not been fully consumed.** All 5,086 selected source files
are now preserved losslessly in `archive/donor-sources/{rakazo,OpenDots}.tar.xz`; all file hashes,
sizes and modes were verified against the original trees and actual scratch restores BEFORE
removing only the redundant loose copies. The original root licences are included. A 26-file
reviewed reference library remains directly readable under `third_party/donor-library/`.

This newer owner-requested workspace consolidation supersedes the earlier no-cleanup decision,
not the integration/security gates. Nothing is labelled useless merely because it is unintegrated.
`WORKSPACE_CLEANUP.md` / `audit/donor-consolidation.json` identify the exact copies and recovery.
The working HQ app, queue attribution, findrepo tool/skill and OpenBot target source remain.

## What is known, and what is not

- Retained selection: Rakazo 4,899 files  / 47,148,124 B; OpenDots 187 files  / 1,578,537 B.
  `audit/donor-review.json` binds the selected bytes to reproducible tree fingerprints and hashes
  the reviewed references. The continuation manifest carries individual retained-file hashes.
- `.openbot/state/upstream.json` records main@2026-11-09 tarballs, **not immutable commit SHAs**.
  A content fingerprint proves what is retained, not who published it or an upstream revision.
  Establish a matching upstream commit in AG0/AG3 before upgrade/provenance claims.
- Root licences examined: Rakazo **Apache-2.0**; OpenDots **MIT, Atai Barkai**. Preserve licence,
  copyright and applicable notices/change attribution when porting. Root licences do not clear
  third-party dependencies, logos/assets, accounts or separately licensed CopilotKit Intelligence.
- No direct Rakazo/OpenDots runtime import/reference was found by the scoped first-party source
  search recorded in the audit. This is not a full transitive-dependency/security audit. Earlier
  routines/review ideas are **pattern reuse**, not proof their implementations were installed.
- Donor servers/tests/installers were not run or enabled. OpenDots `.env` remains at its original
  path, byte/mode unchanged, excluded from source archives and continuation packaging. Its content
  is not displayed. The redundant public source copies were retired only after exact restore;
  `audit/donor-review.json` remains unchanged as the original review/fingerprint receipt.

## Source-backed reuse / defer / reject matrix

Paths in this table are logical paths relative to the original `repos/<donor>/` snapshots.
The 26 previously reviewed files now have readable copies under `third_party/donor-library/<donor>/`
(the backup shell reference ends in `.sh.txt` and is non-executable). ALL other selected source,
including unreviewed/deferred features and tests, is recoverable using `scripts/donor_vault.py`
into a NEW scratch directory. A copied reference is not an integrated capability.

| Source | Useful remaining mechanism | Decision and landing | Guard before adoption |
|---|---|---|---|
| Rakazo `packages/adapters/src/routine-coalescing.ts` (+test) | Timer-specific nonce, pristine/unattempted catch-up checks, transactional fence recheck, retained cancellation history | **Reuse pattern next**, AG3 scheduler | Our durable occurrence key includes venture/original initiator/spec; never coalesce manual/event/attempted/uncertain work. Prisma/schema calls are not a drop-in SQLite/PG patch |
| Rakazo `routine-watch.ts` (+test), same directory | Non-model fingerprint check; baseline/unchanged/changed, retry versus pause, bounded detail | **Defer until AG1/AG3**, then read-only first-party change watch | Pure compare/hash logic is separable; donor readComputer/readTool can provision computers/run commands/use connections. Every check still needs policy, audit, resource/egress budget |
| Rakazo `routine-handover.ts` | Explicit queued-owner handover distinct from running identity | **Reference, not copy verbatim**, AG3 | Preserve immutable original initiation/delegation lineage. Do not silently re-authorize our queued effects under another person's credentials |
| Rakazo `docs/board.md`, `ticket-context.ts` | Review/blocked statuses; space-scoped bounded escaped context with “data, not instructions” | **Selective reuse later**, task UX after AG2 | Existing HQ task UI prevents a second board/database now. Ticket assignment cannot itself grant tool authority; escaping is not prompt-injection isolation |
| Rakazo `group-handoff.ts`, `docs/groups.md` | Active source/member checks, transactional delivery nonce, hop limits, source-run linkage | **Defer delegation**, after AG2/AG3 | Thread/space checks are not venture authority or shared financial limits. Bind inherited actor/initiator and total budget; no autonomous cross-space/bot-management rights |
| Rakazo `docs/skills.md`, `skills-lock.json` | Import preview, instructions-only scripts, teach→draft→save/test/routine workflow, hash lock | **Reference for AG6**, not an enabled importer | Licence/dependency/script review, secrets-masked authorized capture, held-out eval and human promotion; instructions never widen permissions |
| Rakazo `docs/self-host-backups.md`, `infra/compose/backup-drill.sh` | Off-host encrypted backup/retention/capacity and verified streams | **Adapt checklist in AG5**, no script execution here | Drill script verifies checksum/decrypt/archive listings, not actual DB/app restore. Execute independent matching-state restore/rollback; never import donor retention deletion logic blindly |
| OpenDots `src/client/PageReviewCard.tsx`, `src/server/page-routes.ts`, `pages.ts#createReviewed` | Stored draft receipt; changed draft/Space conflict; transactional one saved page per review; deleted receipt survives to prevent recreation | **Reuse review UX/state pattern**, AG1/AG2 | Human auth/immutable reviewed input and kernel audit remain ours. Local fixed reviewed-wordcount uses analogous original code, not this TS component. `TaskActions.tsx` is pause/run UI, not the actual review-save implementation |
| OpenDots `src/server/connection-tools.ts`, `connection-routes.ts` | Re-resolve enabled tool, store exact connection/tool/args, owner route uses stored request, TTL/replay check | **Reuse exact-review/revocation pattern**, AG1/AG2 | Tool readOnly annotations/name are untrusted; enabled must not mean safe. Independent policy can still gate. Authenticate owner; deny all unreviewed tools by default |
| OpenDots `connection-store.ts`, same directory | Claim/result/approval linkage and explicit stale interrupted state | **Use uncertainty UX; reject blind external retry**, AG2/AG3 | Stale result-less claim may already have caused remote effect; route reclaims then calls again. Local claim is not remote idempotency. Multi-process one-approval uniqueness needs DB enforcement/review |
| OpenDots `src/server/runner.ts` | Lease/ownership checks, AbortController, interrupted-on-stop, permission fingerprint | **Reference**, AG2/AG3 | AbortSignal only stops a cooperative implementation. No claim of process/provider termination or hard spend control without independent acknowledgment |
| OpenDots `pages.ts`, `page-tools.ts`, `page-service.ts` | expectedRevision transaction/conflicts, Space access recheck, page/thread reservation and recovery | **Defer pages**, after useful company outputs exist | Direct authorized page create/edit tools exist; not all writes require review. Promise.race timeout does not cancel Intelligence. Keep reports private/default, sanitize renderer, no auto-share |
| Both: voice/mobile/messaging/MCP/Composio/payment/computer/server stacks | Broader integrations and interaction patterns | **Reject wholesale host/kernel migration now; defer optional adapters** | Separate terms/accounts/cost/privacy/egress. `mcp_connections.token TEXT` is not our separated credential vault. No raw donor credentials/startup/approval gaps |

## What this review actually changed

Original first-party local executor extends the existing GatewayAdapter and Sentinel—not donor
engines. It now rejects stored-request/preview/output/event corruption, binds relevant reviewed
implementation hashes and relative delivery scope, and refuses ambiguous repeats. The bounded
worker/real stop proof provides a baseline for later donor-inspired adapters, not evidence the
other repositories' full features have been ported. See `services/gateway/PORTED_FROM.md`.

**Priority:** use donor tests/mechanisms to close AG1–AG3 before adding pages, voice, mobile or
another bot framework. The completed reversible consolidation is NOT an external/off-host backup,
full feature adoption, redistribution clearance or production readiness. Keep the source archives,
notices and current private continuation download. The normal cleaner remains cache-only and no
further source deletion is authorized merely by a green verification result.
