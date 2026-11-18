# OpenBot HQ — installed local-only Bot HQ profile

Pinned upstream: https://github.com/nickvasilescu/bot-hq at
`decf9a215cddd8792a5f20f4a11a87d4dffa6d15`. MIT © 2026 Nick Vasilescu.

This is an installed, modified **local workspace**, not a running Hermes/Orgo/
Composio/xAI integration. Its default entry is `server/src/local-entry.ts`.
The independent company policy/audit/ledger kernel is retained outside this app.

From the **project root**:

```sh
bash scripts/bot-hq.sh install      # Linux x86_64, Python 3.13; pinned/hash-checked downloads
bash scripts/bot-hq.sh test         # rebuild/typecheck; disposable kernel + host tests
bash scripts/bot-hq.sh start        # foreground, authenticated, 0.0.0.0:8787
# another terminal:
bash scripts/bot-hq.sh access-code  # paste into Local access code; never commit/share it
```

The local profile reuses Bot HQ's SQLite schema/store, sessions, event hub, roster,
transcripts, task UI and skill data. A real `company.readiness` action crosses into
the fixed Python adapter, persists independent Sentinel audit rows BEFORE evidence
reads/writes, and returns hashed evidence. Successful tasks retain the kernel run,
input hashes and completion/report integrity reference. This reads existing
verification receipts; it **does not run the verification suite** or declare launch.

## Deliberately unavailable

All model/provider/voice/Google/OAuth/app connections, screens/VNC/computer controls,
MCP, shell/browser tools, schedulers, sensitive outbound and financial authority.
Their API routes are **not mounted**. Upstream `index.ts` throws instead of starting.
Root-install/pack/config helper scripts are non-executable reference text under
`upstream-reference/`; do not run/copy them as our installation instructions.
No `.env` or dummy provider key is needed or loaded by the local launcher.

Notes and skills are inert local data. Instructions in them do not grant permissions.
Interrupted jobs keep markers and require human/engineering reconciliation, never
an automatic new request ID to repeat an uncertain action. This same-user adapter
is not a hostile-process/tenant sandbox and does not fix the upstream browser/shell
approval gap. Full execution/approval/budget/cancellation/delivery work remains.

## Licence / assets

Keep `LICENSE` and `THIRD_PARTY_NOTICES.md`. Excluded donor silhouettes/eyes/icons,
app logos and favicon were NOT installed. Neutral letter badges are new; replacement
icons use the attributed Lucide package. No external logo/font URLs are fetched.
`README.upstream.md` is the historical upstream README, not our active runbook.

State is under `.openbot/hq/` and `.openbot/hq-kernel/`, outside this source directory.
The toolchain, dependencies, builds, authentication code and processes do not survive
workspace snapshots; use the installer after transfer. See root
`BOT_HQ_INSTALLATION.md`, `CONTINUE_HERE.md` and `audit/bot-hq-*.json` for evidence,
known gaps, provenance and the current continuation package.
