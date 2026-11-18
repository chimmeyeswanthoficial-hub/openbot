# OPENBOT-OS patches (edits inside repos/)

Every `// OPENBOT-OS:` / `# OPENBOT-OS:` marker inside `repos/` must have a row here, and every row
must have a marker. `scripts/os-markers.sh` enforces both directions in CI.

**Current state: no patches.** Our code lives in `services/`, `packages/` and plugin seams, per D2
in `STACK_DECISIONS.md`. When the first patch is needed, add a row:

| Marker | File | Why | Ledger / issue | Upstream PR | Status |
|---|---|---|---|---|---|
| _example_ | `repos/OpenBot/server/src/audit/row.ts` | routine initiator must reach the audit row | `pm_2026_11_10_…` | — | pending |
