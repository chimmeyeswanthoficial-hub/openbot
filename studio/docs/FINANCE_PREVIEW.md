# OpenMuse-derived, read-only spending preview

## What is really integrated

Open **Spending preview** in Studio. Paste a transaction CSV or choose a local UTF-8
`.csv` file, choose INR/USD/EUR/GBP, inspect and explicitly confirm the **positive
expenses / negative income** convention, then select **Preview spending**. A
fictional example is available; it is not an account or money-received demonstration.

This calls the actual adapted module in `web/finance-preview.js` inside the browser,
not a mock response or a remote financial service. The CSV scanner, report shape
and regression vectors were adapted from the user-confirmed CopilotKit/OpenMuse
repository at immutable revision `a4944f4c471d3dc93b8bfc060b5da309b5216ab2`.
The public repository metadata resolves that requested URL to `CopilotKit/openfuse`.
This is the selected bounded review revision, **not a latest-branch or whole-repo audit**.

The full MIT notice, exact unmodified reviewed TypeScript module and three original
test files, file hashes and adoption decisions are retained in
`third_party/openmuse/`. The adapted JavaScript and built single-file HTML also
carry the full upstream copyright/permission notice. Studio's remaining first-party
UI/planner code stays original. No upstream dependency graph was installed.

## Input contract and differences from upstream

- Required headers, in any order: `date,description,amount,category`. Case/outer
  whitespace is normalized for header lookup. Duplicate required headers fail closed.
  Distinct extra fields and duplicate irrelevant fields may be present but are ignored.
- Optional `currency` is checked on every transaction and must match the explicitly
  selected currency. Duplicate currency headers fail. Without a currency column, the
  application relies on the user's confirmation; it **cannot detect hidden currency mixing**.
- Only four explicitly supported **two-decimal** currencies: INR, USD, EUR, GBP.
  No guessed default, FX, crypto, zero-/three-decimal currencies or locale inference.
- At most **500,000 UTF-8 bytes / 5,000 transaction records**. Input files must be
  `.csv`, UTF-8 and within the byte limit. Invalid UTF-8 files are rejected rather
  than silently replacement-decoded; control/binary text is rejected.
- RFC-style comma-separated quoted fields, escaped quotes, embedded line endings,
  CR/LF/CRLF and an initial BOM are supported. Characters following a closing quote
  are rejected. Blank records are ignored; no partial report on malformed input.
- Gregorian `YYYY-MM-DD` dates are checked without normalizing invalid calendar days.
- Plain signed decimal amounts only: at most two fractional digits, no symbol,
  exponent, parentheses, thousands separator or floating special value. Individual
  amount text is bounded to 32 characters; absolute amount limit is `1,000,000,000,000`
  minor units. Leading zeros within that bound are allowed.
- **Exact integer minor units**, parsed using integer arithmetic rather than upstream's
  `Math.round(Number(amount) * 100)`. Every aggregation is checked for a safe integer;
  5,000 maximum-size amounts remain exact. Formatting uses integer digit strings.
- Positive amounts are classified as expenses, negative amounts as income. The
  user must verify this convention; refunds and transfers can make it misleading.
- Exact normalized date/description/amount/category duplicates are **disclosed and
  retained**, not silently deduplicated. This is not fraud detection or reconciliation.
- “Net imported” is imported income minus expenses. The upstream `saved` label is
  deliberately not used. No profit, bank-balance, settled-revenue or earnings proof.

The display shows the largest ten expense categories and first fifty transactions,
with long source strings truncated visually. Explicit **Preview JSON** download
contains the full imported rows and must be treated as sensitive. It uses
`amount_minor`, `income_minor`, `spending_minor` and `net_import_minor`, not floating
currency amounts. Every report has false `ledger_writes`, `bank_connected`,
`earnings_verified` and `permission_to_spend` flags. They describe a read-only code
boundary, **not a cryptographic approval or trusted financial receipt**.

## Privacy, invalidation and authority

The file is read with the browser's local File API. CSV contents never enter a
Studio request, model call, telemetry event, browser draft storage or kernel ledger.
Navigation can retain the import in tab memory. Reload/clear removes the application's
active reference; it is **not secure erasure of browser/OS memory, downloads or backups**.
“Remember drafts” intentionally does not save imported financial data. A user-requested
JSON download is a separate sensitive file under the user's control.

An edit to CSV, currency or confirmation removes the old report and download button.
CSV/currency changes also reset confirmation. Late local-file reads cannot resurrect
cleared or edited data. Invalid files preserve previous input but remove stale output.
Descriptions, categories, URLs, formulas and markup are escaped text, never rendered
as links, HTML, instructions or spreadsheet cells. There is no CSV/spreadsheet export.

This module does not connect a bank, call CopilotKit Intelligence, infer money earned,
post ledger entries, reconcile provider usage, approve a spend, or change the kernel's
policy/approval/budget/operational authority. No bank credentials are requested.

## Verification and limits

```sh
node --test tests/finance-preview.test.cjs
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/build-web.py
```

Node 20+ is used for the dependency-free adapted module tests. With a separately
installed Playwright 1.56.1 and browsers, start the local server and run:

```sh
PREVIEW_URL=http://127.0.0.1:4184 TEST_ENGINE=chromium node scripts/test-finance-ui.cjs
PREVIEW_URL=http://127.0.0.1:4184 TEST_ENGINE=webkit node scripts/test-finance-ui.cjs
```

These browser cases exercise actual local imports/calculation/downloads, validation,
stale-result and in-flight read rejection, literal unsafe text, optional-storage
exclusion, mobile layouts, opaque offline iframe behavior and request observation.
All financial inputs used in recorded tests are synthetic. Upstream TypeScript tests
are **retained, not claimed to execute unchanged**; adapted regression vectors run
against the actual JavaScript module without Zod. See root `VERIFICATION.md` for the
checkpoint's measured outcomes and retained initial test-fixture failures.

This useful bounded adoption does not finish R02's other candidate reviews or the
product's public-release roadmap. Independent security and usefulness acceptance,
real integrations, operations and the observed pilot remain open.
