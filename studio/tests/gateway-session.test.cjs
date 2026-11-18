// Protocol unit tests with real WebCrypto but a FAKE transport/server.
// Not TLS, native, provider or independent security acceptance.
'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {webcrypto,createHash,randomBytes,randomUUID}=require('node:crypto');
const {Session,liveLocation,allowed}=require('../web/gateway-session.js');
const hash=s=>createHash('sha256').update(s).digest('hex');
const canonical=v=>v===null||typeof v!=='object'?JSON.stringify(v):Array.isArray(v)?'['+v.map(canonical).join(',')+']':'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';
const origin={protocol:'https:',origin:'https://owned.invalid',pathname:'/control/',search:''};
const code='g'.repeat(43),id='w'+'b'.repeat(32),planDigest='c'.repeat(64);
const proposal=()=>({request_id:randomUUID(),fixture:'invoice-good-v1',goal:'Check owned sample',acceptance:'Report independent test evidence',rights_ref:'owned:first-party-seed',ai_use_approved:true,destination:'local-review'});
const gate=()=>{let release;const promise=new Promise(r=>{release=r;});return{promise,release};};
function fixture(options={}){
 let mono=100,online=true,pub,expired=false,change=0;
 const requests=[],challenges=new Map(),keys=[];
 const data={role:'owner',device:'d'.repeat(32),venture:'demo',scopes:['read','propose','approve','execute','cancel','revoke-self'],expires:1700000900,...options.pairing};
 const snapshot={status:{execution_mode:'fixed_owned_qa_only',paid_provider_enabled:false,customer_execution_enabled:false},tasks:[{id,status:'review',spec_digest:planDigest}],audit:[],exact_book:{summary:{},postings:[]}};
 const artifact={content:{kind:'synthetic-unit-artifact',approved:false},external_delivery:false};artifact.sha256=hash(canonical(artifact.content));
 function envelope(value){return{api_version:'1',server_id:'a'.repeat(64),observed_at:1700000000,fresh_for_seconds:15,source:'local_authenticated_server',data:value};}
 const subtle=new Proxy(webcrypto.subtle,{get(target,k){if(k==='generateKey')return async(...args)=>{if(options.keyGate)await options.keyGate.promise;const key=await target.generateKey(...args);keys.push(key);return key;};const v=target[k];return typeof v==='function'?v.bind(target):v;}});
 const transport=async(path,request)=>{
  requests.push({path,...request});const body=request.body?JSON.parse(request.body):null;let value;
  if(path==='/api/v1/identity')value={client_version:'0.2.0',client_sha256:'e'.repeat(64),tls_required:true,mode:'local_owned_fixture',public_or_production_release:false};
  else if(path==='/api/v1/pair'){
   pub=await webcrypto.subtle.importKey('spki',Buffer.from(body.public_key,'base64url'),{name:'ECDSA',namedCurve:'P-256'},true,['verify']);
   assert(await webcrypto.subtle.verify({name:'ECDSA',hash:'SHA-256'},pub,Buffer.from(body.signature,'base64url'),Buffer.from('openbot.pair/1\n'+'a'.repeat(64)+'\n'+code)));
   value={...data,...(expired?{expires:1699999999}:{})};
  }else if(path==='/api/v1/challenge'){
   const nonce=randomBytes(24).toString('base64url'),expires=1700000030;
   value={id:nonce,expires,message:['openbot.control-request/1','a'.repeat(64),data.device,nonce,body.method,body.path,body.body_sha256,String(expires)].join('\n')};
   challenges.set(nonce,{...body,...value});if(options.tamperChallenge)value.message+=' changed';
  }else{
   const c=challenges.get(request.headers['X-OpenBot-Challenge']);assert(c,'one-use challenge required');challenges.delete(c.id);
   assert.equal(c.method,request.method);assert.equal(c.path,path);assert.equal(c.body_sha256,hash(request.body||''));
   assert(await webcrypto.subtle.verify({name:'ECDSA',hash:'SHA-256'},pub,Buffer.from(request.headers['X-OpenBot-Signature'],'base64url'),Buffer.from(c.message)));
   if(path==='/api/v1/snapshot'){if(options.readGate)await options.readGate.promise;value=snapshot;}
   else if(path.endsWith('/artifact'))value=artifact;
   else if(path==='/api/v1/tasks'){if(options.writeGate)await options.writeGate.promise;if(options.failWrite)throw Error('synthetic lost response after possible write');value={id,status:'review',spec_digest:planDigest};}
   else if(path.endsWith('/approve')){snapshot.tasks[0].status='queued';value={approved:true};}
   else if(path.endsWith('/execute')){snapshot.tasks[0].status='completed';value={status:'completed'};}
   else if(path.endsWith('/cancel')){snapshot.tasks[0].status='cancelled';value={cancelled:true};}
   else if(path==='/api/v1/session/revoke')value={revoked:true,running_work_stop_confirmed:false};
   else throw Error('unexpected unit route '+path);
  }
  const env=envelope(value);if(options.badServer&&path!=='/api/v1/identity')env.server_id='f'.repeat(64);
  return{ok:true,json:async()=>JSON.parse(JSON.stringify(env))};
 };
 const session=new Session({location:origin,transport,crypto:{subtle},now:()=>mono,online:()=>online,changed:()=>{change++;}});
 return{session,requests,keys,snapshot,artifact,options,setTime:v=>{mono=v;},setOnline:v=>{online=v;},expire:()=>{expired=true;},get changes(){return change;},async pair(){await session.identify();return session.pair(code,'Unit device');}};
}
test('live route accepts only HTTPS exact /control/ without query',()=>{
 assert(liveLocation(origin));for(const x of [{protocol:'http:'},{pathname:'/'},{pathname:'/control'},{search:'?actor=owner'},{origin:'null'}])assert(!liveLocation({...origin,...x}));
});
test('route allowlist rejects authority issuance, arbitrary tasks and path encodings',()=>{
 assert(allowed('GET','/api/v1/snapshot'));assert(allowed('POST','/api/v1/tasks/'+id+'/approve'));
 for(const [m,p]of [['POST','/api/v1/pairing-grant'],['POST','/api/v1/run'],['GET','/api/v1/tasks/../../secret'],['POST','/api/v1/tasks/'+id+'/execute?role=owner'],['POST','https://evil.invalid/api/v1/tasks'],['DELETE','/api/v1/tasks'],['GET','/api/v1/%73napshot']])assert(!allowed(m,p));
});
test('local preview cannot identify, pair or mutate',async()=>{
 let count=0;const s=new Session({location:{...origin,pathname:'/'},transport:()=>{count++;}});assert.equal(await s.identify(),false);await assert.rejects(s.pair(code,'Label'));await assert.rejects(s.propose(proposal()));assert.equal(count,0);
});
test('unpaired state has no authority and bad console inputs send nothing',async()=>{
 const f=fixture();await f.session.identify();const n=f.requests.length;for(const pair of [['api-key','Label'],[code,''],[code,'x\n']])await assert.rejects(f.session.pair(...pair));await assert.rejects(f.session.propose(proposal()));assert.equal(f.requests.length,n);assert(!f.session.fresh());
});
test('real P-256 proofs pair, scopes derive from server, private key is non-exportable',async()=>{
 const f=fixture();assert(await f.pair());assert(f.session.can('propose'));assert.equal(f.keys[0].privateKey.extractable,false);await assert.rejects(webcrypto.subtle.exportKey('pkcs8',f.keys[0].privateKey));assert.equal(f.session.info().pairing.role,'owner');assert(!('keys'in f.session));assert(f.changes>0);
});
test('identity mismatch after first identity fails closed',async()=>{
 const f=fixture({badServer:true});await assert.rejects(f.pair(),/identity or version/);assert(!f.session.pairing);assert(!f.session.can('execute'));
});
test('expired pairing result never becomes an active device',async()=>{
 const f=fixture();f.expire();await assert.rejects(f.pair(),/server-derived/);assert.equal(f.session.pairing,null);
});
test('unknown or escalated viewer scopes are refused',async()=>{
 for(const pairing of [{scopes:['read','root']},{role:'viewer'},{scopes:['read','read']}]){const f=fixture({pairing});await assert.rejects(f.pair(),/server-derived/);assert(!f.session.can('approve'));}
});
test('viewer cannot propose, approve, execute or cancel',async()=>{
 const f=fixture({pairing:{role:'viewer',scopes:['read','revoke-self']}});await f.pair();assert(f.session.can('read'));for(const s of ['propose','approve','execute','cancel'])assert(!f.session.can(s));const n=f.requests.length;await assert.rejects(f.session.propose(proposal()));assert.equal(f.requests.length,n);
});
test('snapshot expires at exactly fifteen seconds and ignores backward monotonic time',async()=>{
 const f=fixture();await f.pair();f.setTime(15099);assert(f.session.fresh());f.setTime(15100);assert(!f.session.can('propose'));f.setTime(99);assert(!f.session.fresh());
});
test('server grant expiry limits otherwise fresh snapshot',async()=>{
 const f=fixture({pairing:{expires:1700000001}});await f.pair();f.setTime(1100);assert(!f.session.can('execute'));
});
test('offline immediately disables writes without dispatch',async()=>{
 const f=fixture();await f.pair();f.setOnline(false);const n=f.requests.length;await assert.rejects(f.session.propose(proposal()),/Fresh/);assert.equal(f.requests.length,n);
});
test('edits, arbitrary shell, foreign destination and UI role/venture are refused',async()=>{
 const f=fixture();await f.pair();const n=f.requests.length;
 for(const patch of [{actor:'human:owner'},{venture:'other'},{role:'owner'},{fixture:'shell'},{rights_ref:'unknown'},{destination:'external'},{ai_use_approved:false},{request_id:'-'.repeat(36)},{goal:'bad\ncontrol'}])await assert.rejects(f.session.propose({...proposal(),...patch}),/Exact owned/);
 assert.equal(f.requests.length,n);
});
test('proposal signs exact method/path/body once and requires a new read-back',async()=>{
 const f=fixture();await f.pair();const p=proposal();await f.session.propose(p);const r=f.requests.filter(r=>r.path==='/api/v1/tasks');assert.equal(r.length,1);assert.deepEqual(JSON.parse(r[0].body),p);assert(!f.session.can('approve'));assert(await f.session.refresh());assert(f.session.can('approve'));assert(r[0].credentials==='omit'&&r[0].redirect==='error');
});
test('malformed challenge does not dispatch a signed operation',async()=>{
 const f=fixture();await f.pair();f.options.tamperChallenge=true;await assert.rejects(f.session.propose(proposal()),/binding/);assert.equal(f.requests.filter(r=>r.path==='/api/v1/tasks').length,0);assert(!f.session.fresh());
});
test('unknown write response is not retried and removes write freshness',async()=>{
 const f=fixture({failWrite:true});await f.pair();await assert.rejects(f.session.propose(proposal()),/lost response/);assert.equal(f.requests.filter(r=>r.path==='/api/v1/tasks').length,1);assert(!f.session.fresh());assert.match(f.session.error,/no automatic retry/);
});
test('approval requires exact task/digest, review state and separate console code',async()=>{
 const f=fixture();await f.pair();const n=f.requests.length;for(const a of [['approve',id,'f'.repeat(64),code],['approve',id,planDigest,''],['execute',id,planDigest],['approve','w'+'d'.repeat(32),planDigest,code]])await assert.rejects(f.session.taskAction(...a));assert.equal(f.requests.length,n);
});
test('approval never implicitly executes, execution is a separate exact signed request',async()=>{
 const f=fixture();await f.pair();await f.session.taskAction('approve',id,planDigest,code);assert.equal(f.requests.filter(r=>r.path.endsWith('/execute')).length,0);await f.session.refresh();await f.session.taskAction('execute',id,planDigest);assert.equal(f.requests.filter(r=>r.path.endsWith('/execute')).length,1);
});
test('cancel is explicit and does not claim remote process kill',async()=>{
 const f=fixture();await f.pair();await f.session.taskAction('cancel',id);assert.equal(f.requests.filter(r=>r.path.endsWith('/cancel')).length,1);assert(!f.session.fresh());
});
test('artifact content is hash checked, external delivery is refused',async()=>{
 const f=fixture();await f.pair();assert.equal((await f.session.artifact(id)).sha256,f.artifact.sha256);f.artifact.content.approved=true;await assert.rejects(f.session.artifact(id),/artifact content/);await f.session.refresh();f.artifact.sha256=hash(canonical(f.artifact.content));f.artifact.external_delivery=true;await assert.rejects(f.session.artifact(id),/artifact content/);
});
test('revoke forgets device and key locally only after acknowledged request',async()=>{
 const f=fixture();await f.pair();await f.session.revoke();assert.equal(f.session.pairing,null);assert.equal(f.session.snapshot.tasks.length,0);assert(!f.session.can('read'));await assert.rejects(f.session.artifact(id));
});
test('forget is not a claim of server revocation',async()=>{
 const f=fixture();await f.pair();f.session.forget();assert.match(f.session.error,/Revoke on the trusted server/);assert.equal(f.requests.filter(r=>r.path.includes('revoke')).length,0);
});
test('cancelled key generation cannot send a later pairing request',async()=>{
 const g=gate(),f=fixture({keyGate:g});await f.session.identify();const p=f.session.pair(code,'Unit device');f.session.invalidate('User cancelled');g.release();await assert.rejects(p,/cancelled before dispatch/);assert.equal(f.requests.filter(r=>r.path==='/api/v1/pair').length,0);
});
test('late write after invalidation is discarded with no replay',async()=>{
 const g=gate(),f=fixture({writeGate:g});await f.pair();const p=f.session.propose(proposal());while(!f.requests.some(r=>r.path==='/api/v1/tasks'))await new Promise(r=>setImmediate(r));f.session.invalidate('Paused');g.release();await assert.rejects(p,/Late response/);assert.equal(f.requests.filter(r=>r.path==='/api/v1/tasks').length,1);assert(!f.session.fresh());
});
test('only one refresh is active; no mutation races a pending snapshot',async()=>{
 const f=fixture();await f.pair();const g=gate();f.options.readGate=g;const p=f.session.refresh();assert.equal(await f.session.refresh(),false);await assert.rejects(f.session.propose(proposal()),/Fresh/);g.release();assert(await p);
});
test('late read after lifecycle invalidation cannot restore authority',async()=>{
 const f=fixture();await f.pair();const g=gate();f.options.readGate=g;const p=f.session.refresh();f.session.invalidate('Backgrounded');g.release();assert.equal(await p,false);assert(!f.session.can('approve'));assert.match(f.session.error,/Backgrounded/);
});
