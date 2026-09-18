/* No external dependency. Review mode never submits or persists personal data. */
(() => {
  'use strict';
  const SITE = window.SITE;
  const BASE = SITE.base || '';
  let step = 0;
  let submitting = false;
  let renderedRoute = '';
  const trackedKeys = ['utm_source','utm_medium','utm_campaign','utm_content','utm_term','n_keyword','n_keyword_id','n_ad_group','n_ad','gclid'];
  const labels = {
    service: {onsite:'상주 위탁',duty:'직무고시 대행',both:'상주 위탁 + 직무고시'},
    inspectionType: {discuss:'범위부터 상담',periodic:'정기 점검',annual:'연차 점검',specific:'특정 항목 점검·측정'},
    facility: {factory:'공장',logistics:'물류시설',building:'업무·상업용 건물',construction:'건설현장',other:'기타 시설'},
    requestType: {new:'신규 상주선임',change:'기존 위탁업체 변경',transition:'직접고용 → 위탁',consult:'조건부터 상담'},
    start: {discuss:'일정 협의',soon:'가능한 빠르게 검토',month:'약 한 달 이내 희망',later:'이후 일정 검토'}
  };
  let attribution = {};
  let entryPath = '';
  function loc() {
    let path = location.pathname;
    if (BASE && path.startsWith(BASE)) path = path.slice(BASE.length) || '/';
    const input = window.__OFFLINE__ ? (location.hash.startsWith('#/') ? location.hash.slice(1) : '/') : path + location.search;
    return new URL(input, 'https://review.invalid');
  }
  function captureAttribution() {
    const u = loc();
    trackedKeys.forEach(k => {const v=u.searchParams.get(k); if (v) attribution[k]=v.slice(0,200);});
    const entry = u.searchParams.get('entry_path');
    entryPath = entry && /^\/[a-z0-9\-/]*$/.test(entry) ? entry : (entryPath || u.pathname);
  }
  function enriched(path) {
    const u = new URL(path,'https://review.invalid');
    Object.entries(attribution).forEach(([k,v])=>{if(!u.searchParams.has(k))u.searchParams.set(k,v);});
    if(u.pathname==='/quote/' && entryPath)u.searchParams.set('entry_path',entryPath);
    return u.pathname+u.search+u.hash;
  }
  function renderOffline() {
    if (!window.__OFFLINE__) return;
    const u=loc();const page=window.__PAGES__[u.pathname] || window.__PAGES__['/404.html'];
    if (renderedRoute === u.pathname+u.search) return;
    document.body.innerHTML=page.html;
    document.title=page.title;
    renderedRoute=u.pathname+u.search;
    init();
    window.scrollTo(0,0);
  }
  function updateCities(provinceSlug, selected='') {
    const select=document.getElementById('city');if(!select)return;
    const province=SITE.regions.find(r=>r.slug===provinceSlug);
    select.replaceChildren();
    function option(value,text) {const n=document.createElement('option');n.value=value;n.textContent=text;select.appendChild(n);}
    if(!province){option('','권역 먼저 선택');return;}
    option('','세부 지역 선택');
    province.cities.forEach(c=>option(c.slug,c.name));
    option('other',province.cities.length ? '목록 외 시·군·구 / 후속 확인' : province.name+' 내 세부 지역 / 후속 확인');
    select.value=selected || (province.cities.length ? '' : 'other');
    if(!select.value && selected)select.value='other';
  }
  function init() {
    step=0;submitting=false;captureAttribution();
    document.body.classList.toggle('quote-page',loc().pathname==='/quote/');
    const form=document.getElementById('inquiry-form');
    if(form){
      form.reset();
      const u=loc();const province=SITE.regions.find(r=>r.slug===u.searchParams.get('province'));
      const service=u.searchParams.get('service');
      if(['onsite','duty','both'].includes(service))form.elements.service.value=service;
      const type=u.searchParams.get('type');
      if(['new','change','transition','consult'].includes(type))form.elements.requestType.value=type;
      syncServiceFields();
      if(province){form.elements.province.value=province.slug;updateCities(province.slug,u.searchParams.get('city')||'');}
      showStep(0,false);
    }
    document.querySelectorAll('a[data-route]').forEach(link=>{
      const target=link.dataset.route;
      link.href=window.__OFFLINE__?'#'+enriched(target):BASE+enriched(target);
    });
    setRegionService(loc().searchParams.get('service')==='duty'?'duty':'onsite');
    document.querySelectorAll('.site-nav a').forEach(a=>{const active=loc().pathname.startsWith(new URL(a.dataset.route,'https://review.invalid').pathname);a.classList.toggle('is-current',active);if(active)a.setAttribute('aria-current','page');});
    initReveal();initHeroMotion();
    const count=document.querySelectorAll('.search-city-list [data-search]').length;
    const result=document.querySelector('.search-result');if(result)result.textContent=`${count}개 세부 지역 · 가나다순`;
  }

  function initReveal() {
    const targets=document.querySelectorAll('.section-head,.path-card,.primary-service,.secondary-service,.feature,.icon-item,.hero-photo,.process-step,.guide-card,.scope-row,.stateless-card,.scope-service-card,.inspection-board,.duty-feature-grid>div:first-child,.faq-intro,.faqs,.cta-block,.region-directory,.content-block,.local-banner');
    targets.forEach(el=>el.classList.add('reveal'));
    if(!('IntersectionObserver' in window)||matchMedia('(prefers-reduced-motion: reduce)').matches){targets.forEach(el=>el.classList.add('is-visible'));return;}
    const io=new IntersectionObserver(entries=>{entries.forEach(entry=>{if(entry.isIntersecting){entry.target.classList.add('is-visible');io.unobserve(entry.target);}});},{rootMargin:'0px 0px -8% 0px',threshold:.08});
    targets.forEach((el,i)=>{el.style.setProperty('--reveal-delay',`${Math.min((i%4)*70,210)}ms`);io.observe(el);});
    // 화면 안에 이미 있는 요소는 즉시 표시한다.
    requestAnimationFrame(()=>targets.forEach(el=>{const r=el.getBoundingClientRect();if(r.top<innerHeight&&r.bottom>0)el.classList.add('is-visible');}));
  }
  function initHeroMotion() {
    const hero=document.querySelector('.hero-light');if(!hero)return;
    if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;
    let raf=0,mx=0,my=0;
    const apply=()=>{raf=0;hero.style.setProperty('--mx',mx.toFixed(3));hero.style.setProperty('--my',my.toFixed(3));hero.style.setProperty('--sy',String(Math.min(scrollY,600)));};
    const schedule=()=>{if(!raf)raf=requestAnimationFrame(apply);};
    window.addEventListener('scroll',schedule,{passive:true});apply();
  }
  function onScroll() {
    const header=document.querySelector('.site-header');if(!header)return;
    header.classList.toggle('is-scrolled',scrollY>24);
  }
  function setRegionService(service) {
    const duty=service==='duty';
    document.querySelectorAll('[data-region-service]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.regionService===service)));
    document.querySelectorAll('a[data-region-route]').forEach(link=>{
      const target=duty?link.dataset.dutyRoute:link.dataset.regionRoute;
      link.dataset.route=target;
      link.href=window.__OFFLINE__?'#'+enriched(target):BASE+enriched(target);
    });
  }
  function syncServiceFields() {
    const f=document.getElementById('inquiry-form');if(!f)return;
    const service=f.elements.service.value;
    document.querySelectorAll('[data-service-fields]').forEach(group=>{
      const visible=group.dataset.serviceFields==='onsite'?service!=='duty':['duty','both'].includes(service);
      group.hidden=!visible;
      group.querySelectorAll('input,select,textarea').forEach(field=>field.disabled=!visible);
    });
    const title=document.getElementById('condition-title');
    if(title)title.textContent=service==='duty'?'어떤 점검이 필요한가요?':service==='both'?'운영과 점검 조건을 알려주세요.':'어떤 운영을 원하시나요?';
  }

  function setError(message,field) {
    const error=document.querySelector('.form-error');if(error)error.textContent=message;
    if(field)field.focus();
    return false;
  }
  function validate(which) {
    const f=document.getElementById('inquiry-form');if(!f)return false;
    if(which===0){
      if(!['onsite','duty','both'].includes(f.elements.service.value))return setError('필요한 서비스를 선택해 주세요.',f.querySelector('[name=service]'));
      if(!SITE.regions.some(r=>r.slug===f.elements.province.value))return setError('현장 권역을 선택해 주세요.',f.elements.province);
      if(!f.elements.city.value)return setError('세부 지역 또는 후속 확인 항목을 선택해 주세요.',f.elements.city);
      if(!f.elements.facility.value)return setError('시설 유형을 선택해 주세요.',f.querySelector('[name=facility]'));
    }
    if(which===1 && f.elements.service.value!=='duty' && !f.elements.requestType.value)return setError('상주 위탁 문의 유형을 선택해 주세요.',f.querySelector('[name=requestType]'));
    if(which===2){
      const p=f.elements.phone.value.trim();
      if(!/^[+0-9\s()\-]+$/.test(p)||p.replace(/\D/g,'').length<9||p.replace(/\D/g,'').length>13)return setError('연락 가능한 전화번호를 확인해 주세요.',f.elements.phone);
      if(f.elements.email.value && !f.elements.email.checkValidity())return setError('이메일 형식을 확인해 주세요.',f.elements.email);
      if(!f.elements.privacyConsent.checked)return setError(SITE.mode==='preview'?'검토용 화면 안내를 확인해 주세요.':'개인정보 수집·이용 안내를 확인해 주세요.',f.elements.privacyConsent);
      if(SITE.mode!=='preview' && SITE.thirdPartyTransfer && !f.elements.transferConsent?.checked)return setError('제3자 제공 내용을 확인해 주세요.',f.elements.transferConsent);
    }
    setError('');return true;
  }
  function showStep(next,focus=true) {
    step=next;
    document.querySelectorAll('.form-step').forEach(s=>{s.hidden=Number(s.dataset.step)!==step;});
    document.querySelectorAll('.step-indicator').forEach(s=>{const n=Number(s.dataset.stepIndicator);s.classList.toggle('active',n===step);s.classList.toggle('done',n<step);if(n===step)s.setAttribute('aria-current','step');else s.removeAttribute('aria-current');});
    const prev=document.querySelector('.form-actions .prev'),nextBtn=document.querySelector('.form-actions .next'),submit=document.querySelector('.form-actions .submit');
    if(!prev)return;prev.hidden=step===0;nextBtn.hidden=step===2;submit.hidden=step!==2;
    // CSS display values must not override the hidden attribute.
    prev.style.display=prev.hidden?'none':'';nextBtn.style.display=nextBtn.hidden?'none':'';submit.style.display=submit.hidden?'none':'';
    setError('');
    if(step===2)updateSummary();
    if(focus){const legend=document.querySelector(`[data-step="${step}"] legend`);legend.tabIndex=-1;legend.focus({preventScroll:true});if(innerWidth<700)legend.scrollIntoView({block:'center',behavior:'smooth'});}
  }
  function updateSummary() {
    const f=document.getElementById('inquiry-form'),dl=document.getElementById('inquiry-summary');if(!f||!dl)return;
    const r=SITE.regions.find(r=>r.slug===f.elements.province.value);
    const city=r?.cities.find(c=>c.slug===f.elements.city.value)?.name || '세부지역 후속 확인';
    const rows=[['서비스',labels.service[f.elements.service.value]||''],['현장',`${r?.name||''} · ${city}`],['시설',labels.facility[f.elements.facility.value]||''],['문의',f.elements.service.value==='duty'?(labels.inspectionType[f.elements.inspectionType.value]||'점검 범위 협의'):(labels.requestType[f.elements.requestType.value]||'')],['시작 시점',labels.start[f.elements.start.value]||'']];
    if(f.elements.service.value==='both')rows.splice(4,0,['점검',labels.inspectionType[f.elements.inspectionType.value]||'범위부터 상담']);
    dl.replaceChildren();rows.forEach(([key,value])=>{const div=document.createElement('div'),dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=key;dd.textContent=value;div.append(dt,dd);dl.append(div);});
  }
  function result(preview,reference='') {
    const form=document.getElementById('inquiry-form'),box=document.querySelector('.form-result');
    form.reset();form.hidden=true;form.style.display='none';document.querySelector('.form-steps').hidden=true;document.querySelector('.form-steps').style.display='none';
    box.hidden=false;box.replaceChildren();
    const icon=document.createElement('div');icon.className='result-icon';icon.textContent='✓';
    const title=document.createElement('h2');title.textContent=preview?'입력 흐름을 확인했습니다.':'상담 문의가 접수되었습니다.';
    const desc=document.createElement('p');desc.textContent=preview?'현재는 검토용 화면입니다. 실제 상담 접수·개인정보 저장·문자·이메일 발송은 이루어지지 않았습니다.':'접수번호: '+reference+' · 상담 검토를 위한 접수이며, 계약이나 배치를 확정한 것은 아닙니다.';
    const reset=document.createElement('button');reset.type='button';reset.className='btn';reset.dataset.resetForm='true';reset.textContent=preview?'처음부터 다시 확인':'새 문의 작성';
    box.append(icon,title,desc,reset);box.tabIndex=-1;box.focus();
  }
  async function submitForm(event) {
    event.preventDefault();if(submitting)return;
    for(let n=0;n<3;n++)if(!validate(n)){if(step!==n){showStep(n);validate(n);}return;}
    if(SITE.mode==='preview'||window.__OFFLINE__){result(true);return;}
    if(!SITE.form.enabled){setError('현재 온라인 접수 준비 중입니다. 운영 안내의 공식 연락처를 확인해 주세요.');return;}
    const form=event.target;const fd=new FormData(form);
    const allowed=['service','inspectionType','shutdownPossible','province','city','facility','requestType','start','workType','capacity','contactName','phone','email','message','website'];
    const payload={};allowed.forEach(k=>payload[k]=String(fd.get(k)||'').trim());
    if(payload.service==='duty'){payload.requestType='consult';payload.workType='discuss';}
    if(payload.service==='onsite'){payload.inspectionType='discuss';payload.shutdownPossible='unknown';}
    payload.privacyConsent=fd.get('privacyConsent')==='yes';payload.transferConsent=fd.get('transferConsent')==='yes';
    payload.privacyVersion=SITE.privacyVersion;payload.turnstileToken=String(fd.get('cf-turnstile-response')||'');
    payload.attribution={...attribution};payload.entryPath=entryPath||'/';
    if(SITE.form.turnstileSiteKey && !payload.turnstileToken){setError('보안 확인을 완료해 주세요.');return;}
    submitting=true;const button=form.querySelector('.submit');button.disabled=true;button.textContent='접수 중…';
    try{
      const response=await fetch(BASE+SITE.form.endpoint,{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(payload)});
      const data=await response.json();
      if(!response.ok || data.ok!==true || !data.reference)throw new Error(data.error||'접수에 실패했습니다. 잠시 후 다시 시도해 주세요.');
      result(false,data.reference);
    }catch(error){setError(error.message||'네트워크 연결을 확인해 주세요.');if(window.turnstile)window.turnstile.reset();}
    finally{submitting=false;button.disabled=false;button.textContent='비공개 상담 접수 ↗';}
  }
  document.addEventListener('click',event=>{
    const menu=event.target.closest('.menu-toggle');if(menu){const header=document.querySelector('.site-header');const open=header.classList.toggle('menu-open');menu.setAttribute('aria-expanded',String(open));menu.setAttribute('aria-label',open?'메뉴 닫기':'메뉴 열기');return;}
    const serviceButton=event.target.closest('[data-region-service]');if(serviceButton){setRegionService(serviceButton.dataset.regionService);return;}
    const tab=event.target.closest('[data-tab]');if(tab){
      document.querySelectorAll('[data-tab]').forEach(b=>{b.setAttribute('aria-selected',String(b===tab));b.tabIndex=b===tab?0:-1;});
      document.querySelectorAll('.region-panel').forEach(p=>p.hidden=p.id!=='panel-'+tab.dataset.tab);return;
    }
    if(event.target.closest('.form-actions .next')){if(validate(step))showStep(step+1);return;}
    if(event.target.closest('.form-actions .prev')){showStep(step-1);return;}
    if(event.target.closest('[data-reset-form]')){
      if(window.__OFFLINE__){renderedRoute='';renderOffline();}else location.reload();return;
    }
    const link=event.target.closest('a[data-route]');
    if(link && window.__OFFLINE__ && !event.ctrlKey && !event.metaKey && !event.shiftKey){
      event.preventDefault();const target=enriched(link.dataset.route);const old=location.hash;location.hash='#'+target;
      if(old===location.hash){document.querySelector('.site-header')?.classList.remove('menu-open');window.scrollTo(0,0);}
    }
  });
  document.addEventListener('keydown',event=>{
    const t=event.target.closest('[role=tab]');if(t && ['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){
      event.preventDefault();const tabs=[...document.querySelectorAll('[role=tab]')];const i=tabs.indexOf(t);let next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(i+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;tabs[next].click();tabs[next].focus();
    }
    if(event.key==='Escape'){document.querySelector('.site-header')?.classList.remove('menu-open');document.querySelector('.menu-toggle')?.setAttribute('aria-expanded','false');}
  });
  document.addEventListener('change',event=>{if(event.target.id==='province')updateCities(event.target.value);if(event.target.name==='service')syncServiceFields();});
  document.addEventListener('input',event=>{
    if(event.target.id!=='region-search')return;
    const search=event.target.value.replace(/\s/g,'').toLowerCase();let count=0;
    document.querySelectorAll('[data-search]').forEach(a=>{const ok=a.dataset.search.replace(/\s/g,'').toLowerCase().includes(search);a.hidden=!ok;if(ok)count++;});
    const result=document.querySelector('.search-result');result.textContent=count?`${count}개 상세 안내`:'해당 상세 페이지가 없습니다. 위의 권역 안내에서 상담할 수 있습니다.';
  });
  document.addEventListener('submit',event=>{if(event.target.id==='inquiry-form')submitForm(event);});
  window.addEventListener('scroll',onScroll,{passive:true});onScroll();
  window.addEventListener('hashchange',renderOffline);
  if(window.__OFFLINE__)renderOffline();else init();
})();
