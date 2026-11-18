/* Actual shared light renderer -> real HTTPS -> P-256 proof -> kernel -> owned QA.
 * Disposable synthetic owner console only. No production/native/provider acceptance.
 * The private-key observation is injected by this test, never a shipped UI hook.
 */
'use strict';
const {chromium,webkit}=require('playwright');
const engine=process.env.TEST_ENGINE||'chromium';if(!['chromium','webkit'].includes(engine))throw Error('Unsupported engine');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {execFileSync}=require('node:child_process');
const profile=process.env.CONTROL_TEST_PROFILE,evidence=process.env.CONTROL_TEST_EVIDENCE;
if(!profile||!evidence)throw Error('Explicit disposable fixture and evidence required');
const cfg=JSON.parse(fs.readFileSync(path.join(profile,'profile.json'),'utf8'));
const ca=new crypto.X509Certificate(fs.readFileSync(path.join(profile,'tls-cert.pem')));
const pin=crypto.createHash('sha256').update(ca.publicKey.export({type:'spki',format:'der'})).digest('base64');
const canonical=v=>v===null||typeof v!=='object'?JSON.stringify(v):Array.isArray(v)?'['+v.map(canonical).join(',')+']':'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';
const checks=[],errors=[],requests=[],artifacts=[];
function check(name,ok,detail){if(!ok)throw Error(name+': '+JSON.stringify(detail));checks.push({name,passed:true,...(detail?{detail}:{})});console.log('PASS',name);}
function consoleCommand(command,args=[]){return JSON.parse(execFileSync(process.env.CONTROL_TEST_PYTHON,[process.env.CONTROL_TEST_CONSOLE,command,'--profile',profile,'--ack-local-synthetic',...args],{encoding:'utf8'}));}
let browser,proof;
(async()=>{
 browser=await({chromium,webkit})[engine].launch({headless:true,args:engine==='chromium'?['--no-sandbox','--ignore-certificate-errors-spki-list='+pin]:[]});
 const context=await browser.newContext({ignoreHTTPSErrors:engine==='webkit',viewport:{width:1512,height:982},reducedMotion:'reduce'});
 await context.addInitScript(()=>{const original=SubtleCrypto.prototype.generateKey;SubtleCrypto.prototype.generateKey=async function(...args){const key=await original.apply(this,args);if(key?.privateKey)window.__testKeyFact={privateExtractable:key.privateKey.extractable};return key;};const originalFetch=window.fetch;window.fetch=async function(...args){const response=await originalFetch.apply(this,args);if(args[0]==='/api/v1/tasks'&&args[1]?.method==='POST'&&window.__dropNextProposal){window.__dropNextProposal=false;throw new TypeError('TEST: response lost after actual server reply');}return response;};});
 const page=await context.newPage();page.on('pageerror',e=>errors.push(String(e)));
 page.on('request',r=>{if(r.url().startsWith('http')){const h=r.headers();requests.push({origin:new URL(r.url()).origin,path:new URL(r.url()).pathname,method:r.method()});if(!proof&&r.method()==='GET'&&new URL(r.url()).pathname==='/api/v1/snapshot'&&h['x-openbot-device'])proof={path:'/api/v1/snapshot',headers:{'X-OpenBot-Device':h['x-openbot-device'],'X-OpenBot-Challenge':h['x-openbot-challenge'],'X-OpenBot-Signature':h['x-openbot-signature']}};}});
 const fresh=()=>page.waitForFunction(()=>window.OpenBotWorkspace?.connection.fresh&&!window.OpenBotWorkspace.connection.busy);
 const work=async()=>{if(page.viewportSize().width<=760&&await page.locator('#mobile-back').isVisible())await page.locator('#mobile-back').click();await page.locator('.contact-footer [data-view="plugins"]').click();await page.locator('#main [data-view="work"]').click();};
 await page.goto(cfg.origin+'/control/',{waitUntil:'networkidle'});await page.waitForFunction(()=>window.OpenBotWorkspace?.connection.server);
 check('Secure WebCrypto context at exact gateway path',await page.evaluate(()=>isSecureContext&&Boolean(crypto.subtle)&&location.pathname==='/control/'));
 await work();check('Unpaired proposal is disabled',await page.locator('#new-qa').isDisabled());
 await page.locator('#main [data-view="connection"]').click();
 const code=JSON.parse(fs.readFileSync(path.join(profile,'pairing-code.json'),'utf8')).code;
 await page.locator('#pair-device').click();await page.locator('#pair-code').fill(code);await page.locator('#device-label').fill('Shared light Chromium fixture');await page.locator('#pair-submit').click();await fresh();
 check('Pairing derives owner/venture/scopes from server',await page.evaluate(()=>{const p=window.OpenBotWorkspace.connection.pairing;return p.role==='owner'&&p.venture==='demo'&&p.scopes.includes('approve');}));
 check('Actual renderer private key is non-exportable',await page.evaluate(()=>window.__testKeyFact?.privateExtractable===false));
 check('No renderer device secret was persisted',await page.evaluate(()=>localStorage.length===0&&sessionStorage.length===0));
 const device=await page.evaluate(()=>window.OpenBotWorkspace.connection.pairing.device);
 await work();
 async function record(id){await page.locator(`[data-task-detail="${id}"]`).click();const value=JSON.parse(await page.locator('#modal-body pre').innerText());await page.locator('#modal-close').click();return value;}
 async function propose(fixture,goal){await fresh();await page.locator('#new-qa').click();await page.locator('#fixture').selectOption(fixture);if(goal)await page.locator('#goal').fill(goal);await page.locator('#rights').check();await page.locator('#propose-submit').click();await page.locator('#modal[open]').waitFor({state:'hidden'});await fresh();const row=page.locator('[data-task]').filter({hasText:goal||'Validate the owned invoice sample'}).filter({has:page.locator('.task-status',{hasText:'review'})}).last();await row.waitFor();return record(await row.getAttribute('data-task'));}
 let first=true;
 for(const fixture of ['invoice-good-v1','invoice-discount-defect-v1','invoice-docs-defect-v1']){
  const row=await propose(fixture,'Prove shared light '+fixture);
  check(fixture+' is a real unattempted review proposal',row.status==='review'&&row.attempted===0);
  if(first){
   const n=requests.filter(r=>r.path.endsWith('/approve')).length;
   await page.locator(`[data-approve="${row.id}"]`).click();await page.locator('#reauth-code').fill('x'.repeat(43));await page.locator('#approve-submit').click();await fresh();
   check('Invalid exact-review code is refused without mutation retry',(await record(row.id)).status==='review'&&requests.filter(r=>r.path.endsWith('/approve')).length===n+1);
   first=false;
  }
  const reauth=consoleCommand('reauth',['--device',device,'--task',row.id,'--digest',row.spec_digest]);
  await page.locator(`[data-approve="${row.id}"]`).click();check(fixture+' exact plan/digest/device is visible for review',(await page.locator('#modal-body').innerText()).includes(row.spec_digest)&&(await page.locator('#modal-body').innerText()).includes(device));
  await page.locator('#reauth-code').fill(reauth.code);await page.locator('#approve-submit').click();await fresh();await page.locator(`[data-execute="${row.id}"]`).waitFor();
  check(fixture+' exact approval queues but does not execute',(await record(row.id)).status==='queued');
  const n=requests.filter(r=>r.path.endsWith('/execute')).length;await page.locator(`[data-execute="${row.id}"]`).click();check(fixture+' requires separate execution confirmation',await page.locator('#confirm-execute').isVisible()&&requests.filter(r=>r.path.endsWith('/execute')).length===n);await page.locator('#confirm-execute').click();
  await page.locator(`[data-artifact="${row.id}"]`).waitFor({timeout:30000});await fresh();await page.locator(`[data-artifact="${row.id}"]`).click();await page.locator('#modal-title').filter({hasText:'Server-verified local artifact'}).waitFor();
  const content=JSON.parse(await page.locator('#modal-body pre').innerText()),text=await page.locator('#modal-body').innerText();const hash=crypto.createHash('sha256').update(canonical(content)).digest('hex');check(fixture+' actual artifact content/hash is read back',text.includes(hash)&&text.includes('No external delivery'));
  artifacts.push({task:row.id,fixture,sha256:hash,content,qualified_human_acceptance:false});await page.locator('#modal-close').click();
 }
 const pending=await propose('invoice-good-v1','Untrusted goal <img src=x onerror="window.poison=1">');
 check('Untrusted task content stays text, never HTML or authority',await page.evaluate(()=>window.poison===undefined&&document.querySelectorAll('img[src="x"]').length===0));
 const book=JSON.parse(await page.locator('#server-book').textContent());check('Canonical exact-book strings retain source and settlement limits',book.source==='economic_v1_postings'&&book.summary.net_captured_minor==='20000'&&book.not_profit_or_bank_settlement===true);
 check('Scoped audit is actually read back',JSON.parse(await page.locator('#server-audit').textContent()).length>0);
 // Simulate a response lost AFTER a real HTTPS proposal reaches the kernel.
 await page.evaluate(()=>{window.__dropNextProposal=true;});
 const before=requests.filter(r=>r.method==='POST'&&r.path==='/api/v1/tasks').length;
 await fresh();await page.locator('#new-qa').click();await page.locator('#goal').fill('Ambiguous response fixture');await page.locator('#rights').check();await page.locator('#propose-submit').click();await page.locator('#proposal-error').filter({hasText:'Outcome requires read-back'}).waitFor();check('Uncertain response never triggers implicit mutation replay',requests.filter(r=>r.method==='POST'&&r.path==='/api/v1/tasks').length===before+1);await page.evaluate(()=>{window.__dropNextProposal=false;});await page.locator('#modal-close').click();await page.locator('#refresh-server').click();await fresh();check('Explicit refresh recovers the one real proposal',await page.locator('[data-task]').filter({hasText:'Ambiguous response fixture'}).count()===1);
 await page.locator('#new-qa').click();check('Previous uncertain proposal must be inspected before any new proposal',await page.locator('#inspect-prior-proposal').isVisible());await page.locator('#inspect-prior-proposal').click();await fresh();
 await page.locator(`[data-cancel="${pending.id}"]`).click();await fresh();check('Explicit stop is read back as cancelled, not remote kill',(await record(pending.id)).status==='cancelled');
 await context.setOffline(true);await page.waitForFunction(()=>!window.OpenBotWorkspace.connection.fresh&&document.querySelector('#new-qa')?.disabled&&document.querySelector('#gateway-badge')?.textContent.includes('Stale'));check('Offline disables proposal and clearly reports stale state',await page.locator('#new-qa').isDisabled()&&(await page.locator('#gateway-badge').textContent()).includes('Stale'));await context.setOffline(false);await fresh();check('Reconnect uses an authoritative read, not cached approval',await page.evaluate(()=>window.OpenBotWorkspace.taskCount===5));
 await page.evaluate(()=>window.dispatchEvent(new Event('openbotpause')));check('Native pause immediately removes write freshness',await page.evaluate(()=>!window.OpenBotWorkspace.connection.fresh));await page.evaluate(()=>window.dispatchEvent(new Event('openbotresume')));await fresh();check('Native resume reads fresh signed state',await page.evaluate(()=>window.OpenBotWorkspace.connection.fresh));
 const denial=await page.evaluate(async proof=>{const replay=await fetch(proof.path,{headers:proof.headers,credentials:'omit'});const changed=await fetch('/api/v1/status',{headers:proof.headers,credentials:'omit'});const c=await(await fetch('/api/v1/challenge',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({device:window.OpenBotWorkspace.connection.pairing.device,method:'GET',path:'/api/v1/status',body_sha256:'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',api_version:'1'}),credentials:'omit'})).json();const forged=await fetch('/api/v1/status',{headers:{'X-OpenBot-Device':window.OpenBotWorkspace.connection.pairing.device,'X-OpenBot-Challenge':c.data.id,'X-OpenBot-Signature':btoa(String.fromCharCode(...new Uint8Array(64))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'')},credentials:'omit'});return[replay.status,changed.status,forged.status];},proof);
 check('Real TLS API refuses consumed proof replay',denial[0]===403);check('Real TLS API refuses proof moved to another path',denial[1]===403);check('Real TLS API refuses a forged device signature',denial[2]===403);
 async function scopedView(role,venture){const c=await browser.newContext({ignoreHTTPSErrors:engine==='webkit',viewport:{width:1440,height:960}}),p=await c.newPage();p.on('pageerror',e=>errors.push(String(e)));await p.goto(cfg.origin+'/control/#connection');await p.waitForFunction(()=>window.OpenBotWorkspace.connection.server);const code=consoleCommand('pairing',['--role',role,'--venture',venture]).code;await p.locator('#pair-device').click();await p.locator('#pair-code').fill(code);await p.locator('#pair-submit').click();await p.waitForFunction(()=>window.OpenBotWorkspace.connection.fresh&&!window.OpenBotWorkspace.connection.busy);await p.locator('#main [data-view="work"]').click();return{c,p};}
 const viewer=await scopedView('viewer','demo');check('Server viewer cannot propose or approve',await viewer.p.locator('#new-qa').isDisabled()&&await viewer.p.locator('[data-approve]:enabled').count()===0);await viewer.c.close();const other=await scopedView('owner','other');check('Other venture cannot read these owned tasks',await other.p.evaluate(()=>window.OpenBotWorkspace.taskCount===0));await other.c.close();
 for(const width of [320,390,768,1512]){await page.setViewportSize({width,height:width<500?844:982});check('Live work has no root horizontal overflow at '+width,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));}
 await page.screenshot({path:path.join(evidence,'LIGHT-LIVE-DESKTOP.png'),animations:'disabled'});await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(evidence,'LIGHT-LIVE-MOBILE.png'),animations:'disabled'});await page.setViewportSize({width:1512,height:982});
 consoleCommand('revoke',['--device',device]);await page.locator('#refresh-server').click();await page.waitForFunction(()=>!window.OpenBotWorkspace.connection.fresh&&!window.OpenBotWorkspace.connection.busy&&document.querySelector('#new-qa')?.disabled);check('Host-console revocation disables client mutation after read-back',await page.evaluate(()=>!window.OpenBotWorkspace.connection.fresh)&&await page.locator('#new-qa').isDisabled());
 check('No cross-origin request or provider call was made',requests.every(r=>r.origin===cfg.origin));check('No renderer page errors',errors.length===0,errors);
 fs.writeFileSync(path.join(evidence,'owned-artifacts.json'),JSON.stringify({artifacts,provider_used:false,external_delivery:false,qualified_human_acceptance:false},null,2)+'\n');
 const receipt={schema:'openbot.shared-gateway-browser-proof/1',checks,count:checks.length,requests,errors,engine,transport:engine==='chromium'?'Actual HTTPS; exact disposable fixture SPKI permitted; ignoreHTTPSErrors=false. Separate Python real CA/wrong-host/default-trust checks.':'Actual HTTPS/WebCrypto behavior with TEST-ONLY WebKit ignoreHTTPSErrors=true for disposable self-signed localhost certificate. This does NOT test WebKit/native trust. Separate Python CA/wrong-host/default-trust checks still run; production/native code never bypasses TLS.',native_devices_tested:false,provider_used:false,production_authorized:false,independent_security_acceptance:false};fs.writeFileSync(path.join(evidence,'s08-browser.json'),JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify({passed:checks.length,failed:0,page_errors:errors.length,native_device_proof:false}));await context.close();
})().catch(error=>{fs.writeFileSync(path.join(evidence,'shared-gateway-failure.json'),JSON.stringify({error:error.stack,checks,errors,requests},null,2)+'\n');console.error(error);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();});
