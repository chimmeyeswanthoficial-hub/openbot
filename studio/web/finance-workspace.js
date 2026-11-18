/* Original OpenBot UI for the attributed OpenMuse-derived read-only CSV module.
 * No CSV content is sent to a server, model, browser storage or accounting ledger.
 */
(() => {
  'use strict';
  function create({esc, icon, toast, download, refresh, chooseFile = () => document.querySelector('#finance-file').click()}) {
    const api = window.OpenBotFinance;
    const fresh = () => ({csv:'', currency:'', confirmed:false, report:null, error:'', busy:false, hint:'No file selected. Paste CSV or choose a local file.'});
    let state = fresh(), readEpoch = 0;
    const short = (value, limit = 100) => value.length > limit ? value.slice(0, limit) + '…' : value;
    const empty = () => '<div class="finance-empty"><span class="pulse-icon">'+icon('file')+'</span><h3>No preview calculated.</h3><p>Choose a source currency, check the sign convention, then preview. Nothing will be sent, reconciled or written to a ledger.</p></div>';
    function result() {
      const r = state.report;
      if (!r) return empty();
      const money = value => esc(api.formatMinor(value, r.currency));
      const max = r.categories[0]?.amount_minor || 1;
      return `<div class="finance-result-header"><div><div class="eyebrow">UNRECONCILED FILE PREVIEW</div><h2>${r.count.toLocaleString('en-US')} imported rows</h2><p class="muted">${esc(r.period.from)} to ${esc(r.period.to)} · ${esc(r.currency)} only · duplicates retained</p></div><button class="button small" id="finance-download">${icon('download')}Preview JSON</button></div><div class="finance-metrics"><div><span>Imported expenses</span><strong>${money(r.spending_minor)}</strong></div><div><span>Imported income</span><strong>${money(r.income_minor)}</strong></div><div><span>Net imported</span><strong>${money(r.net_import_minor)}</strong><small>Income minus expenses · not a balance</small></div></div><p class="finance-warning">This is not a bank balance, profit, settled earnings, tax calculation, verified revenue or permission to spend. Refunds, transfers, missing rows and source classifications can make these totals misleading.</p>${r.duplicate_rows ? `<p class="finance-warning" id="finance-duplicates">${r.duplicate_rows.toLocaleString('en-US')} exact duplicate row${r.duplicate_rows===1?'':'s'} found. They are included in the totals, not silently removed.</p>` : '<p class="inline-note" id="finance-duplicates">No exact duplicate date/description/amount/category rows found. This is not reconciliation or fraud detection.</p>'}<section class="finance-section" aria-label="Imported expense categories"><h3>Expenses by source category</h3>${r.categories.length ? `<div class="finance-bars">${r.categories.slice(0,10).map(c=>`<div class="finance-category"><div><span>${esc(short(c.name,80))}</span><b>${money(c.amount_minor)}</b></div><div class="finance-bar" aria-hidden="true"><span style="width:${Math.max(0.2, c.amount_minor/max*100).toFixed(2)}%"></span></div></div>`).join('')}</div><p class="inline-note">${r.categories.length>10?'Largest 10 of '+r.categories.length+' categories shown. ':''}Categories come from the file, not an AI or accounting determination.</p>` : '<p class="muted">No positive expense amounts in this file.</p>'}</section><section class="finance-section"><h3>Imported transaction preview</h3><p class="inline-note">Showing ${Math.min(50,r.count)} of ${r.count} rows. Descriptions/categories are truncated on screen. A JSON download includes all imported rows and may contain sensitive data.</p><div class="finance-table-wrap" role="region" aria-label="Imported transaction rows" tabindex="0"><table class="finance-table"><thead><tr><th scope="col">Date</th><th scope="col">Description</th><th scope="col">Category</th><th scope="col">Amount</th></tr></thead><tbody>${r.transactions.slice(0,50).map(t=>`<tr><td>${esc(t.date)}</td><td>${esc(short(t.description))}</td><td>${esc(short(t.category,60))}</td><td>${money(t.amount_minor)}</td></tr>`).join('')}</tbody></table></div><p class="inline-note">Positive expense / negative income, exactly as confirmed. Preview JSON uses integer minor units (one hundredth of the selected currency), not floating-point ledger entries.</p></section>`;
    }
    function view(heading) {
      return `<div class="page finance-page">${heading('LOCAL FILE. NO ACCOUNT CONNECTION.','Understand a spending CSV.','A read-only preview adapted from OpenMuse. Your file stays in this browser tab, even if draft saving is enabled. It never changes the accounting ledger.')}<section class="finance-boundary" aria-label="Financial preview boundaries"><span class="status-pill">Read-only · no bank connection</span><p>No model, upload, currency conversion, accounting import, verified earnings or spend authority. Use only data you are allowed to inspect on this device.</p></section><div class="finance-layout"><section class="panel finance-input" aria-labelledby="finance-input-title"><div class="finance-input-heading"><h2 id="finance-input-title">Bring your own CSV</h2><button class="text-button" id="finance-sample">Try fictional example</button></div><p class="muted">Required columns: <code>date,description,amount,category</code>. ISO dates; plain amounts with up to two decimals. Optional <code>currency</code> must match your selection.</p><label for="finance-csv">Transaction CSV<textarea id="finance-csv" rows="9" maxlength="500000" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="date,description,amount,category&#10;2026-10-01,Coffee,10.10,Food" aria-describedby="finance-limit">${esc(state.csv)}</textarea></label><div class="finance-file-row"><button class="button small" id="finance-choose">${icon('file')}Choose local CSV</button><p id="finance-hint" class="inline-note" role="status">${esc(state.hint)}</p></div><p class="inline-note" id="finance-limit">At most 500,000 UTF-8 bytes and 5,000 transactions. No amount symbols, thousands separators or mixed currencies. No file is automatically analysed or saved.</p><label for="finance-currency">Source currency<select id="finance-currency"><option value="">Choose explicitly</option>${api.CURRENCIES.map(c=>`<option value="${c}"${state.currency===c?' selected':''}>${c} · two-decimal amounts</option>`).join('')}</select></label><label class="finance-confirm"><input type="checkbox" id="finance-confirm"${state.confirmed?' checked':''}><span>I checked that the entire CSV uses only the selected currency, <b>positive expenses</b> and <b>negative income</b>. This confirms the preview convention, not the correctness or settlement of the source data.</span></label><p class="form-error" id="finance-error" role="alert">${esc(state.error)}</p><div class="finance-actions"><button class="button primary" id="finance-analyze"${state.busy?' disabled':''}>Preview spending</button><button class="button ghost" id="finance-clear">Clear imported data</button></div><p class="inline-note">Tab memory only. Reloading clears this feature; enabling “Remember drafts” does not save transaction data. Clearing a tab cannot promise secure memory or device erasure.</p></section><section class="panel finance-output" id="finance-results" aria-label="Unreconciled CSV results" aria-live="polite">${result()}</section></div><p class="finance-attribution">CSV parser adapted from CopilotKit/OpenMuse, MIT · pinned source and full notice are in <code>studio/third_party/openmuse/</code>. This preview is not a bank, bookkeeping service or financial adviser.</p></div>`;
    }
    function invalidate() {
      readEpoch++;
      state.report = null; state.error = ''; state.busy = false;
      const results = document.querySelector('#finance-results');
      if (results) results.innerHTML = empty(); // Static first-party markup only.
      const error = document.querySelector('#finance-error');
      if (error) error.textContent = '';
      const button = document.querySelector('#finance-analyze');
      if (button) button.disabled = false;
    }
    function input(target) {
      if (!['finance-csv','finance-currency','finance-confirm'].includes(target.id)) return false;
      invalidate();
      if (target.id === 'finance-confirm') state.confirmed = target.checked === true;
      else {
        if (target.id === 'finance-csv') state.csv = target.value;
        else state.currency = target.value;
        state.confirmed = false;
        const confirm = document.querySelector('#finance-confirm');
        if (confirm) confirm.checked = false;
      }
      state.hint = 'Tab memory only. Input changed; preview must be recalculated.';
      const hint = document.querySelector('#finance-hint');
      if (hint) hint.textContent = state.hint;
      return true;
    }
    function clear() {readEpoch++; state = fresh();}
    function click(id) {
      if (id === 'finance-choose') chooseFile();
      else if (id === 'finance-sample') {
        clear();
        state.csv = 'date,description,amount,category\n2026-10-01,Fictional salary,-1000.00,Income\n2026-10-02,Fictional groceries,120.25,Food\n2026-10-03,Fictional train ticket,29.75,Travel\n2026-10-03,Fictional groceries,120.25,Food';
        state.hint = 'Fictional example, not money received. Choose a currency and check the convention.';
        refresh();
      } else if (id === 'finance-clear') {
        clear(); refresh(); toast('Imported CSV and preview cleared from this tab. No ledger, source file or account was modified. This is not a secure-erasure claim.');
      } else if (id === 'finance-analyze') {
        if (state.busy) return true;
        state.report = null; state.error = '';
        try {
          state.report = api.analyzeSpending(state.csv, {currency:state.currency, amountConvention:api.CONVENTION, singleCurrencyConfirmed:state.confirmed});
          state.hint = 'Preview calculated locally. Data is unverified; no upload, account or ledger action.';
        } catch (error) {
          state.error = error.message;
          state.hint = 'Input retained. No preview, upload or account action succeeded.';
        }
        refresh();
      } else if (id === 'finance-download') {
        if (state.report) {
          if (download('OpenBot-unreconciled-spending-preview.json',state.report) !== false) toast('Preview JSON download requested with all imported rows. Treat it as sensitive, unverified source data; no accounting or bank action occurred.');
        }
      } else return false;
      return true;
    }
    async function readFile(target) {
      const file = target.files?.[0]; target.value = '';
      if (!file) return;
      invalidate();
      const epoch = readEpoch;
      state.confirmed = false;
      if (file.size > api.MAX_CSV_BYTES || !/\.csv$/i.test(file.name)) {
        state.error = 'Choose a .csv file no larger than 500,000 UTF-8 bytes. Nothing was uploaded.';
        state.hint = 'Selected file refused; previous text retained. No upload occurred.';
        refresh(); return;
      }
      state.busy = true; state.hint = 'Reading the selected file locally…'; refresh();
      try {
        const bytes = await file.arrayBuffer();
        const text = new TextDecoder('utf-8',{fatal:true}).decode(bytes);
        if (epoch !== readEpoch) return; // Clear/edit/new selection wins over late reads.
        state.csv = text;
        state.hint = 'File read locally, not uploaded or analysed. Choose a currency and check the convention.';
      } catch (_) {
        if (epoch !== readEpoch) return;
        state.error = 'Could not read a valid UTF-8 CSV. No preview or upload succeeded; existing input is retained.';
      } finally {
        if (epoch === readEpoch) {state.busy = false; refresh();}
      }
    }
    return Object.freeze({view, input, click, readFile, clear});
  }
  Object.defineProperty(window,'OpenBotSpendingWorkspace',{value:Object.freeze({create}),writable:false,configurable:false});
})();
