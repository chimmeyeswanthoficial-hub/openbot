// Uses an existing Playwright installation; never installs a package or browser.
'use strict';
const {chromium,webkit}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const engine=process.env.TEST_ENGINE||'chromium';
if(!['chromium','webkit'].includes(engine))throw new Error('Unsupported browser engine');
const base=process.env.PREVIEW_URL||'http://127.0.0.1:4184';
const output=path.resolve(process.env.EVIDENCE_DIR||path.join(__dirname,'../.cache/finance-ui'));
fs.mkdirSync(output,{recursive:true});
const results=[],requests=[],errors=[];
const marker='LOCAL_ONLY_FINANCE_SYNTHETIC_SENTINEL_71';
const text='date,description,amount,category\n2026-10-02,'+marker+',1.13,Food\n2026-10-01,Fictional income,-100.00,Income\n2026-10-02,'+marker+',1.13,Food';
let browser,context,page;
async function check(name,fn){const start=Date.now();try{await fn();results.push({name,status:'passed',duration_ms:Date.now()-start});console.log('PASS',name);}catch(error){results.push({name,status:'failed',error:error.stack,duration_ms:Date.now()-start});throw error;}}
async function nav(route){
 if(page.viewportSize().width<=760&&await page.locator('#mobile-back').isVisible())await page.locator('#mobile-back').click();
 if(route==='trust')await page.locator(page.viewportSize().width<=760?'.profile-button':'.account-button').click();
 else if(route==='chat')await page.locator(page.viewportSize().width<=760?'#mobile-favorites [data-companion="chief"]':'#contact-list [data-companion="chief"]').click();
 else{await page.locator('.contact-footer [data-view="plugins"]').click();if(route!=='plugins')await page.locator('#main [data-view="'+route+'"]').first().click();}
}
async function source(csv=text,currency='INR'){await page.locator('#finance-csv').fill(csv);await page.locator('#finance-currency').selectOption(currency);await page.locator('#finance-confirm').check();}
async function calculate(){await page.locator('#finance-analyze').click();await page.locator('.finance-metrics').waitFor();}
async function localFile(name,buffer){await page.locator('#finance-file').setInputFiles({name,mimeType:'text/csv',buffer:Buffer.isBuffer(buffer)?buffer:Buffer.from(buffer)});await page.waitForFunction(()=>!document.querySelector('#finance-analyze')?.disabled);}
(async()=>{
 browser=await({chromium,webkit})[engine].launch({headless:true,args:engine==='chromium'?['--no-sandbox']:[]});
 context=await browser.newContext({viewport:{width:1580,height:1060},acceptDownloads:true});page=await context.newPage();
 context.on('page',p=>{p.on('pageerror',e=>errors.push(e.message));});page.on('pageerror',e=>errors.push(e.message));
 context.on('request',r=>requests.push({url:r.url(),method:r.method(),body:r.postData()}));
 await check('the real integrated finance route states its no-account/no-ledger boundary',async()=>{
  await page.goto(base,{waitUntil:'networkidle'});await nav('finance');assert.equal(await page.locator('#main').getAttribute('aria-label'),'Spending preview');assert.match(await page.locator('.finance-boundary').innerText(),/no bank connection/i);assert.match(await page.locator('.finance-empty').innerText(),/Nothing will be sent/);assert.equal(await page.locator('#finance-currency').inputValue(),'');assert(!(await page.locator('#finance-confirm').isChecked()));
 });
 await check('fictional example does not calculate or imply real money without confirmation',async()=>{
  await page.locator('#finance-sample').click();assert.match(await page.locator('#finance-hint').innerText(),/Fictional/);assert.equal(await page.locator('.finance-metrics').count(),0);await page.locator('#finance-analyze').click();assert.match(await page.locator('#finance-error').innerText(),/Confirm/);assert.equal(await page.locator('.finance-metrics').count(),0);
 });
 await check('currency alone is insufficient and denied input is retained',async()=>{
  await page.locator('#finance-currency').selectOption('INR');const before=await page.locator('#finance-csv').inputValue();await page.locator('#finance-analyze').click();assert.match(await page.locator('#finance-error').innerText(),/Confirm/);assert.equal(await page.locator('#finance-csv').inputValue(),before);
 });
 await check('confirmed synthetic CSV is actually parsed into exact, unverified totals',async()=>{
  await source();await calculate();assert.match(await page.locator('#finance-hint').innerText(),/Preview calculated locally/);assert.match(await page.locator('.finance-metrics').innerText(),/INR 2\.26/);assert.match(await page.locator('.finance-metrics').innerText(),/INR 100\.00/);assert.match(await page.locator('.finance-metrics').innerText(),/INR 97\.74/);assert.match(await page.locator('#finance-duplicates').innerText(),/1 exact duplicate/);assert.match(await page.locator('.finance-warning').first().innerText(),/not a bank balance/);
 });
 await check('preview JSON contains integer data and explicit false authority flags',async()=>{
  const pending=page.waitForEvent('download');await page.locator('#finance-download').click();const file=await pending;assert.equal(file.suggestedFilename(),'OpenBot-unreconciled-spending-preview.json');const r=JSON.parse(fs.readFileSync(await file.path(),'utf8'));
  assert.equal(r.schema,'openbot.finance-preview/1');assert.equal(r.scope,'unreconciled_user_supplied_csv_preview');assert.equal(r.spending_minor,226);assert.equal(r.income_minor,10000);assert.equal(r.net_import_minor,9774);assert.equal(r.transactions[0].amount_minor,113);assert.equal(r.transactions[0].description,marker);assert.equal(r.transactions.length,3);assert.equal(r.duplicate_rows,1);for(const field of ['ledger_writes','bank_connected','earnings_verified','permission_to_spend'])assert.equal(r[field],false);assert.equal(r.saved,undefined);assert.equal(r.bank_balance,undefined);
 });
 await check('editing CSV invalidates results, download and sign confirmation immediately',async()=>{
  await page.locator('#finance-csv').fill(text+'\n2026-10-03,Another,0.29,Food');assert.equal(await page.locator('.finance-metrics').count(),0);assert.equal(await page.locator('#finance-download').count(),0);assert(!(await page.locator('#finance-confirm').isChecked()));await page.locator('#finance-analyze').click();assert.match(await page.locator('#finance-error').innerText(),/Confirm/);
 });
 await check('currency or confirmation edits also invalidate already calculated output',async()=>{
  await source();await calculate();await page.locator('#finance-currency').selectOption('USD');assert.equal(await page.locator('.finance-metrics').count(),0);assert(!(await page.locator('#finance-confirm').isChecked()));await page.locator('#finance-confirm').check();await calculate();await page.locator('#finance-confirm').uncheck();assert.equal(await page.locator('#finance-download').count(),0);
 });
 await check('mixed-currency files fail closed rather than converting or ignoring a row',async()=>{
  await source('date,description,amount,category,currency\n2026-10-01,Fictional,1.00,Food,USD');await page.locator('#finance-analyze').click();assert.match(await page.locator('#finance-error').innerText(),/currency does not match/);assert.equal(await page.locator('.finance-metrics').count(),0);
 });
 await check('malformed quotes, dates, money and duplicate required headers return no partial report',async()=>{
  for(const csv of ['date,description,amount,category\n2026-10-01,"bad"tail,1.00,Food','date,description,amount,category\n2026-02-29,Invalid date,1.00,Food','date,description,amount,category\n2026-10-01,Bad amount,1e2,Food','date,description,amount,category, Amount \n2026-10-01,Duplicate header,1.00,Food,100']){
   await source(csv);await page.locator('#finance-analyze').click();assert((await page.locator('#finance-error').innerText()).length>0);assert.equal(await page.locator('.finance-metrics').count(),0);assert.equal(await page.locator('#finance-download').count(),0);
  }
 });
 await check('untrusted markup, URL and formula descriptions render only as text',async()=>{
  await source('date,description,amount,category\n2026-10-01,<img src=x onerror=alert(1)>,1.13,<svg>\n2026-10-02,"=HYPERLINK("""")",0.29,https://example.invalid');await calculate();assert.match(await page.locator('.finance-table').innerText(),/<img src=x onerror=alert\(1\)>/);assert.match(await page.locator('.finance-table').innerText(),/=HYPERLINK\(""\)/);assert.equal(await page.locator('#finance-results img,#finance-results iframe,#finance-results a,#finance-results svg:not(:has(use))').count(),0);
 });
 await check('a local UTF-8 CSV file is read but never automatically analysed or sent',async()=>{
  await localFile('synthetic.CSV',text);await page.locator('#finance-hint').filter({hasText:'File read locally'}).waitFor();assert.equal(await page.locator('#finance-csv').inputValue(),text);assert.equal(await page.locator('.finance-metrics').count(),0);assert(!(await page.locator('#finance-confirm').isChecked()));await page.locator('#finance-currency').selectOption('INR');await page.locator('#finance-confirm').check();await calculate();
 });
 await check('wrong extension and oversized files retain prior input and remove stale output',async()=>{
  for(const [name,data]of [['not-csv.txt',text],['oversized.csv',Buffer.alloc(500001,120)]]){
   const before=await page.locator('#finance-csv').inputValue();await localFile(name,data);assert.match(await page.locator('#finance-error').innerText(),/500,000 UTF-8 bytes/);assert.equal(await page.locator('#finance-csv').inputValue(),before);assert.equal(await page.locator('#finance-download').count(),0);
  }
 });
 await check('invalid UTF-8 is refused, not silently replacement-decoded',async()=>{
  const before=await page.locator('#finance-csv').inputValue();await localFile('invalid.csv',Buffer.from([0xc3,0x28]));await page.locator('#finance-error').filter({hasText:'valid UTF-8'}).waitFor();assert.equal(await page.locator('#finance-csv').inputValue(),before);assert.equal(await page.locator('.finance-metrics').count(),0);
 });
 await check('clearing imported data wins against an in-flight file read',async()=>{
  await page.evaluate(()=>{window.originalLocalArrayBuffer=File.prototype.arrayBuffer;File.prototype.arrayBuffer=function(){return new Promise(resolve=>{window.finishLocalRead=()=>resolve(new TextEncoder().encode('date,description,amount,category\n2026-10-01,Must not return,1.00,Food').buffer);});};});
  await page.locator('#finance-file').setInputFiles({name:'delayed.csv',mimeType:'text/csv',buffer:Buffer.from(text)});await page.waitForFunction(()=>typeof window.finishLocalRead==='function');assert(await page.locator('#finance-analyze').isDisabled());await page.locator('#finance-clear').click();await page.evaluate(()=>{File.prototype.arrayBuffer=window.originalLocalArrayBuffer;window.finishLocalRead();});await page.waitForTimeout(50);assert.equal(await page.locator('#finance-csv').inputValue(),'');assert.equal(await page.locator('#finance-download').count(),0);
 });
 await check('editing while a file is reading also wins over its late completion',async()=>{
  await page.evaluate(()=>{window.originalLocalArrayBuffer=File.prototype.arrayBuffer;File.prototype.arrayBuffer=function(){return new Promise(resolve=>{window.finishLocalRead=()=>resolve(new TextEncoder().encode('date,description,amount,category\n2026-10-01,Discarded,1.00,Food').buffer);});};window.finishLocalRead=null;});
  await page.locator('#finance-file').setInputFiles({name:'delayed-edit.csv',mimeType:'text/csv',buffer:Buffer.from(text)});await page.waitForFunction(()=>typeof window.finishLocalRead==='function');await page.locator('#finance-csv').fill(text);await page.evaluate(()=>{File.prototype.arrayBuffer=window.originalLocalArrayBuffer;window.finishLocalRead();});await page.waitForTimeout(50);assert.equal(await page.locator('#finance-csv').inputValue(),text);assert(!(await page.locator('#finance-analyze').isDisabled()));
 });
 await check('normal navigation retains tab-only data but optional draft saving excludes it',async()=>{
  await source();await calculate();await nav('trust');await page.locator('#remember-drafts').check();await nav('finance');assert.equal(await page.locator('#finance-csv').inputValue(),text);assert.equal(await page.locator('.finance-metrics').count(),1);
  const stored=await page.evaluate(()=>({local:Object.entries(localStorage),session:Object.entries(sessionStorage)}));assert(!JSON.stringify(stored).includes(marker));assert(!JSON.stringify(stored).includes('finance-csv'));assert.equal(stored.session.length,0);
 });
 await check('reloading clears all imported financial data even with remember-drafts enabled',async()=>{
  await page.reload({waitUntil:'networkidle'});await page.locator('#finance-csv').waitFor();assert.equal(await page.locator('#finance-csv').inputValue(),'');assert.equal(await page.locator('#finance-currency').inputValue(),'');assert(!(await page.locator('#finance-confirm').isChecked()));assert.equal(await page.locator('.finance-metrics').count(),0);await nav('trust');assert(await page.locator('#remember-drafts').isChecked());
 });
 await check('the general clear-drafts action also clears the in-memory finance workspace',async()=>{
  await nav('finance');await source();await calculate();await nav('trust');await page.locator('#clear-drafts').click();await page.locator('#confirm-clear').click();await nav('finance');assert.equal(await page.locator('#finance-csv').inputValue(),'');assert.equal(await page.locator('.finance-metrics').count(),0);assert.equal(await page.evaluate(()=>localStorage.getItem('openbot.workspace.local-drafts.v2')),null);
 });
 await check('all eight views fit desktop; the actual CSV preview fits a 375px viewport',async()=>{
  await source();await calculate();await page.locator('#toast').waitFor({state:'hidden',timeout:8000});await page.evaluate(()=>{document.activeElement?.blur();window.scrollTo(0,0);});await page.screenshot({path:path.join(output,engine+'-finance-desktop.png'),fullPage:true,animations:'disabled'});
  for(const route of ['chat','plugins','social','connection','work','library','finance','trust']){await nav(route);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),route);}
  await page.setViewportSize({width:375,height:812});await nav('finance');assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.equal(await page.locator('#finance-confirm').getAttribute('type'),'checkbox');await page.evaluate(()=>{document.activeElement?.blur();window.scrollTo(0,0);});await page.screenshot({path:path.join(output,engine+'-finance-mobile.png'),fullPage:true,animations:'disabled'});
 });
 await check('opaque offline iframe can calculate locally with no server, storage or forms grant',async()=>{
  const local=await context.newPage();await local.goto(base);await local.setContent('<iframe title="Offline spending preview" sandbox="allow-scripts" style="width:100%;height:950px;border:0"></iframe>');await local.locator('iframe').evaluate((el,html)=>{el.srcdoc=html;},fs.readFileSync(path.join(__dirname,'../web/index.html'),'utf8'));
  const frame=local.frameLocator('iframe');await frame.locator('.contact-footer [data-view="plugins"]').click();await frame.locator('#main [data-view="finance"]').click();await frame.locator('#finance-csv').fill(text);await frame.locator('#finance-currency').selectOption('INR');await frame.locator('#finance-confirm').check();await frame.locator('#finance-analyze').click();await frame.locator('.finance-metrics').waitFor();assert.match(await frame.locator('.finance-metrics').innerText(),/INR 2\.26/);await local.close();
 });
 await check('no transaction data, upload, telemetry, model, bank or ledger request occurred',async()=>{
  assert.deepEqual(requests.filter(r=>new URL(r.url).origin!==new URL(base).origin&&!r.url.startsWith('blob:')),[]);assert(!requests.some(r=>r.method!=='GET'));assert(!JSON.stringify(requests).includes(marker));assert(!requests.some(r=>/\/(finance|bank|ledger|telemetry|upload|publish)(?:\/|$)/.test(new URL(r.url).pathname)));assert.deepEqual(errors,[]);
 });
 await context.close();
})().catch(error=>{console.error(error.stack);process.exitCode=1;}).finally(async()=>{
 if(browser)await browser.close();fs.writeFileSync(path.join(output,'finance-ui-'+engine+'.json'),JSON.stringify({schema:'openbot.observed-finance-browser-tests/1',engine,base,results,requests,page_errors:errors,scope:'Synthetic, browser-only CSV preview. No bank, accounting, external provider, VM or public-release acceptance.'},null,2)+'\n');console.log('Observed',results.filter(r=>r.status==='passed').length,'passed;',results.filter(r=>r.status==='failed').length,'failed');
});
