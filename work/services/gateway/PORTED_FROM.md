# Gateway execution provenance

`src/local_executor.py`, `local_tool_worker.py` and their tests are original first-party code.
They extend the existing GatewayAdapter/mapper and independent Sentinel policy/Store, preserving
licences of those components. No Rakazo/OpenDots TypeScript implementation is installed in the
first-party runtime or enabled. Original source is now also copied as an INERT reviewed reference
library, not falsely described as an integrated component.

Reviewed design references retained read-only:
- Rakazo Apache-2.0: `packages/adapters/src/routine-coalescing.ts`, `routine-handover.ts`,
  `routine-watch.ts` — occurrence/authority/recovery constraints for future scheduling work.
- OpenDots MIT / Atai Barkai: `src/server/{pages,page-routes,connection-tools,connection-routes,
  connection-store,runner}.ts`, `src/client/PageReviewCard.tsx` — exact stored drafts, review
  receipts, revoked-tool re-resolution and interrupted-state UX. External interrupted retry
  is deliberately **not** adopted as an exactly-once guarantee.

Exact retained bytes and root licences are fingerprinted in `audit/donor-review.json`.
`audit/donor-consolidation.json` maps their newer lossless source vaults and 26 readable references;
all full selected sources were restored before redundant loose-copy removal. Original
metadata names main@2026-11-09 tarballs, not immutable commits; do not invent SHA provenance.
The full continuation manifest has per-file hashes. See `DONOR_REUSE_REVIEW.md` for decisions.
A future literal port must add file-level copyright/licence/change attribution and a proven
revision before being labelled a copied/installed donor feature.
