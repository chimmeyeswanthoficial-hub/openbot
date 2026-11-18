# Bot HQ local derivative patch register

Base: https://github.com/nickvasilescu/bot-hq at
`decf9a215cddd8792a5f20f4a11a87d4dffa6d15`, MIT © 2026 Nick Vasilescu.
This is an explicit local derivative under `apps/bot-hq`, not a silent `repos/` fork,
upstream PR, remote commit or replacement of financial authority. No remote was pushed.

| Seam | Local changes | Why / evidence |
|---|---|---|
| Defaults / entry | package scripts, provider-free env, throwing upstream index, new local entry/app | Upstream startup initializes engines beyond scheduler flag; static import-closure + host denial tests |
| Neutral schema | add `kind`/`hidden` columns in idempotent config migration | First host run4pass/10fail; fix without autonomous init;14pass |
| Sessions | SameSite/partitioned HTTPS preview cookie handling; local access code | Auth required; same-origin JSON writes; no Google/OAuth/provider keys |
| UI | neutral badges, licensed Lucide icons, no logos/favicon; local sign-in/banner/notes/details | Excluded donor artwork has no MIT grant; browser tested with no external resource requests |
| Company execution | fixed Python adapter, separate Sentinel audit DB, zero-cost readiness report, task/transcript receipts | Audit-before-read/write, request identity, report digest and uncertain-job reconciliation tests |
| Dependencies | unused tsx/obsolete esbuild subtree removed, no other version changes | Initial2moderate→final0reported advisories; npm lifecycle scripts always suppressed |
| Upstream helpers | root installer/pack/config/sign-in scripts retained as non-executable reference text | They are not our runbook; no root/cloud/engine operations executed |
| Continuation | pinned restore instructions, source hashes, skill, safe archive generator/verifier | Source/locks transfer, caches/processes/credentials do not; private owner bundle only |

Per-file original hashes/asset omissions: `audit/bot-hq-source-intake.json`.
Current per-file deltas/new files/native-binding digest: `audit/bot-hq-installed-source.json`.
Dependency-only lock delta: `audit/bot-hq-dependency-changes.json`.
Main report and measured limits: `BOT_HQ_INSTALLATION.md`.

Do not import upstream `routes`/`engine`/`loop`/`computer`/provider modules to fix a
local UI symptom. Preserve the independent kernel and complete the disposable
approval/budget/cancellation/delivery boundary before any live agent runtime choice.
