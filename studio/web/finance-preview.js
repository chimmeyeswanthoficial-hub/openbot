/*
 * SPDX-License-Identifier: MIT
 * CSV scanner/report structure adapted from CopilotKit/OpenMuse (canonical openfuse),
 * apps/server/src/engine/finance.ts at a4944f4c471d3dc93b8bfc060b5da309b5216ab2.
 * Copyright (c) 2026 OpenMuse contributors. Full notice and exact reviewed source:
 * studio/third_party/openmuse/. OpenBot modifications: browser-only execution,
 * explicit source currency/sign confirmation, exact integer minor units, duplicate
 * disclosure, Gregorian dates, bounded input, and no ledger/account authority.
 *
 * MIT License
 * Copyright (c) 2026 OpenMuse contributors
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */
(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else Object.defineProperty(root, 'OpenBotFinance', {value: api, writable: false, configurable: false});
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';
  const MAX_CSV_BYTES = 500000;
  const MAX_TRANSACTIONS = 5000;
  const MAX_ROW_MINOR = 1000000000000n;
  // Only these tested two-decimal currencies. No inferred currency or FX conversion.
  const CURRENCIES = Object.freeze(['INR', 'USD', 'EUR', 'GBP']);
  const CONVENTION = 'positive_expenses_negative_income';
  const required = ['date', 'description', 'amount', 'category'];

  function checkCurrency(currency) {
    if (!CURRENCIES.includes(currency)) throw new Error('Choose INR, USD, EUR or GBP. No currency conversion is available.');
  }
  function checkOptions(options) {
    if (!options || typeof options !== 'object' || Array.isArray(options) ||
        Object.keys(options).sort().join(',') !== 'amountConvention,currency,singleCurrencyConfirmed' ||
        options.singleCurrencyConfirmed !== true || options.amountConvention !== CONVENTION) {
      throw new Error('Confirm one source currency and positive expenses / negative income before previewing.');
    }
    checkCurrency(options.currency);
  }
  function parseAmountMinor(source) {
    if (typeof source !== 'string' || source.length > 32) throw new Error('Transaction amount is out of range or not plain decimal text.');
    const match = /^([+-]?)(\d+)(?:\.(\d{1,2}))?$/.exec(source);
    if (!match) throw new Error('Use a plain amount with at most two decimal places; no symbols, exponents or thousands separators.');
    const magnitude = BigInt(match[2]) * 100n + BigInt((match[3] || '').padEnd(2, '0'));
    if (magnitude > MAX_ROW_MINOR) throw new Error('Transaction amount is out of range.');
    return Number(match[1] === '-' ? -magnitude : magnitude);
  }
  function addMinor(a, b) {
    const result = a + b;
    if (!Number.isSafeInteger(result)) throw new Error('Aggregate amount is outside exact integer limits.');
    return result;
  }
  function isoDate(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    const year = Number(value.slice(0, 4)), month = Number(value.slice(5, 7)), day = Number(value.slice(8, 10));
    if (year < 1 || month < 1 || month > 12) return false;
    const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
    return day >= 1 && day <= [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1];
  }

  // Adapted upstream scanner: reject non-delimiters after closing quotes, preserve
  // quoted multiline fields and escaped quotes, and support CR, LF and CRLF.
  function scanCsv(csv) {
    if (typeof csv !== 'string') throw new Error('CSV must be text.');
    if (new TextEncoder().encode(csv).byteLength > MAX_CSV_BYTES) throw new Error('Import at most 500 KB of transaction CSV.');
    if (/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(csv)) throw new Error('Binary or control characters are not accepted in CSV.');
    if (csv.charCodeAt(0) === 0xfeff) csv = csv.slice(1);
    const rows = [];
    let row = [], cell = '', quoted = false;
    for (let i = 0; i <= csv.length; i++) {
      const c = csv[i];
      if (c === '"') {
        if (quoted && csv[i + 1] === '"') {cell += '"'; i++;}
        else if (!quoted && cell.length) throw new Error('Invalid quoted CSV field.');
        else {
          quoted = !quoted;
          if (!quoted) {
            const next = csv[i + 1];
            if (next !== undefined && next !== ',' && next !== '\n' && next !== '\r') throw new Error('Invalid quoted CSV field.');
          }
        }
      } else if (!quoted && (c === ',' || c === '\r' || c === '\n' || c === undefined)) {
        row.push(cell); cell = '';
        if (c !== ',') {
          if (row.some(v => v.trim())) rows.push(row);
          if (rows.length > MAX_TRANSACTIONS + 1) throw new Error('Import between 1 and 5,000 transactions.');
          row = [];
          if (c === '\r' && csv[i + 1] === '\n') i++;
        }
      } else if (c !== undefined) cell += c;
    }
    if (quoted) throw new Error('CSV has an unclosed quoted field.');
    return rows;
  }

  function analyzeSpending(csv, options) {
    checkOptions(options);
    const rows = scanCsv(csv);
    const header = rows.shift()?.map(v => v.trim().toLowerCase());
    if (!header || !required.every(v => header.includes(v))) throw new Error('CSV needs date,description,amount,category columns.');
    if ([...required, 'currency'].some(name => header.includes(name) && header.indexOf(name) !== header.lastIndexOf(name))) {
      throw new Error('CSV has a duplicate required or currency column.');
    }
    if (!rows.length || rows.length > MAX_TRANSACTIONS) throw new Error('Import between 1 and 5,000 transactions.');
    const currency = options.currency;
    const grouped = new Map(), seen = new Set();
    let spending = 0, income = 0, duplicates = 0, from = null, to = null;
    const transactions = rows.map((row, index) => {
      if (row.length !== header.length) throw new Error(`Row ${index + 2} has the wrong number of columns.`);
      const get = name => row[header.indexOf(name)]?.trim() ?? '';
      const date = get('date');
      if (!isoDate(date)) throw new Error(`Row ${index + 2} needs a valid Gregorian ISO date (YYYY-MM-DD).`);
      if (header.includes('currency') && get('currency') !== currency) throw new Error(`Row ${index + 2} currency does not match the chosen source currency. No mixing or FX conversion.`);
      const amount = parseAmountMinor(get('amount'));
      const description = get('description'), category = get('category') || 'Uncategorized';
      const fingerprint = JSON.stringify([date, description, amount, category, currency]);
      if (seen.has(fingerprint)) duplicates++;
      else seen.add(fingerprint);
      if (amount > 0) {
        spending = addMinor(spending, amount);
        grouped.set(category, addMinor(grouped.get(category) || 0, amount));
      } else if (amount < 0) income = addMinor(income, -amount);
      if (from === null || date < from) from = date;
      if (to === null || date > to) to = date;
      return {id: `row-${index + 2}`, date, description, category, amount_minor: amount};
    });
    return {
      schema: 'openbot.finance-preview/1',
      scope: 'unreconciled_user_supplied_csv_preview',
      currency, unit: 'integer_minor_units_1_100', amount_convention: CONVENTION,
      ledger_writes: false, bank_connected: false, earnings_verified: false, permission_to_spend: false,
      income_minor: income, spending_minor: spending, net_import_minor: addMinor(income, -spending),
      count: transactions.length, duplicate_rows: duplicates, period: {from, to},
      categories: [...grouped].map(([name, amount_minor]) => ({name, amount_minor})).sort((a, b) => b.amount_minor - a.amount_minor || a.name.localeCompare(b.name)),
      transactions,
      limitations: [
        'User-supplied, unreconciled data; amounts and classifications may be wrong or incomplete.',
        'Positive amounts are treated as expenses; negative amounts as income, including refunds or transfers the source may misclassify.',
        'Exact duplicate rows are counted, disclosed and retained; not automatically removed.',
        'Net imported is income minus expenses in this file, not a bank balance, profit, settled earnings or permission to spend.',
        'No currency inference, exchange rates, external account access, model call or ledger write.'
      ]
    };
  }
  function formatMinor(value, currency) {
    checkCurrency(currency);
    if (!Number.isSafeInteger(value)) throw new Error('Only exact safe integer minor units can be formatted.');
    const digits = String(Math.abs(value)).padStart(3, '0');
    const whole = digits.slice(0, -2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return `${currency} ${value < 0 ? '-' : ''}${whole}.${digits.slice(-2)}`;
  }
  return Object.freeze({analyzeSpending, parseAmountMinor, formatMinor, MAX_CSV_BYTES, MAX_TRANSACTIONS, CURRENCIES, CONVENTION});
});
