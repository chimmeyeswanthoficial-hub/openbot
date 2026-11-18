// Real local UI regression. Requires separately installed Playwright, no installs.
'use strict';
const {chromium,webkit}=require('playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const engine=process.env.TEST_ENGINE||'chromium';
if(!['chromium','webkit'].includes(engine))throw Error('Unsupported engine');
const base=process.env.PREVIEW_URL||'http://127.0.0.1:4184';
const evidence=path.resolve(process.env.EVIDENCE_DIR||path.join(__dirname,'../.cache/ui-evidence'));
fs.mkdirSync(evidence,{recursive:true});
const results=[],requests=[],errors=[],KEY='openbot.workspace.local-drafts.v2',LEGACY='openbot.studio.local-drafts.v1';
const names={chat:'Conversation',plugins:'Plugins & tools',social:'Social desk',finance:'Spending preview',library:'Brief library',connection:'Server & session',work:'Verified work',trust:'Workspace settings'};
const canonical=v=>v===null||typeof v!=='object'?JSON.stringify(v):Array.isArray(v)?'['+v.map(canonical).join(',')+']':'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';
const readDownload=async d=>fs.readFileSync(await d.path(),'utf8');
let browser;
async function test(name,fn){const start=Date.now();try{await fn();results.push({name,status:'passed',duration_ms:Date.now()-start});console.log('PASS',name);}catch(error){results.push({name,status:'failed',error:error.stack});throw error;}}
(async()=>{
 browser=await({chromium,webkit})[engine].launch({headless:true,args:engine==='chromium'?['--no-sandbox']:[]});
 const context=await browser.newContext({viewport:{width:1512,height:982},acceptDownloads:true,reducedMotion:'reduce'}),page=await context.newPage();
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push({url:r.url(),method:r.method(),kind:r.resourceType()}));
 const nav=async view=>{
  if(page.viewportSize().width<=760&&await page.locator('#mobile-back').isVisible())await page.locator('#mobile-back').click();
  if(view==='chat'){
   const target=page.viewportSize().width<=760?'#mobile-favorites [data-companion="chief"]':'#contact-list [data-companion="chief"]';
   if(await page.locator('#contact-search').isVisible())await page.locator('#contact-search').fill('');await page.locator(target).click();
  }else if(view==='trust')await page.locator(page.viewportSize().width<=760?'.profile-button':'.account-button').click();
  else if(view==='connection')await page.locator('.contact-footer [data-view="connection"]').click();
  else{await page.locator('.contact-footer [data-view="plugins"]').click();if(view!=='plugins')await page.locator(`#main [data-view="${view}"]`).first().click();}
  await page.locator(`#main[aria-label="${names[view]}"]`).waitFor();
 };
 const socialResponse=()=>page.waitForResponse(r=>r.url().endsWith('/api/social-plan')&&r.request().method()==='POST');
 let firstPlan;
 await test('initial original light UI has ten blueprints, no live model, PC or authority',async()=>{
  const r=await page.goto(base,{waitUntil:'networkidle'});assert.equal(r.status(),200);assert.match(await page.locator('h1').innerText(),/A little clarity/);
  assert.equal(await page.locator('#contact-list [data-companion]').count(),10);assert.match(await page.locator('.composer-note').innerText(),/not live AI chat/);
  assert.match(await page.locator('.computer-desktop').innerText(),/No computer connected/);assert.equal(await page.evaluate(()=>localStorage.getItem('openbot.workspace.local-drafts.v2')),null);
  assert.equal(await page.evaluate(()=>window.OpenBotWorkspace.connection.enabled),false);assert.equal(await page.locator('meta[name="color-scheme"]').getAttribute('content'),'light');
 });
 await test('desktop three columns are distinct, bounded and capture the reference layout',async()=>{
  const boxes=await Promise.all(['.contact-panel','.conversation-panel','.details-panel'].map(s=>page.locator(s).boundingBox()));assert(boxes.every(b=>b&&b.width>200));assert(boxes[0].x<boxes[1].x&&boxes[1].x<boxes[2].x);
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(evidence,engine+'-desktop.png'),animations:'disabled'});
 });
 await test('companion search filters display profiles, not accounts',async()=>{
  await page.locator('#contact-search').fill('expense');assert.equal(await page.locator('#contact-list .contact-row').count(),1);assert.match(await page.locator('#contact-list').innerText(),/Expense Manager/);await page.locator('#contact-search').fill('no-such-name');assert.match(await page.locator('#contact-list').innerText(),/No matching/);await page.locator('#contact-search').fill('');
 });
 await test('computer details close and reopen correctly on desktop',async()=>{
  await page.locator('#close-details').click();assert(!(await page.locator('#details-panel').isVisible()));assert.equal(await page.locator('#show-computer').getAttribute('aria-expanded'),'false');await page.locator('#show-computer').click();assert(await page.locator('#details-panel').isVisible());
 });
 await test('example conversation is conspicuously fictional and cannot send messages',async()=>{
  await page.locator('#view-example').click();assert.match(await page.locator('.example-label').innerText(),/FICTIONAL DESIGN EXAMPLE/);assert.equal(await page.locator('.message.system').count(),2);await page.screenshot({path:path.join(evidence,engine+'-example-desktop.png'),animations:'disabled'});await page.locator('#leave-example').click();
 });
 await test('unsent text survives navigation without upload or silent saving',async()=>{
  await page.locator('#brief-input').fill('Unsent draft stays here');await nav('library');await nav('chat');assert.equal(await page.locator('#brief-input').inputValue(),'Unsent draft stays here');assert.equal(await page.evaluate(k=>localStorage.getItem(k),KEY),null);
 });
 await test('local brief and deterministic intake are XSS-safe, not invented model output',async()=>{
  await page.locator('#brief-input').fill('<img src=x onerror="window.__bad=1"> Research carefully');await page.locator('#save-brief').click();assert.match(await page.locator('.message.user').innerText(),/<img src=x/);assert.match(await page.locator('.message.system').innerText(),/NOT AN AI RESPONSE/);assert.equal(await page.locator('#main img').count(),0);assert.equal(await page.evaluate(()=>window.__bad),undefined);
 });
 await test('Markdown export is explicitly a human brief, not execution approval',async()=>{
  await nav('library');const pending=page.waitForEvent('download');await page.locator('[data-download-brief]').click();const text=await readDownload(await pending);assert.match(text,/# Local work brief/);assert.match(text,/Not an AI answer, assigned job or execution grant/);assert.match(text,/<img src=x/);
 });
 await test('requested xAI profile becomes a verified planning blueprint only',async()=>{
  await page.locator('[data-add-companion]').click();await page.locator('#companion-name').fill('Atlas');await page.locator('#companion-provider').selectOption('xai');const response=page.waitForResponse(r=>r.url().endsWith('/api/companion-plan'));await page.locator('#create-companion').click();firstPlan=await(await response).json();await page.locator('#toast').filter({hasText:'Planning hash verified'}).waitFor();
  assert.equal(firstPlan.vm_started,false);assert.equal(firstPlan.model_connected,false);assert.equal(firstPlan.execution_authorized,false);assert.equal(firstPlan.toolchain.length,3);assert.deepEqual(firstPlan.workspace.host_mounts,[]);assert.equal(firstPlan.workspace.network,'deny');assert.match(await page.locator('#thread-heading').innerText(),/Atlas/);
  const pending=page.waitForEvent('download');await page.locator('#download-companion').click();assert.equal(JSON.parse(await readDownload(await pending)).id,firstPlan.id);
 });
 await test('real-PC and all three IDE requirements remain explicit and unprovisioned',async()=>{
  await page.locator('#computer-settings').click();const text=await page.locator('#modal').innerText();for(const s of ['no VM or IDE','Claude Code','Antigravity','T3 Code','Kill/expiry/orphan'])assert(text.includes(s));await page.locator('#modal-close').click();assert.match(await page.locator('.computer-subtitle').innerText(),/0 allocated PCs/);
 });
 await test('Unicode/markup companion names preserve plan hash and cannot inject HTML',async()=>{
  await page.locator('[data-add-companion]').click();await page.locator('#companion-name').fill('Nova <b>🌱</b>');const pending=page.waitForResponse(r=>r.url().endsWith('/api/companion-plan'));await page.locator('#create-companion').click();const p=await(await pending).json();await page.locator('#toast').filter({hasText:'Planning hash verified'}).waitFor();const {sha256,...body}=p;assert.equal(crypto.createHash('sha256').update(canonical(body)).digest('hex'),sha256);assert.equal(await page.locator('#thread-heading strong b').count(),0);assert.match(await page.locator('#thread-heading').innerText(),/<b>🌱<\/b>/);
 });
 await test('routine validates the IANA zone, saves a request, never schedules a job',async()=>{
  await page.locator('[data-routine="0"]').click();await page.locator('#routine-zone').fill('No/SuchZone');await page.locator('#save-routine').click();assert.match(await page.locator('#routine-error').innerText(),/IANA/);await page.locator('#routine-zone').fill('Asia/Kolkata');const pending=page.waitForEvent('download');await page.locator('#save-routine').click();const r=JSON.parse(await readDownload(await pending));assert.equal(r.scheduler_connected,false);assert.equal(r.execution_authorized,false);assert.match(await page.locator('[data-routine="0"]').innerText(),/request only/);
 });
 await test('YouTube local review explicitly previews private visibility and unknown audience',async()=>{
  await nav('social');await page.locator('[data-platform="youtube"]').click();await page.locator('#social-title').fill('Owned field notes');await page.locator('#social-text').fill('Owned release notes for careful human review');await page.locator('#social-media').selectOption('video');await page.locator('#social-asset').fill('a'.repeat(64));await page.locator('#social-rights').fill('owned:fixture-video');const pending=socialResponse();await page.locator('#review-social').click();const p=await(await pending).json();await page.locator('#download-review').waitFor();assert.equal(p.metadata_preview.status.privacyStatus,'private');assert.equal(p.metadata_preview.notifySubscribers,false);assert.equal(p.metadata_preview.status.selfDeclaredMadeForKids,null);assert.equal(p.metadata_preview.status.containsSyntheticMedia,null);assert.equal(p.transport_request,null);assert.equal(p.external_write_enabled,false);assert(await page.locator('#download-review').isDisabled());
 });
 await test('social acknowledgement/export cannot become authenticated publishing approval',async()=>{
  await page.locator('#social-ack').check();const pending=page.waitForEvent('download');await page.locator('#download-review').click();const p=JSON.parse(await readDownload(await pending));assert.equal(p.execution_authorized,false);assert.equal(p.authenticated_approver,null);assert.equal(p.local_review_acknowledgement,true);
 });
 await test('every draft edit invalidates review and acknowledgement',async()=>{
  await page.locator('#social-text').fill('Changed owned release notes');assert.equal(await page.locator('#social-ack').count(),0);assert.match(await page.locator('#social-result').innerText(),/Not reviewed/);
 });
 await test('duplicate content is warned, not rewritten for evasion',async()=>{
  await page.locator('#social-text').fill('Owned release notes for careful human review');const pending=socialResponse();await page.locator('#review-social').click();const p=await(await pending).json();assert.equal(p.duplicate_risk,true);await page.locator('#download-review').waitFor();assert.match(await page.locator('#social-result').innerText(),/Do not reword/);
 });
 await test('X has no reply, DM, like, follow or account-write route',async()=>{
  await page.locator('[data-platform="x"]').click();await page.locator('#social-media').selectOption('none');await page.locator('#social-asset').fill('');const pending=socialResponse();await page.locator('#review-social').click();const p=await(await pending).json();assert.equal(p.action,'review_own_post_only');assert(p.policy_notes.includes('automated_ai_replies_require_separate_platform_approval'));assert.equal(p.external_write_enabled,false);await page.locator('#download-review').waitFor();
 });
 await test('Instagram login/account/scopes remain unfulfilled, not granted by a checklist',async()=>{
  await page.locator('[data-platform="instagram"]').click();await page.locator('#social-media').selectOption('image');const pending=socialResponse();await page.locator('#review-social').click();const p=await(await pending).json();assert.equal(p.api_host_reference,'graph.instagram.com');assert(p.requirements.includes('professional_account_verification_required'));assert.deepEqual(p.scope_references_not_grants,['instagram_business_basic','instagram_business_content_publish']);assert.equal(p.external_write_enabled,false);await page.locator('#download-review').waitFor();
 });
 await test('validator outage retains draft and cannot claim a successful review',async()=>{
  await page.locator('#social-text').fill('Keep this during an outage');await page.route('**/api/social-plan',r=>r.abort());await page.locator('#review-social').click();await page.locator('#social-error').filter({hasText:'unavailable'}).waitFor();assert.equal(await page.locator('#social-text').inputValue(),'Keep this during an outage');assert.equal(await page.locator('#download-review').count(),0);await page.unroute('**/api/social-plan');
 });
 await test('late validator response cannot approve an edited draft',async()=>{
  let release,seen;const held=new Promise(r=>{release=r;}),received=new Promise(r=>{seen=r;});await page.route('**/api/social-plan',async r=>{seen();await held;await r.continue();});await page.locator('#review-social').click();await received;await page.locator('#social-text').fill('Changed while validating');release();await page.locator('#toast').filter({hasText:'late review was discarded'}).waitFor();assert.equal(await page.locator('#download-review').count(),0);await page.unroute('**/api/social-plan');
 });
 await test('opt-in browser persistence excludes financial data, authority and verified plans',async()=>{
  await nav('trust');assert(!(await page.locator('#remember-drafts').isChecked()));await page.locator('#remember-drafts').check();const d=await page.evaluate(k=>JSON.parse(localStorage.getItem(k)),KEY);assert.equal(d.schema,2);assert.equal(d.custom.length,2);assert(!JSON.stringify(d).includes('privateKey'));assert(!JSON.stringify(d).includes('sha256'));await page.reload({waitUntil:'networkidle'});assert(await page.locator('#remember-drafts').isChecked());assert.equal(await page.locator('#contact-list .contact-row').count(),12);
  await page.locator('#contact-list .contact-row').filter({hasText:'Atlas'}).click();const pending=page.waitForEvent('download');await page.locator('#download-companion').click();const dwn=await pending;assert.match(dwn.suggestedFilename(),/unvalidated/);assert.equal(JSON.parse(await readDownload(dwn)).provider,'xai');assert.match(await page.locator('.computer-desktop').innerText(),/No computer connected/);
 });
 await test('legacy browser data is preserved, never silently migrated or deleted',async()=>{
  await page.evaluate(k=>localStorage.setItem(k,'historical v1 local draft'),LEGACY);await page.reload({waitUntil:'networkidle'});await nav('trust');assert.match(await page.locator('#main').innerText(),/v1 browser data was detected and left untouched/);await page.locator('#clear-drafts').click();await page.locator('#confirm-clear').click();assert.equal(await page.evaluate(k=>localStorage.getItem(k),LEGACY),'historical v1 local draft');assert.equal(await page.evaluate(k=>localStorage.getItem(k),KEY),null);assert.equal(await page.locator('#contact-list .contact-row').count(),10);
 });
 await test('possible credentials are refused as briefs, not persisted or sent',async()=>{
  await nav('chat');await page.locator('#brief-input').fill('sk-'+'A'.repeat(30));await page.locator('#save-brief').click();assert.match(await page.locator('#toast').innerText(),/possible credentials/);assert.equal(await page.locator('.message.user').count(),0);await page.locator('#brief-input').fill('');
 });
 await test('local UTF-8 attachment is a composer draft, never automatically saved/uploaded',async()=>{
  await page.locator('#brief-file').setInputFiles({name:'brief.md',mimeType:'text/markdown',buffer:Buffer.from('An attached local brief')});await page.waitForFunction(()=>document.querySelector('#brief-input')?.value==='An attached local brief');assert.equal(await page.locator('.message.user').count(),0);
 });
 await test('invalid UTF-8, binary and oversized brief files fail closed',async()=>{
  for(const [name,data]of [['bad.md',Buffer.from([0xc3,0x28])],['bad.txt',Buffer.from('binary\0')],['huge.md',Buffer.alloc(32769,120)]]){await page.locator('#brief-file').setInputFiles({name,mimeType:'text/plain',buffer:data});await page.waitForTimeout(50);assert.equal(await page.locator('#brief-input').inputValue(),'An attached local brief');}
 });
 await test('editing a draft wins over a late local attachment read',async()=>{
  await page.evaluate(()=>{window.originalRead=File.prototype.arrayBuffer;File.prototype.arrayBuffer=function(){return new Promise(r=>{window.finishRead=()=>r(new TextEncoder().encode('Must be discarded').buffer);});};});await page.locator('#brief-file').setInputFiles({name:'late.md',mimeType:'text/plain',buffer:Buffer.from('x')});await page.waitForFunction(()=>typeof window.finishRead==='function');await page.locator('#brief-input').fill('Edited while reading');await page.evaluate(()=>{File.prototype.arrayBuffer=window.originalRead;window.finishRead();});await page.locator('#toast').filter({hasText:'Late file read discarded'}).waitFor();assert.equal(await page.locator('#brief-input').inputValue(),'Edited while reading');
 });
 await test('unpaired work and session views expose no privileged execution route',async()=>{
  await nav('work');assert(await page.locator('#new-qa').isDisabled());assert.match(await page.locator('#work-authority').innerText(),/cannot execute/);await nav('connection');assert(await page.locator('#pair-device').isDisabled());assert.equal(await page.locator('input[type="password"]').count(),0);
 });
 await test('mobile opens as companion list, selects chat, and returns with native-style back',async()=>{
  await page.setViewportSize({width:390,height:844});await page.reload({waitUntil:'networkidle'});if(await page.locator('#mobile-back').isVisible())await page.locator('#mobile-back').click();assert(await page.locator('#mobile-favorites').isVisible());assert(!(await page.locator('.conversation-panel').isVisible()));await page.screenshot({path:path.join(evidence,engine+'-mobile-list.png'),animations:'disabled'});await page.locator('#mobile-favorites [data-companion="chief"]').click();assert(await page.locator('#brief-input').isVisible());await page.locator('#brief-input').fill('A mobile work brief');await page.locator('#brief-input').press('Control+Enter');assert.match(await page.locator('.message.system').innerText(),/NOT AN AI RESPONSE/);await page.screenshot({path:path.join(evidence,engine+'-mobile-chat.png'),animations:'disabled'});assert(await page.evaluate(()=>window.openbotBack()));assert(await page.locator('#mobile-favorites').isVisible());
 });
 await test('mobile search includes pinned companions and details overlay dismisses accessibly',async()=>{
  await page.locator('#mobile-search').click();await page.locator('#contact-search').fill('Chief');assert.equal(await page.locator('#contact-list .contact-row:visible').count(),1);await page.locator('#contact-list [data-companion="chief"]').click();await page.locator('#show-computer').click();assert(await page.locator('#details-panel').isVisible());await page.keyboard.press('Escape');assert(!(await page.locator('#details-panel').isVisible()));assert.equal(await page.locator('#show-computer').getAttribute('aria-expanded'),'false');await page.locator('#mobile-back').click();await page.locator('#mobile-search').click();if(await page.locator('#contact-search').isVisible())await page.locator('#contact-search').fill('');
 });
 await test('all eight views fit 320px, 760px and desktop without horizontal document overflow',async()=>{
  for(const width of [320,760,1512]){await page.setViewportSize({width,height:900});for(const view of Object.keys(names)){await nav(view);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),width+' '+view);}}
 });
 await test('keyboard landmarks, dialog focus and mobile action names are present',async()=>{
  await nav('chat');await page.keyboard.press('Tab');assert.equal(await page.locator('main').getAttribute('tabindex'),'-1');assert.equal(await page.locator('aside[aria-label]').count(),2);await page.locator('#voice-info').click();assert.match(await page.locator('#modal').innerText(),/does not request microphone/);assert(await page.locator('#modal[open]').isVisible());await page.keyboard.press('Escape');assert.equal(await page.locator('#modal[open]').count(),0);
 });
 await test('sandboxed opaque offline preview supports drafting with no forms/storage/network grant',async()=>{
  const p=await context.newPage(),localErrors=[];p.on('pageerror',e=>localErrors.push(e.message));await p.goto(base);await p.setContent('<iframe title="Offline preview" sandbox="allow-scripts" style="width:100%;height:900px;border:0"></iframe>');await p.locator('iframe').evaluate((el,html)=>{el.srcdoc=html;},fs.readFileSync(path.join(__dirname,'../web/index.html'),'utf8'));const f=p.frameLocator('iframe');await f.locator('#brief-input').fill('Offline human brief');await f.locator('#save-brief').click();await f.locator('.message.system').waitFor();assert.match(await f.locator('.message.system').innerText(),/NOT AN AI RESPONSE/);assert.deepEqual(localErrors,[]);await p.close();
 });
 await test('malformed browser data cannot fabricate authority or crash rendering',async()=>{
  const c=await browser.newContext(),p=await c.newPage(),localErrors=[];p.on('pageerror',e=>localErrors.push(e.message));await p.goto(base);await p.evaluate(k=>localStorage.setItem(k,JSON.stringify({schema:2,remember:true,custom:[{id:'a'.repeat(36),name:'<img src=x>',role:'builder',provider:'xai',ide_tools:[],color:'#7d8ca5',initials:null}],briefs:[],routines:{}})),KEY);await p.reload({waitUntil:'networkidle'});assert.equal(await p.locator('#contact-list .contact-row').count(),11);assert.equal(await p.locator('#contact-list img').count(),0);assert.equal(await p.evaluate(()=>window.OpenBotWorkspace.connection.fresh),false);assert.deepEqual(localErrors,[]);await p.evaluate(k=>localStorage.setItem(k,'{"schema":9000,"remember":true,"vm_started":true}'),KEY);await p.reload({waitUntil:'networkidle'});assert.equal(await p.locator('#contact-list .contact-row').count(),10);assert.match(await p.locator('#toast').innerText(),/could not be verified/);await c.close();
 });
 await test('native capability hint blocks file/download affordances but grants no authority',async()=>{
  const c=await browser.newContext({userAgent:'Mozilla/5.0 OpenBotNative/0.3.0'}),p=await c.newPage();await p.goto(base);await p.locator('#download-companion').click();assert.match(await p.locator('#toast').innerText(),/Downloads are disabled/);assert.equal(await p.evaluate(()=>window.OpenBotWorkspace.connection.enabled),false);await p.locator('#attach-menu').click();await p.locator('#choose-brief').click();assert.match(await p.locator('#toast').innerText(),/File selection is disabled/);await c.close();
 });
 await test('no model, provider, installer, social write, telemetry or credential request occurred',async()=>{
  assert.deepEqual(requests.filter(r=>new URL(r.url).origin!==new URL(base).origin&&!r.url.startsWith('blob:')),[]);assert(!requests.some(r=>/\/api\/(publish|run|install|connect|vm|v1)/.test(r.url)));assert.deepEqual(errors,[]);
 });
 await context.close();
})().catch(error=>{console.error(error.stack);process.exitCode=1;}).finally(async()=>{
 if(browser)await browser.close();fs.writeFileSync(path.join(evidence,'ui-'+engine+'.json'),JSON.stringify({schema:'openbot.observed-reference-ui/1',engine,base,results,requests,page_errors:errors,scope:'Local light UI and synthetic planning. No real model, PC, IDE, social, native-device, independent accessibility or release acceptance.'},null,2)+'\n');console.log('Observed',results.filter(r=>r.status==='passed').length,'passed;',results.filter(r=>r.status==='failed').length,'failed');
});
