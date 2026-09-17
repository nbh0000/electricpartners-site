/**
 * Private inquiry receiver for Cloudflare Workers + D1.
 * Disabled unless deployment, privacy, anti-bot and retention settings are present.
 * No public inquiry list or admin endpoint is provided.
 */
import { REGION_CITIES } from './regions.js';
const MAX_BYTES = 16_384;
const ALLOWED = {
  service: ['onsite','duty','both'],
  inspectionType: ['discuss','periodic','annual','specific'],
  shutdownPossible: ['unknown','yes','limited','no'],
  facility: ['factory','logistics','building','construction','other'],
  requestType: ['new','change','transition','consult'],
  start: ['discuss','soon','month','later'],
  workType: ['discuss','day','shift']
};
const TEXT_LIMITS = {capacity:120,contactName:60,phone:20,email:254,message:2000,entryPath:200};
const TRACKED = ['utm_source','utm_medium','utm_campaign','utm_content','utm_term','n_keyword','n_keyword_id','n_ad_group','n_ad','gclid'];
const reply = (status, data) => new Response(JSON.stringify(data), {status,headers:{
  'Content-Type':'application/json; charset=utf-8',
  'Cache-Control':'no-store',
  'X-Content-Type-Options':'nosniff',
  'X-Robots-Tag':'noindex, nofollow',
  'Referrer-Policy':'no-referrer'
}});

async function readJSON(request) {
  if(Number(request.headers.get('content-length')||0)>MAX_BYTES)throw new Error('TOO_LARGE');
  if(!request.body)throw new Error('BAD_JSON');
  const reader=request.body.getReader();const chunks=[];let length=0;
  try{
    for(;;){const {value,done}=await reader.read();if(done)break;length+=value.length;if(length>MAX_BYTES){await reader.cancel();throw new Error('TOO_LARGE');}chunks.push(value);}
  }finally{reader.releaseLock();}
  const bytes=new Uint8Array(length);let offset=0;for(const c of chunks){bytes.set(c,offset);offset+=c.length;}
  try{return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));}catch{throw new Error('BAD_JSON');}
}
function validate(body,env) {
  if(!body||typeof body!=='object'||Array.isArray(body))return {error:'입력 형식을 확인해 주세요.'};
  if(body.website)return {error:'접수할 수 없는 요청입니다.'};
  if(body.privacyConsent!==true)return {error:'개인정보 수집·이용 동의가 필요합니다.'};
  if(env.REQUIRE_TRANSFER_CONSENT==='true' && body.transferConsent!==true)return {error:'개인정보 제공 동의를 확인해 주세요.'};
  if(body.privacyVersion!==env.PRIVACY_VERSION)return {error:'개인정보 안내가 변경되었습니다. 페이지를 새로 열어 주세요.',status:409};
  if(typeof body.province!=='string'||!Object.hasOwn(REGION_CITIES,body.province))return {error:'상담 대상 권역을 확인해 주세요.'};
  if(!REGION_CITIES[body.province].includes(body.city))return {error:'현장 세부 지역을 확인해 주세요.'};
  const cleaned={province:body.province,city:body.city};
  for(const [name,values] of Object.entries(ALLOWED)){
    if(!values.includes(body[name]))return {error:'시설과 운영 조건을 확인해 주세요.'};
    cleaned[name]=body[name];
  }
  for(const [name,max] of Object.entries(TEXT_LIMITS)){
    if(body[name]!==undefined && typeof body[name]!=='string')return {error:'입력값 형식을 확인해 주세요.'};
    const v=(body[name]||'').trim();if(v.length>max||/[\x00-\x08\x0B\x0C\x0E-\x1F]/.test(v))return {error:'입력 길이와 문자를 확인해 주세요.'};
    cleaned[name]=v;
  }
  if(!/^[+0-9\s()\-]+$/.test(cleaned.phone) || cleaned.phone.replace(/\D/g,'').length<9 || cleaned.phone.replace(/\D/g,'').length>13)return {error:'연락처 형식을 확인해 주세요.'};
  if(cleaned.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleaned.email))return {error:'이메일 형식을 확인해 주세요.'};
  if(cleaned.entryPath && !/^\/[a-z0-9\-/]*$/.test(cleaned.entryPath))cleaned.entryPath='/';
  cleaned.attribution={};
  if(body.attribution && typeof body.attribution==='object' && !Array.isArray(body.attribution)){
    for(const k of TRACKED){const v=body.attribution[k];if(typeof v==='string')cleaned.attribution[k]=v.slice(0,200);}
  }
  if(typeof body.turnstileToken!=='string'||body.turnstileToken.length<1||body.turnstileToken.length>2048)return {error:'보안 확인을 완료해 주세요.'};
  return {cleaned};
}
async function verifyTurnstile(token,env) {
  try{
    const response=await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({secret:env.TURNSTILE_SECRET_KEY,response:token}),
      signal:AbortSignal.timeout(8000)
    });
    if(!response.ok)return false;
    const check=await response.json();
    return check.success===true && check.hostname===env.TURNSTILE_HOSTNAME && check.action==='inquiry';
  }catch{return false;}
}
async function limited(ip,env) {
  // Hash IPs with a secret salt; do not retain raw addresses in the application DB.
  const bucket=Math.floor(Date.now()/300000);
  const key=await crypto.subtle.importKey('raw',new TextEncoder().encode(env.RATE_LIMIT_SALT),{name:'HMAC',hash:'SHA-256'},false,['sign']);
  const hash=await crypto.subtle.sign('HMAC',key,new TextEncoder().encode(`${ip}|${bucket}`));
  const fingerprint=Array.from(new Uint8Array(hash),b=>b.toString(16).padStart(2,'0')).join('');
  const expiry=new Date((bucket+2)*300000).toISOString();
  const row=await env.DB.prepare('INSERT INTO request_limits (fingerprint, count, expires_at) VALUES (?,1,?) ON CONFLICT(fingerprint) DO UPDATE SET count = count + 1 RETURNING count').bind(fingerprint,expiry).first();
  return !row || row.count>5;
}
async function notify(reference,cleaned,env) {
  if(!env.LEAD_NOTIFY_URL)return;
  try{
    const target=new URL(env.LEAD_NOTIFY_URL);if(target.protocol!=='https:')return;
    const headers={'Content-Type':'application/json'};if(env.LEAD_NOTIFY_TOKEN)headers.Authorization='Bearer '+env.LEAD_NOTIFY_TOKEN;
    // Notification intentionally excludes phone, name, email and message.
    await fetch(target,{method:'POST',headers,body:JSON.stringify({event:'private_inquiry_created',reference,province:cleaned.province,service:cleaned.service,requestType:cleaned.requestType}),signal:AbortSignal.timeout(8000)});
  }catch{/* Intake remains successful after storage even if a notification fails. */}
}
export default {
  async fetch(request,env,ctx) {
    const url=new URL(request.url);
    if(!url.pathname.startsWith('/api/'))return env.ASSETS.fetch(request);
    if(url.pathname!=='/api/inquiries')return reply(404,{ok:false,error:'해당 경로가 없습니다.'});
    if(request.method!=='POST')return reply(405,{ok:false,error:'허용하지 않는 요청 방식입니다.'});
    const retention=Number(env.RETENTION_DAYS);
    if(env.ENABLE_INQUIRIES!=='true'||env.PRIVACY_VERIFIED!=='true'||!env.DB||!env.SITE_ORIGIN||!env.TURNSTILE_SECRET_KEY||!env.TURNSTILE_HOSTNAME||!env.RATE_LIMIT_SALT||!env.PRIVACY_VERSION||!Number.isInteger(retention)||retention<1||retention>3650)
      return reply(503,{ok:false,error:'온라인 상담 접수를 준비 중입니다.'});
    if(request.headers.get('origin')!==env.SITE_ORIGIN || url.origin!==env.SITE_ORIGIN)return reply(403,{ok:false,error:'허용된 사이트에서 다시 접수해 주세요.'});
    if(!(request.headers.get('content-type')||'').toLowerCase().startsWith('application/json'))return reply(415,{ok:false,error:'입력 형식을 확인해 주세요.'});
    let body;try{body=await readJSON(request);}catch(error){return reply(error.message==='TOO_LARGE'?413:400,{ok:false,error:'요청 크기 또는 입력 형식을 확인해 주세요.'});}
    const checked=validate(body,env);if(checked.error)return reply(checked.status||400,{ok:false,error:checked.error});
    if(!await verifyTurnstile(body.turnstileToken,env))return reply(400,{ok:false,error:'보안 확인이 만료되었거나 유효하지 않습니다. 다시 확인해 주세요.'});
    const ip=request.headers.get('CF-Connecting-IP');if(!ip)return reply(503,{ok:false,error:'접수 환경을 확인할 수 없습니다.'});
    try{
      if(await limited(ip,env))return reply(429,{ok:false,error:'잠시 후 다시 접수해 주세요.'});
      const c=checked.cleaned;const reference='EP-'+crypto.randomUUID();const now=new Date();const expiry=new Date(now.getTime()+retention*86400000).toISOString();
      await env.DB.prepare(`INSERT INTO inquiries (id, created_at, expires_at, province, city, facility, request_type, start_preference, work_type, capacity, contact_name, phone, email, message, entry_path, attribution_json, privacy_version, privacy_consent, transfer_consent, status, service, inspection_type, shutdown_possible) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`).bind(reference,now.toISOString(),expiry,c.province,c.city,c.facility,c.requestType,c.start,c.workType,c.capacity,c.contactName,c.phone,c.email,c.message,c.entryPath,JSON.stringify(c.attribution),env.PRIVACY_VERSION,1,body.transferConsent===true?1:0,'new',c.service,c.inspectionType,c.shutdownPossible).run();
      ctx.waitUntil(notify(reference,c,env));
      return reply(201,{ok:true,reference});
    }catch{return reply(503,{ok:false,error:'현재 접수를 완료할 수 없습니다. 잠시 후 다시 시도해 주세요.'});}
  },
  async scheduled(_event,env,ctx) {
    if(!env.DB)return;
    const now=new Date().toISOString();
    ctx.waitUntil(env.DB.batch([
      env.DB.prepare('DELETE FROM inquiries WHERE expires_at <= ?').bind(now),
      env.DB.prepare('DELETE FROM request_limits WHERE expires_at <= ?').bind(now)
    ]));
  }
};
