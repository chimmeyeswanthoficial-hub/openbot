# Download / restore / start a new chat

## What to download

**`openbot-continuation.tar.xz`** is the full private-owner continuation package:
first-party project source, lossless donor source vaults/reviewed references with notices, installed local HQ
source, skills/local policies, company records, audit/run evidence, uploads, memory,
brain/method/predictions, dependency/runtime locks and exact continuation instructions.
It is a source/state handoff, **not** an offline binary installation or public release.

Keep the adjacent `.sha256` file / `audit/continuation-bundle.json` for the measured
archive size/digest and validation receipt. The in-archive
`audit/continuation-manifest.json` lists every included file's size/hash/mode plus
explicit omissions/SQLite transformations. The full manifest is **inside the archive only**
to avoid duplicating almost 2MB beside the working tree. Digests detect corruption; they are not
a publisher signature or a security/licence certification.

**`OUR_PROJECT.md`** is the requested single comprehensive owner guide and Bot HQ remaining-value
review, including genuinely preserved exact request versus labelled reconstruction of older intent.
It and the bounded HQ history feature/evidence are included in the refreshed full package.
`WORKFORCE_PLATFORM.md` adds the newer broader work-platform direction, QA/documentation-first
technical choice, candidate services/social/data/video gates and the tested offline workbench.
`audit/workforce-review.json` is the newest feature evidence; older metadata/history/execution
receipts are recoverable through `audit/workforce-evidence-consolidation.json` and its tar command.
`NEXT_CHAT_PROMPT.txt` is the short message to paste with the uploaded package.
Everything required for context is also inside the main package; no old chat is needed.
`WORKSPACE_CLEANUP.md` / `audit/donor-consolidation.json` describe the newer reversible source
consolidation. ALL 5,086 selected Rakazo/OpenDots files are preserved in nested source archives,
with26 reviewed references readable. They are not fully integrated. Keep active HQ/findrepo/OpenBot.
The checked donor recovery tool refuses existing targets and never deletes or runs sources.
The older `openbot-reviewed-overlay.tar.gz` and earlier rollback archives are historical,
not the current full continuation package.

## Newest technical continuation

`ANTIGRAVITY_START.md` contains the immediate backup/import/paste steps. `DELIVERY_PLAN.md` and
`NAMESPACE_EXPERIMENT.md` explain the fixed namespace experiment, truthful default-off dispatcher
and remaining AG1 gates; `audit/progression-review.json` is current feature evidence. Earlier
workforce/donor/HQ receipts are preserved to their named freezes, not retroactive certification.

After the pinned project installer, `make isolation-install` explicitly restores the pinned
non-setuid Bubblewrap tool into excluded cache. `make isolation-test`, `make isolation-demo`
and `OPENBOT_TEST_NAMESPACE=1 make release-check` reproduce the actual namespace profile.
No Docker daemon, account key, provider or system/root installation is required for these fixed
checks on a compatible host. No general customer-code execution is authorized. Cgroups and
mandatory authenticated runtime/secret/tenant controls plus independent review remain AG1.
A normal non-opt-in Python run skips actual namespace tests; never relabel those skips as passes.

## What is intentionally NOT transferred

- `.venv`, `node_modules`, caches, downloaded Node/browser binaries and build outputs;
- authentication codes/sessions, `.env`/private credentials, Git credential/history
  folders and unrelated `.config` harness settings;
- running processes, external provider accounts, literal assistant identity or unlimited memory.

The actual HQ and kernel databases are exported with consistent SQLite backup.
Only HQ authentication/session/login-attempt rows are removed **from the export copy**,
with secure deletion/VACUUM and unchanged business-table row counts checked. Original
working data is not erased. Kernel audit/runs/reports/markers, notes/tasks/skills,
company policies and ledger evidence are retained. SQLite WAL/SHM files are not copied
on top of the consistent backups. Auth is regenerated locally after restore.

Retained older donor snapshots/archives remain for the owner's private continuity.
They are not blanket permission to publish restricted donor assets or separately
licensed Intelligence code. No excluded Bot HQ artwork is part of the new installation.
Do not publish this full private project/state package without a separate rights/data review.

## Restore safely

1. Verify the download digest if you have the adjacent checksum. Inspect path/type/hash
   validation (`audit/continuation-bundle.json`). Never extract over newer work.
2. On a trusted copy of this workspace, verify before extraction:
   `python3 scripts/handoff.py verify openbot-continuation.tar.xz --sha256 DIGEST`.
   A new agent without the script should first inspect the tar with Python stdlib:
   only bounded regular files under `openbot-continuation/`, no absolute/traversal
   paths, backslashes, symlinks/hardlinks, duplicate members or special mode bits.
3. Extract into a **new empty directory**, then enter `openbot-continuation/`.
   **Arena cap:** keep the original download on your own computer. Move only the uploaded
   input copy into excluded `.cache` staging BEFORE extraction: the input archive plus
   its expanded manifest/source plus an existing tree can otherwise exceed128MB. `.cache` is transient,
   not a second durable backup. If an old working tree is present, do restore drills in
   `.cache` rather than leaving two persistent loose projects.
   On Linux/WSL in a new workspace (after validation):

```sh
mkdir -p .cache
STAGE="$(mktemp -d "$PWD/.cache/continuation-incoming.XXXXXX")"
mv -- openbot-continuation.tar.xz "$STAGE/"
mkdir restore  # must be new; do not extract over existing work
tar --no-same-owner -xJf "$STAGE/openbot-continuation.tar.xz" -C restore
cd restore/openbot-continuation
```

   Windows users can use WSL or an xz-capable archive tool; the measured installer is Linux-only.
4. Read `CONTINUE_HERE.md` → `AGENTS.md` → memory → brain → installation/final receipts.
5. Restore the measured Linux x86_64 / Python3.13 environment (downloads need network):

```sh
bash scripts/bot-hq.sh install
export PATH="$PWD/.venv/bin:$PWD/.cache/openbot-toolchains/node-v24.22.3-linux-x64/bin:$PATH"
make lint
make release-check
bash scripts/bot-hq.sh start
# another host terminal:
bash scripts/bot-hq.sh access-code
```

The hash-locked wheel set is measured for Python3.13/Linux x86_64. For another
platform/runtime, review/resolve a new lock; do not disable hash/engine checks blindly.
The installer restores our script executable bits if a transfer normalized file modes.
No model/payment/provider credential is required. All those runtime routes stay disabled.
Stop the local server with Ctrl-C or its process manager; preserve `.openbot/`.

Optional browser verification needs additional system libraries and Chromium:

```sh
node apps/bot-hq/node_modules/playwright/cli.js install chromium
# review then install the OS dependency plan if needed (may require admin privileges):
node apps/bot-hq/node_modules/playwright/cli.js install-deps --dry-run chromium
node scripts/test-bot-hq-browser.mjs
```

Do not run upstream's real-provider e2e or quarantined cloud/root helper scripts.

## Completed restoration evidence

**Current progression freeze:** `audit/progression-review.json` records exact full gates and
same-host independent pinned source installation. The adjacent `audit/continuation-bundle.json`
records the actual final archive/extraction; only those explicit observations count. Import
instructions/tool pins are not direct Antigravity shipment or independent security review.

**Current workspace-cleanup freeze:** `audit/donor-consolidation.json` preserves actual
pre-removal full donor restores and current gates/independent-source scope. The adjacent
`audit/continuation-bundle.json` identifies the exact final package and its actual extraction
checks; do not assume a final-archive reinstall unless that receipt explicitly records it.

**Prior HQ-history/master-guide freeze:** `audit/hq-history-review.json` records that freeze's gates,
source delta and preserved primary/donor state. Local Python: **338 passed /2 skipped /340**.
A newly extracted donor-free source candidate was independently installed into fresh dependency/
toolchain trees on the same host: **337 passed /3 skipped /340**. Both release gates, Node **25 reuse
+26 HQ** (17 host +9 shared history-state), lint/build/typecheck, verify22/0/7, smoke10/10 and actual
fixed-process probes passed. Both real HTTP Chromium history flows recovered451 rows/225 notes,
including a503retry; providers remained off. Not a separate host or external security audit.

That history-freeze final package added documentation/receipts/lossless consolidation, not runtime
changes. The newer workforce checkpoint DOES add offline runtime source/tests. Current full
extraction/reconciliation is separately recorded in the adjacent
`audit/continuation-bundle.json`; use that receipt's actual SHA/size, not the candidate or an old
download. Older XML/log bytes remain exactly recoverable through
`audit/master-guide-evidence-compression.json`, including the grouped historical test-log archive.
Optional `node scripts/test-hq-history-browser.mjs` avoids a new large screenshot.

**Earlier execution-freeze evidence:** `audit/EXECUTION_FINAL_VERIFICATION.md` and
`audit/execution-restore.json` preserve local338/2/340, donor-free337/3/340 and Node25+14 at their
named freeze. They are not retroactive proof of later HQ code. The updated IDE/owner/donor and
fixed-execution handoffs remain included. PG/HTTPS/provider/pilot limitations remain explicit.

The following is **historical completed HQ/checkpoint restore evidence**, not the new full-suite
count: `audit/continuation-restore.json` records actual extraction of every payload with matching
hash/size/mode; both standalone SQLite exports passed integrity checks and preserved all
business-table row counts/hashes. HQ auth rows were zero and no known active authentication
value appeared in any exported file. Source authentication/business state was not erased.
From archived source/state, a donor-free independent install passed Python **290/3/0/293**,
Node **25+14**, builds/lint, verify **22/0/7** and smoke **10/10**. Old cookie/code were refused,
new private auth worked, saved task/kernel replay kept six audit rows, and one new fixed report
plus HTTP SSE hello passed in the disposable copy only. Primary audit/task counts stayed6/1.
Local full Python is **291/2/0/293**. Skips are not passes; HTTPS preview cookies remain unmeasured.

The final receipt reports the actual sender workspace budget including the archive. Headroom is
small: inspect before growing the tree or leaving duplicate packages, never delete business/run
history to make room. Extraction also creates the roughly2MB `audit/continuation-manifest.json`.
Keep its original inside your private downloaded archive. Before generating a later continuation
on capped Arena, stage that redundant extracted manifest under excluded `.cache` (or retain it
outside Arena) after validation; the packager embeds a fresh manifest and intentionally will not
delete an existing loose one for you. Never stage business data this way to hide it from backups. Compression uses LZMA2 preset9 extreme; creation may need about700MB RAM,
and verification/extraction a64MB dictionary. Dependencies/browser/OS packages are still separate.
Local verification servers were stopped after measurement; the launcher starts them again.

## Resume work, not old claims

The completed local HQ company report is one real **bounded local evidence** tool,
not full agent/tool execution, model intelligence, revenue or production approval.
The separate fixed trusted-host executor now supplies a narrow process/SSE/review/attempt-quota/
stop/outbox baseline. The next major task is AG1 mandatory authenticated integration and real
OS/egress isolation, then AG2 actual agent transport/financial limits/provider stop evidence.
Human legal/pricing/accounts/spend/sensitive outbound/release authority and the private
**1–6-month evidence-backed pilot** remain binding.

No background business work continues merely because these files were downloaded.
The current chat's local preview process, if still alive, is not a portable process.

Space-preserving upload recovery: the original architecture PDF is retained byte-exact as
`uploads/Untitled document (14).pdf.xz` (857,243→602,340B), verified in
`audit/workforce-evidence-consolidation.json`. View a restored copy via
`xz -dc "uploads/Untitled document (14).pdf.xz" > .cache/restored-architecture.pdf`;
original-name references/source pins identify the recovered PDF, not discarded content.

Historical workforce check: primary and independent-source installation each418pass/2PGskip/420,
Node25+26 and full gates. Exact scope is in audit/workforce-review.json; final archive extraction
is checked against the same245 tested runtime/config/skill files, not called a second reinstall.
