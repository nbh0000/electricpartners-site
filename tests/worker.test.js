import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../worker/index.js';
const ORIGIN='https://test.invalid';
function fixture(overrides={}) {
  const state={inserts:[],count:0,scheduled:[]};
  const DB={prepare(sql){let args=[];return {bind(...v){args=v;return this;},async first(){state.count++;return {count:state.count};},async run(){state.inserts.push({sql,args});return {success:true};},sql};},async batch(q){state.scheduled=q;return [];}};
  const env={ENABLE_INQUIRIES:'true',PRIVACY_VERIFIED:'true',SITE_ORIGIN:ORIGIN,TURNSTILE_SECRET_KEY:'local-test-secret',TURNSTILE_HOSTNAME:'test.invalid',RATE_LIMIT_SALT:'unit-tests-not-a-deployment-secret',PRIVACY_VERSION:'test-v1',RETENTION_DAYS:'30',REQUIRE_TRANSFER_CONSENT:'false',DB,ASSETS:{fetch:async()=>new Response('asset')},...overrides};
  const payload={service:'onsite',inspectionType:'discuss',shutdownPossible:'unknown',province:'gyeonggi',city:'siheung',facility:'factory',requestType:'new',start:'discuss',workType:'day',phone:'010-0000-0000',contactName:'테스트 담당자',capacity:'확인 필요',email:'',message:'테스트 데이터',entryPath:'/regions/gyeonggi/siheung/',privacyConsent:true,transferConsent:false,privacyVersion:'test-v1',turnstileToken:'unit-test-token',attribution:{utm_source:'naver'},website:''};
  const pending=[];const ctx={waitUntil(p){pending.push(p);}};
  return {env,payload,state,ctx,pending};
}
function request(body,headers={},method='POST',path='/api/inquiries') {
  return new Request(ORIGIN+path,{method,headers:{Origin:ORIGIN,'Content-Type':'application/json','CF-Connecting-IP':'192.0.2.1',...headers},...(method==='POST'?{body:typeof body==='string'?body:JSON.stringify(body)}:{})});
}
const captcha=async()=>new Response(JSON.stringify({success:true,hostname:'test.invalid',action:'inquiry'}),{headers:{'Content-Type':'application/json'}});
async function runWithFetch(fn,mock=captcha){const old=globalThis.fetch;globalThis.fetch=mock;try{return await fn();}finally{globalThis.fetch=old;}}

test('disabled deployment rejects intake and stores nothing',async()=>{const f=fixture({ENABLE_INQUIRIES:'false'});const r=await worker.fetch(request(f.payload),f.env,f.ctx);assert.equal(r.status,503);assert.equal(f.state.inserts.length,0);});
test('privacy not confirmed blocks intake',async()=>{const f=fixture({PRIVACY_VERIFIED:'false'});assert.equal((await worker.fetch(request(f.payload),f.env,f.ctx)).status,503);});
test('zero retention blocks intake',async()=>{const f=fixture({RETENTION_DAYS:'0'});assert.equal((await worker.fetch(request(f.payload),f.env,f.ctx)).status,503);});
test('no public inquiry listing endpoint',async()=>{const f=fixture();assert.equal((await worker.fetch(request(null,{},'GET'),f.env,f.ctx)).status,405);assert.equal((await worker.fetch(request(null,{},'GET','/api/admin'),f.env,f.ctx)).status,404);});
test('cross-origin submissions rejected',async()=>{const f=fixture();assert.equal((await worker.fetch(request(f.payload,{Origin:'https://other.invalid'}),f.env,f.ctx)).status,403);});
test('non-JSON rejected',async()=>{const f=fixture();assert.equal((await worker.fetch(request('x',{'Content-Type':'text/plain'}),f.env,f.ctx)).status,415);});
test('malformed JSON rejected',async()=>{const f=fixture();assert.equal((await worker.fetch(request('{'),f.env,f.ctx)).status,400);});
test('oversized body rejected even without Content-Length',async()=>{const f=fixture();assert.equal((await worker.fetch(request('x'.repeat(17000)),f.env,f.ctx)).status,413);});
test('out-of-scope province rejected',async()=>{const f=fixture();f.payload.province='daejeon';assert.equal((await worker.fetch(request(f.payload),f.env,f.ctx)).status,400);});
test('city must belong to chosen province',async()=>{const f=fixture();f.payload.city='cheonan';assert.equal((await worker.fetch(request(f.payload),f.env,f.ctx)).status,400);});
test('privacy consent is required',async()=>{const f=fixture();f.payload.privacyConsent=false;assert.equal((await worker.fetch(request(f.payload),f.env,f.ctx)).status,400);});
test('old consent version rejected',async()=>{const f=fixture();f.payload.privacyVersion='old';assert.equal((await worker.fetch(request(f.payload),f.env,f.ctx)).status,409);});
test('configured third-party transfer requires separate consent',async()=>{const f=fixture({REQUIRE_TRANSFER_CONSENT:'true'});assert.equal((await worker.fetch(request(f.payload),f.env,f.ctx)).status,400);});
test('honeypot rejected without a false success response',async()=>{const f=fixture();f.payload.website='bot';assert.equal((await worker.fetch(request(f.payload),f.env,f.ctx)).status,400);});
test('phone validation rejects letters',async()=>{const f=fixture();f.payload.phone='abc01012345678';assert.equal((await worker.fetch(request(f.payload),f.env,f.ctx)).status,400);});
test('Turnstile hostname mismatch rejected',async()=>{await runWithFetch(async()=>{const f=fixture();assert.equal((await worker.fetch(request(f.payload),f.env,f.ctx)).status,400);},async()=>new Response(JSON.stringify({success:true,hostname:'wrong.invalid',action:'inquiry'})));});
test('valid inquiry stored privately using bound parameters',async()=>{await runWithFetch(async()=>{const f=fixture();const response=await worker.fetch(request(f.payload),f.env,f.ctx);assert.equal(response.status,201);const data=await response.json();assert.equal(data.ok,true);assert.match(data.reference,/^EP-/);assert.equal(f.state.inserts.length,1);assert.equal(f.state.inserts[0].args.length,23);assert.ok(f.state.inserts[0].args.includes('010-0000-0000'));assert.ok(!JSON.stringify(data).includes('010-'));assert.equal(response.headers.get('Cache-Control'),'no-store');await Promise.all(f.pending);});});
test('rate limit blocks sixth valid submission in the bucket',async()=>{await runWithFetch(async()=>{const f=fixture();for(let i=0;i<5;i++)assert.equal((await worker.fetch(request(f.payload),f.env,f.ctx)).status,201);assert.equal((await worker.fetch(request(f.payload),f.env,f.ctx)).status,429);assert.equal(f.state.inserts.length,5);await Promise.all(f.pending);});});
test('SQL errors do not return a false successful receipt',async()=>{await runWithFetch(async()=>{const f=fixture();f.env.DB.prepare=()=>({bind(){return this},first:async()=>({count:1}),run:async()=>{throw new Error('database unavailable')}});assert.equal((await worker.fetch(request(f.payload),f.env,f.ctx)).status,503);});});
test('retention job deletes expired records and request-limit hashes',async()=>{const f=fixture();await worker.scheduled({},f.env,f.ctx);await Promise.all(f.pending);assert.equal(f.state.scheduled.length,2);assert.match(f.state.scheduled[0].sql,/DELETE FROM inquiries/);});

test('duty inquiry records service and inspection scope',async()=>{await runWithFetch(async()=>{const f=fixture();Object.assign(f.payload,{service:'duty',inspectionType:'annual',shutdownPossible:'limited',requestType:'consult',workType:'discuss'});const response=await worker.fetch(request(f.payload),f.env,f.ctx);assert.equal(response.status,201);assert.equal(f.state.inserts[0].args[20],'duty');assert.equal(f.state.inserts[0].args[21],'annual');assert.equal(f.state.inserts[0].args[22],'limited');await Promise.all(f.pending);});});
test('unknown service rejected',async()=>{const f=fixture();f.payload.service='electrical_construction';assert.equal((await worker.fetch(request(f.payload),f.env,f.ctx)).status,400);});
test('expanded Seoul ward accepted',async()=>{await runWithFetch(async()=>{const f=fixture();f.payload.province='seoul';f.payload.city='gangnam';const res=await worker.fetch(request(f.payload),f.env,f.ctx);assert.equal(res.status,201);await Promise.all(f.pending);});});
test('expanded Incheon new ward accepted',async()=>{await runWithFetch(async()=>{const f=fixture();f.payload.province='incheon';f.payload.city='seohae';const res=await worker.fetch(request(f.payload),f.env,f.ctx);assert.equal(res.status,201);await Promise.all(f.pending);});});
