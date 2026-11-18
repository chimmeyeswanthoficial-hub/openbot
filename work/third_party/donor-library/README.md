# Readable donor reference library — inert, not installed integrations

These are the **26 exact-byte previously reviewed reference files** from Rakazo (14) and OpenDots
(12), including both root licences. The original relative paths are preserved below each donor
name, except `infra/compose/backup-drill.sh` is named `backup-drill.sh.txt`. Copies are non-executable
mode0644. They are not compiled/imported, active agent skills, permission grants or enabled engines.

All **5,086 selected source files**, including still-unreviewed and deferred work, are also preserved
in `archive/donor-sources/{rakazo,OpenDots}.tar.xz`. Every recovered file's hash/size/original mode
was compared with the source before only the redundant loose copy was removed. The private OpenDots
`.env` was left untouched at the old path and is not in the public-source vault or continuation.

- `WORKSPACE_CLEANUP.md`: what stayed, space measurement, limits and safe recovery commands.
- `DONOR_REUSE_REVIEW.md`: source-backed reuse/defer/reject matrix and guard before adoption.
- `audit/donor-review.json`: unchanged original content fingerprints and reviewed-reference hashes.
- `audit/donor-consolidation.json`: full source vault hashes, readable mapping and actual restore proof.

## Useful seams preserved directly

| Donor | Readable paths | Intended use; not shipped behavior |
|---|---|---|
| Rakazo | `packages/adapters/src/routine-{coalescing,watch,handover}*` | Timer provenance, unattempted-only catch-up, fencing, bounded change checks and lineage; adapt after AG1/AG3 |
| Rakazo | `ticket-context.ts`, `group-handoff.ts`, `docs/{board,groups}.md` | Bounded untrusted task context and guarded handoff; not shared venture/financial authority |
| Rakazo | `docs/skills.md`, `skills-lock.json` | Preview/draft/review/lock workflow; no automatic skill installation or model self-modification |
| Rakazo | `docs/self-host-backups.md`, `infra/compose/backup-drill.sh.txt` | Checklist only; a checksum/decrypt/listing check is not an actual application/DB restore |
| OpenDots | `src/client/PageReviewCard.tsx`, `src/server/{page-routes,pages}.ts` | Exact stored-draft review/transaction/conflicts; TaskActions is not the review-save implementation |
| OpenDots | `src/server/{connection-tools,connection-routes,connection-store,connections}.ts` | Tool re-resolution, revocation and interrupted state; reject blind retries of uncertain external effects |
| OpenDots | `src/server/{runner,page-tools,page-service}.ts`, `src/client/TaskActions.tsx` | Runner/revision and UX reference; timeout/AbortSignal is not hard stop, and direct page tools can write |

## Provenance and licences

Rakazo: root Apache-2.0, original `LICENSE` retained. OpenDots: root MIT, copyright Atai Barkai,
original `LICENSE` retained. Preserve applicable notices/change attribution when porting. Root
licences do not clear every dependency, asset, provider account or separately licensed CopilotKit
Intelligence. Full archived files retain their original copyright headers/notices.

The snapshot labels are main@2026-11-09 tarballs, **not established immutable upstream commit IDs**.
Hashes bind exact retained bytes, not publisher identity. This is private owner continuity—not
permission to publish restricted assets. Source retention, integration, execution permission and
security/quality certification are separate questions. Never run these references just because
they are present. The normal cleaner never removes donor vaults/notices or business records.
