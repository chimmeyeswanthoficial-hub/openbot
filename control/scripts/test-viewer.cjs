/* Shared native offline HTML in opaque allow-scripts iframe, Chromium + WebKit.
 * These are browser checks, NEVER native launch or hardware trust acceptance.
 */
'use strict';
const {chromium,webkit}=require('playwright');
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..'),out=process.env.CONTROL_UI_EVIDENCE;
if(!out)throw Error('Set a NEW CONTROL_UI_EVIDENCE directory');fs.mkdirSync(out,{recursive:false});
const checks=[],errors=[],requests=[];
function check(name,ok){if(!ok)throw Error(name);checks.push({name,passed:true});}
let browser;
(async()=>{
 for(const engine of ['chromium','webkit']){
  browser=await({chromium,webkit})[engine].launch({headless:true,args:engine==='chromium'?['--no-sandbox']:[]});
  const p=await browser.newPage({viewport:{width:1512,height:982},reducedMotion:'reduce'});p.on('pageerror',e=>errors.push(engine+': '+e.message));p.on('request',r=>requests.push(r.url()));
  await p.setContent('<iframe title="Bundled OpenBot offline workspace" sandbox="allow-scripts" style="width:100%;height:950px;border:0" id="preview"></iframe>');await p.locator('#preview').evaluate((el,html)=>{el.srcdoc=html;},fs.readFileSync(path.join(root,'web/index.html'),'utf8'));const f=p.frameLocator('#preview');await f.locator('h1').waitFor();
  check(engine+' light three-column UI uses original SVG role avatars',await f.locator('meta[name="color-scheme"]').getAttribute('content')==='light'&&await f.locator('#contact-list .contact-row').count()===10);
  check(engine+' offline has no pairing, private key or claimed server authority',await f.locator('body').evaluate(()=>!window.OpenBotWorkspace.connection.enabled&&!window.OpenBotWorkspace.connection.fresh&&window.OpenBotWorkspace.connection.pairing===null));
  await f.locator('#brief-input').fill('Owned offline human work brief');await f.locator('#save-brief').click();check(engine+' offline briefs work without a forms or storage sandbox grant',(await f.locator('.message.system').innerText()).includes('NOT AN AI RESPONSE'));
  await f.locator('#voice-info').click();check(engine+' microphone cannot imply an active recorder',(await f.locator('#modal').innerText()).includes('does not request microphone'));
  check(engine+' native Back hook closes dialog',await f.locator('body').evaluate(()=>window.openbotBack()&&!document.querySelector('#modal').open));
  const nav=async view=>{if(await f.locator('#mobile-back').isVisible())await f.locator('#mobile-back').click();await f.locator('.contact-footer [data-view="plugins"]').click();if(view!=='plugins')await f.locator('#main [data-view="'+view+'"]').click();};
  await nav('work');check(engine+' offline proposal button is disabled',await f.locator('#new-qa').isDisabled());await f.locator('#main [data-view="connection"]').click();check(engine+' offline cannot collect pairing codes',await f.locator('#pair-device').isDisabled()&&await f.locator('input[type="password"]').count()===0);
  await nav('finance');await f.locator('#finance-csv').fill('date,description,amount,category\n2026-10-01,Fixture,1.13,Food');await f.locator('#finance-currency').selectOption('INR');await f.locator('#finance-confirm').check();await f.locator('#finance-analyze').click();check(engine+' offline exact CSV calculation works without server',(await f.locator('.finance-metrics').innerText()).includes('INR 1.13'));
  for(const width of [320,390,768,1512]){await p.setViewportSize({width,height:982});for(const view of ['plugins','finance','social','library','connection','work','trust']){await nav(view);check(engine+' '+view+' fits '+width,await f.locator('html').evaluate(el=>el.scrollWidth<=innerWidth));}}
  await nav('trust');check(engine+' native and release gaps remain explicit',(await f.locator('#main').innerText()).includes('iOS needs Mac/Xcode')&&(await f.locator('#main').innerText()).includes('Accepted real observed pilot days: 0'));
  await f.locator('#contact-list [data-companion="chief"]').click();if(engine==='chromium')await p.screenshot({path:path.join(out,'LIGHT-OFFLINE-DESKTOP.png'),animations:'disabled'});await p.setViewportSize({width:390,height:844});await f.locator('#mobile-back').click();if(engine==='chromium')await p.screenshot({path:path.join(out,'LIGHT-OFFLINE-MOBILE.png'),animations:'disabled'});
  check(engine+' skip link has a visible focus state',await f.locator('a.skip').evaluate(el=>{el.focus();return document.activeElement===el&&el.getBoundingClientRect().top>=0;}));await browser.close();browser=null;
 }
 check('No page errors in either browser',errors.length===0);check('No network requests from opaque offline workspace',requests.length===0);fs.writeFileSync(path.join(out,'viewer-checks.json'),JSON.stringify({schema:'openbot.shared-offline-viewer-proof/1',checks,count:checks.length,errors,requests,engines:['Chromium','Linux WebKit'],iframe_sandbox:'allow-scripts',native_devices_tested:false,full_accessibility_acceptance:false},null,2)+'\n');console.log(JSON.stringify({passed:checks.length,failed:0,page_errors:errors.length,native_devices_tested:false}));
})().catch(error=>{fs.writeFileSync(path.join(out,'viewer-failure.json'),JSON.stringify({error:error.stack,checks,errors,requests},null,2)+'\n');console.error(error);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();});
