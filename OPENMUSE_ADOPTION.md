# OpenMuse adoption — actual code, not an all-features claim

**Bounded predecessor intake record; selected pin retained unchanged. Public release: blocked.**
The owner confirmed **https://github.com/CopilotKit/OpenMuse** as the intended donor.
Public repository metadata resolves that URL to **CopilotKit/openfuse**. Alias
resolution is not affiliation, a whole-repository review or a claim that OpenBot
runs that product.

## Exact review boundary

- Selected immutable commit: **`a4944f4c471d3dc93b8bfc060b5da309b5216ab2`**.
- Upstream recorded committer time: `2026-10-26T15:38:10Z`; an observation, not pilot time.
- This is the explicitly selected bounded review revision. We do **not** claim to
  have adopted or audited the current/latest branch. The intake query cutoff was
  `2026-11-10T18:29:59Z`; later upstream changes are not included in this review.
- Actual root license read: **MIT**, `Copyright (c) 2026 OpenMuse contributors`.
  Exact license SHA-256:
  `399a9cccf1b228c9e8ad348ef66a0a5802d438d46735d0d068390925aee5ee36`.
- License and immutable reviewed sources/tests are included in
  `studio/third_party/openmuse/`. `PROVENANCE.json` identifies every retained source.
  Full notice is also carried in the adapted JS and built HTML so standalone use
  does not discard the upstream permission/warranty text.
- Donor root README/package/workspace metadata and nontruncated tree were inspected
  for dependency/service boundaries. No donor package installation, task worker,
  OAuth flow, model call, telemetry or paid service was activated.

## Adoption ledger

| Feature / path | Actual status | OpenBot result / remaining boundary |
|---|---|---|
| `apps/server/src/engine/finance.ts` | **Code adapted and integrated** | Its CSV scanner/report structure is ported to dependency-free `studio/web/finance-preview.js` and called by the real **Spending preview** route. Original browser UI is `finance-workspace.js`. |
| `tests/finance.test.ts`, `finance-byte-limit.test.ts`, `finance-headers.test.ts` | **Regression vectors adapted** | Quoting, BOM, record endings, UTF-8 boundaries and duplicate-header regressions run against the actual JS adapter. Unmodified TS files are retained for provenance; we do not claim they ran unchanged. |
| `apps/mobile/src/conversation-queue.ts` | **Source inspected; reference only** | One-run-at-a-time composing and no implicit resend on uncertain failure are useful lessons. Not copied, not integrated or claimed tested here; a real queue belongs behind R03's authenticated durable-work boundary. |
| Computer drafts and thread artifacts | **Tree candidates only** | Candidate paths identified; implementations not reviewed or adopted in this bounded intake. Do not call retained drafts/PDF integration complete. |
| Documents, PDF workflows, visible tasks, goals/monitors | **Deferred product candidates** | Review individual modules/licenses and integrate through the existing authority/data lifecycle before use. No PDF generation, Gmail/Calendar send or monitor service added here. |
| Browser session/takeover, shell and Docker computer services | **Deferred; not executed** | Need hostile-host/egress/secret/control-plane review and exact host authorization. A Docker container is not the requested full per-bot VM. |
| Google/OAuth, CopilotKit Intelligence, search/telemetry defaults | **Not imported or activated** | Separate credentials, terms, privacy, consent, account and paid-use decisions are required. MIT repository code is not a service entitlement or service-license clearance. |
| OpenDots, Rakazo, Bot HQ and Grok | **Prior scoped status unchanged** | See `studio/docs/REUSE.md`. No “we copied everything”, all-feature compatibility or closed Grok asset/code claim. |

## What was changed rather than copied blindly

The donor parser's useful strict CSV state machine and regression coverage are
preserved in an attributed port. Its Zod dependency, server `Buffer` use, floating
`Math.round(Number(amount) * 100)` arithmetic and misleading `saved` label are not
carried over. The port uses browser `TextEncoder`, checked integer minor units,
explicit source-currency/sign confirmation, Gregorian dates, duplicate disclosure,
input limits and output labels that do not imply financial truth.

The new UI is read-only and browser-local. It never uploads transaction contents,
writes a ledger, connects a bank, infers settled earnings or grants spend authority.
Optional “Remember drafts” excludes financial imports. Edits invalidate results and
late file reads cannot restore cleared/changed input. Text is escaped, not rendered
as HTML or spreadsheet instructions. JSON downloads are explicit and sensitive.

See **`studio/docs/FINANCE_PREVIEW.md`** for the exact format, caps and limitations.
The `work/` kernel and its independent approval/budget/audit logic remain unchanged.
This successor replaces the client with the shared light UI and now implements a
bounded authenticated fixed-owned QA path. It does not connect models, real PCs,
IDEs, banks or social accounts. See `studio/docs/INTEGRATION_CONTRACT.md`.

## Verification scope

The actual adapted module has 19 dependency-free Node tests. The browser workflow
has 21 observed checks in each Chromium and WebKit, including local file reads,
integer JSON, invalid-input refusal, optional-storage exclusion, in-flight read
races, literal unsafe text, mobile layout and a restricted offline iframe. The predecessor
workspace browser checks were a separate 27 cases per engine; the current light
interface has 35 per engine, not a feature-completion
percentage. Python export/build tests retain the exact notices/source and check
that the actual single-file build embeds the reviewed assets and CSP.

The retained first module-test failure was malformed CSV in a new test fixture; it
was corrected rather than weakening quote validation. The first new browser-test
runs had an assertion wording mismatch (`not be sent` versus `Nothing will be sent`);
that assertion was corrected. Original red logs remain in the checkpoint evidence.
Final outcomes, hash checks and any archive reconstruction reruns are reported in
`VERIFICATION.md`; the source export is not a signature or independent acceptance.

## Remaining work

This closes **one bounded useful adoption**, not R02 as a whole and not public
readiness. The complete R01–R13 roadmap is **`PUBLIC_RELEASE_ROADMAP.md`**. The bounded Studio→authenticated-kernel owned-QA workflow and negative
permission/replay/revocation tests are now implemented and locally verified.
Next are owner staging/native device and real-host/provider acceptance. Real providers, PCs/IDEs, official social accounts,
security/native/operations acceptance, protected independent evaluation, the actual
1–6-month private pilot (at least 30 consecutive observed days) and human release
approval remain open. Accepted real observed pilot days: **0**.
