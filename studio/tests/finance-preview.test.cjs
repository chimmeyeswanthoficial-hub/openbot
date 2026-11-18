// Tests for the actual adopted OpenMuse-derived module, not a mock bank or ledger.
'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {analyzeSpending,parseAmountMinor,formatMinor,MAX_CSV_BYTES}=require('../web/finance-preview.js');
const opts=(changes={})=>({currency:'INR',amountConvention:'positive_expenses_negative_income',singleCurrencyConfirmed:true,...changes});
const csv=(rows,header='date,description,amount,category')=>header+'\n'+rows.join('\n');

test('actual adoption produces an explicitly unreconciled read-only source-currency report',()=>{
 const r=analyzeSpending(csv(['2026-09-01,Coffee,10.10,Food','2026-09-02,Pay,-100.00,Income']),opts());
 assert.equal(r.count,2);assert.equal(r.spending_minor,1010);assert.equal(r.income_minor,10000);assert.equal(r.net_import_minor,8990);
 assert.equal(r.currency,'INR');assert.equal(r.scope,'unreconciled_user_supplied_csv_preview');assert.equal(r.ledger_writes,false);assert.equal(r.bank_connected,false);assert.equal(r.earnings_verified,false);assert.equal(r.permission_to_spend,false);
 assert.equal(Object.hasOwn(r,'profit'),false);assert.equal(Object.hasOwn(r,'bank_balance'),false);assert.equal(Object.hasOwn(r,'saved'),false);
});
test('currency and positive-expense sign convention require explicit correctly typed confirmation',()=>{
 for(const o of [undefined,{},opts({currency:''}),opts({currency:'JPY'}),opts({currency:'usd'}),opts({singleCurrencyConfirmed:false}),opts({singleCurrencyConfirmed:1}),opts({amountConvention:'expenses_negative'}),opts({ledger_writes:true})])assert.throws(()=>analyzeSpending(csv(['2026-09-01,Coffee,10,Food']),o));
 for(const currency of ['INR','USD','EUR','GBP'])assert.equal(analyzeSpending(csv(['2026-09-01,Coffee,10,Food']),opts({currency})).currency,currency);
});
test('money parsing is integer-only and exact at every supported decimal boundary',()=>{
 for(const [source,minor]of[['1.13',113],['0.29',29],['-10.10',-1010],['+10.1',1010],['001.01',101],['-0.00',0],['10000000000.00',1000000000000],['-10000000000',-1000000000000]])assert.equal(parseAmountMinor(source),minor,source);
 for(const source of ['1e2','1.001','NaN','Infinity','1,000.00','₹10','(10.00)','--1','1.',' .1','1.00 ','10000000000.01','1'.repeat(500)])assert.throws(()=>parseAmountMinor(source),source);
});
test('aggregate arithmetic stays exact and safe at all 5000 maximum-value rows',()=>{
 const rows=Array.from({length:5000},()=> '2026-09-01,Repeated high value,10000000000.00,Stress');
 const r=analyzeSpending(csv(rows),opts());assert.equal(r.spending_minor,5000000000000000);assert.equal(r.categories[0].amount_minor,5000000000000000);assert(Number.isSafeInteger(r.net_import_minor));
 assert.equal(formatMinor(r.spending_minor,'INR'),'INR 50,000,000,000,000.00');assert.equal(r.duplicate_rows,4999);assert.equal(r.count,5000);
});
test('formatting uses integer digits, never a floating major-unit ledger value',()=>{
 for(const [minor,text]of[[0,'USD 0.00'],[1,'USD 0.01'],[-101,'USD -1.01'],[9007199254740991,'USD 90,071,992,547,409.91']])assert.equal(formatMinor(minor,'USD'),text);
 for(const minor of [1.2,NaN,Infinity,9007199254740992,'1'])assert.throws(()=>formatMinor(minor,'USD'));
 assert.throws(()=>formatMinor(100,'XXX'));
});
test('upstream quote-boundary regression vectors refuse trailing characters',()=>{
 for(const amount of ['"10"0','""10','"10".00','"10" '])assert.throws(()=>analyzeSpending(csv([`2026-09-01,Coffee,${amount},Food`]),opts()),/quoted CSV/);
 assert.throws(()=>analyzeSpending(csv(['2026-09-01,"Coffee"shop,10,Food']),opts()),/quoted CSV/);
});
test('upstream valid escaped quotes, commas and embedded newlines are preserved',()=>{
 for(const ending of ['', '\n','\r\n','\r']){
  const text='"date","description","amount","category"\r\n"2026-09-01","Coffee, ""local""\nshop","10.10","Food"\r\n'+`"2026-09-02","","20.20",""${ending}`;
  const r=analyzeSpending(text,opts());assert.equal(r.count,2);assert.equal(r.spending_minor,3030);assert.equal(r.transactions[0].description,'Coffee, "local"\nshop');assert.equal(r.transactions[1].category,'Uncategorized');
 }
});
test('upstream BOM and CR/LF/CRLF vectors retain field boundaries',()=>{
 for(const newline of ['\r','\n','\r\n']){
  const text='\uFEFF'+['"date","description","amount","category"','2026-09-01,"Coffee, local",10.10,Food','2026-09-02,Salary,-100.00,Income',''].join(newline);
  const r=analyzeSpending(text,opts());assert.equal(r.count,2);assert.equal(r.spending_minor,1010);assert.equal(r.income_minor,10000);
 }
 const r=analyzeSpending('date,description,amount,category\r2026-09-01,"Coffee\rshop\r\nreceipt",10,Food\r',opts());assert.equal(r.transactions[0].description,'Coffee\rshop\r\nreceipt');
});
test('unclosed or incorrectly positioned quotes never produce a partial report',()=>{
 for(const text of ['date,description,amount,category\n2026-09-01,"Coffee,10,Food','date,description,amount,category\n2026-09-01,Cof"fee,10,Food','date,description,amount,category\n2026-09-01,"Coffee" ,10,Food'])assert.throws(()=>analyzeSpending(text,opts()),/CSV/);
});
test('upstream required headers are normalized and duplicates cannot discard amounts',()=>{
 for(const name of ['date','description','amount','category',' Amount '])assert.throws(()=>analyzeSpending(csv(['2026-09-01,Purchase,10,Food,1000'],'date,description,amount,category,'+name),opts()),/duplicate/);
 assert.throws(()=>analyzeSpending('date,description,category\n2026-09-01,Coffee,Food',opts()),/columns/);
});
test('upstream reordered and irrelevant extra columns remain compatible',()=>{
 const r=analyzeSpending(csv(['First,Food,10,Purchase,2026-09-01,Second'],'note,category,amount,description,date,note'),opts());assert.equal(r.spending_minor,1000);assert.equal(r.transactions[0].description,'Purchase');
});
test('wrong row widths, empty inputs and more than 5000 transactions are refused',()=>{
 for(const text of ['', 'date,description,amount,category',csv(['2026-09-01,Coffee,10']),csv(['2026-09-01,Coffee,10,Food,extra']),csv(Array.from({length:5001},()=> '2026-09-01,X,1,Food'))])assert.throws(()=>analyzeSpending(text,opts()));
});
test('real Gregorian date checks do not normalize invalid dates into another day',()=>{
 for(const date of ['2026-02-29','2026-04-31','2026-13-01','2026-00-01','2026-09-00','26-09-01','2026-9-1','0000-01-01','2026-09-01T00:00:00Z'])assert.throws(()=>analyzeSpending(csv([`${date},Coffee,10,Food`]),opts()),/ISO date/);
 for(const date of ['2024-02-29','2000-02-29','1900-02-28','2026-12-31'])assert.equal(analyzeSpending(csv([`${date},Coffee,10,Food`]),opts()).count,1);
});
test('optional currency column must match chosen currency, with no FX or mixing',()=>{
 assert.equal(analyzeSpending(csv(['2026-09-01,Coffee,10,Food,INR'],'date,description,amount,category,currency'),opts()).count,1);
 for(const value of ['USD','', 'INR,INR']){
  const header=value.includes(',')?'date,description,amount,category,currency,Currency':'date,description,amount,category,currency';
  assert.throws(()=>analyzeSpending(csv(['2026-09-01,Coffee,10,Food,'+value],header),opts()),/currency|duplicate/i);
 }
});
test('exact duplicate rows are disclosed and retained, never silently removed',()=>{
 const text=csv(['2026-09-02,Repeat,10,Food','2026-09-01,Salary,-100,Income','2026-09-02,Repeat,10,Food']);
 const r=analyzeSpending(text,opts());assert.equal(r.duplicate_rows,1);assert.equal(r.count,3);assert.equal(r.spending_minor,2000);assert.deepEqual(r.period,{from:'2026-09-01',to:'2026-09-02'});
});
test('byte limit is UTF-8, including upstream Unicode and exact-boundary vectors',()=>{
 const header='date,description,amount,category\n2026-09-01,';const suffix=',10,Food';
 assert.throws(()=>analyzeSpending(header+'中'.repeat(167000)+suffix,opts()),/500 KB/);
 for(const character of ['x','中','😀']){
  const available=MAX_CSV_BYTES-Buffer.byteLength(header+suffix);const width=Buffer.byteLength(character);const description=character.repeat(Math.floor(available/width))+'x'.repeat(available%width);const text=header+description+suffix;
  assert.equal(Buffer.byteLength(text),MAX_CSV_BYTES);assert.equal(analyzeSpending(text,opts()).count,1);assert.throws(()=>analyzeSpending(text+'\n',opts()),/500 KB/);
 }
});
test('control/binary text and non-text input are refused rather than coerced',()=>{
 for(const text of [null,42,{},csv(['2026-09-01,Bin\u0000ary,10,Food']),csv(['2026-09-01,Esc\u001b,10,Food'])])assert.throws(()=>analyzeSpending(text,opts()));
});
test('HTML, URLs and spreadsheet formula text remain literal user data',()=>{
 const r=analyzeSpending(csv(['2026-09-01,<img src=x onerror=alert(1)>,10,<svg>','2026-09-02,"=HYPERLINK("""")",20,https://example.invalid']),opts());
 assert.equal(r.transactions[0].description,'<img src=x onerror=alert(1)>');assert.equal(r.transactions[0].category,'<svg>');assert.equal(r.bank_connected,false);
});
test('adopted module contains no network, storage, shell, model or DOM rendering path',()=>{
 const source=fs.readFileSync(path.join(__dirname,'../web/finance-preview.js'),'utf8');
 assert(!/\bfetch\s*\(|XMLHttpRequest|localStorage|sessionStorage|child_process|\.innerHTML\s*=|document\.cookie/.test(source));
 assert.match(source,/a4944f4c471d3dc93b8bfc060b5da309b5216ab2/);assert.match(source,/SPDX-License-Identifier: MIT/);
});
