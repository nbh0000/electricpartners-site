#!/usr/bin/env python3
"""Build static HTML and an offline, single-file review copy. Standard library only."""
from __future__ import annotations
import argparse, html, json, os, re, shutil
from pathlib import Path
from urllib.parse import quote, urlparse
from xml.sax.saxutils import escape as xml_escape

ROOT=Path(__file__).resolve().parents[1]
CONFIG=json.loads((ROOT/'config/site.json').read_text('utf-8'))
REGIONS=json.loads((ROOT/'content/regions.json').read_text('utf-8'))
PAGES={}
EXTRA={}  # path -> {'faqs':[...],'service':{...},'keywords':'...'}
E=lambda x: html.escape(str(x),quote=True)
BRAND=CONFIG['brand']
BRAND_EN=CONFIG.get('brandEnglish','ELECTRIC MANAGE PARTNERS')
PREVIEW=CONFIG['mode']!='production'
KEEA='https://www.keea.or.kr/head/work/getWWO04R01R01.do'
BASE=os.environ.get('BASE_PATH','').rstrip('/')  # GitHub Pages 등 하위 경로 배포용
SEO=CONFIG['seo']
ORIGIN=CONFIG['origin'].rstrip('/')
INDEXING=bool(SEO.get('indexing',not PREVIEW)) and bool(ORIGIN)  # 검색엔진 색인 허용 여부(문의 접수 활성화와 별개)
AREA='서울 · 인천 · 경기 · 충북 · 충남'
ARROW='<span class="arrow" aria-hidden="true">→</span>'


def a(path: str, text: str, cls: str='', **attrs)->str:
    extra=' '.join(f'{k.replace("_","-")}="{E(v)}"' for k,v in attrs.items())
    return f'<a href="{E(BASE+path)}" data-route="{E(path)}" class="{E(cls)}" {extra}>{text}</a>'

def btn(path:str,text:str='상주 위탁 상담',cls:str='',**attrs)->str:
    return a(path,E(text)+ARROW,'btn '+cls,**attrs)

def logo_svg()->str:
    # 기존 브랜드 심볼(두 기둥 + 라임 바). 다크 배경에서는 CSS로 기둥 색을 흰색으로 바꾼다.
    return ('<svg viewBox="0 0 40 42" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
            '<path class="mark-pillar" fill="#15352D" d="M3 13 15 9 15 35 3 39zM20 6 32 2 32 35 20 39z"/>'
            '<path fill="#B7E64A" d="M12 18 28 13 28 22 12 27z"/></svg>')


def brand()->str:
    return a('/', '<span class="brand-mark">'+logo_svg()+'</span><span class="brand-name">'+E(BRAND)+'<span class="brand-small">'+E(BRAND_EN)+'</span></span>', 'brand', aria_label=BRAND+' 홈')


NAV=[('/services/onsite/','상주 위탁'),('/services/duty/','직무고시 대행'),('/regions/','서비스 지역'),('/guide/cost/','견적 가이드'),('/about/','회사 소개')]

def header(light=False)->str:
    return f'''<a class="skip" href="#main">본문 바로가기</a>
    <header class="site-header{' light' if light else ''}"><div class="wrap header-inner">{brand()}
    <nav class="site-nav" id="site-nav" aria-label="주요 메뉴">{''.join(a(p,t) for p,t in NAV)}</nav>
    {btn('/quote/','견적 문의','header-cta')}<button type="button" class="menu-toggle" aria-label="메뉴 열기" aria-controls="site-nav" aria-expanded="false"><span></span><span></span></button></div></header>'''


def footer()->str:
    o=CONFIG['operator']
    rows=[('상호',o['name']),('대표',o['representative']),('사업자등록번호',o['registrationNumber'])]
    if CONFIG['phone']:rows.append(('상담전화',CONFIG['phone']))
    if CONFIG['email']:rows.append(('이메일',CONFIG['email']))
    if o['publicAddress']:rows.append(('주소',o['publicAddress']))
    info=''.join(f'<div><dt>{E(k)}</dt><dd>{E(v)}</dd></div>' for k,v in rows)
    regions=''.join(a(region_url(r),E(r['name'])) for r in REGIONS)
    return f'''<div class="current current-footer" aria-hidden="true"></div><footer class="footer"><div class="wrap"><div class="footer-top"><div>{brand()}<p class="footer-intro">전기안전관리자 상주선임·위탁 전문.<br>{AREA} 현장의 전기안전관리를 책임집니다.</p></div>
    <div class="footer-cols"><div class="footer-col"><b>서비스</b>{a('/services/onsite/','전기안전관리자 상주 위탁')}{a('/services/duty/','직무고시 대행')}{a('/quote/','견적 문의')}</div><div class="footer-col"><b>서비스 지역</b><div class="footer-inline">{regions}{a('/regions/','전체 보기')}</div></div><div class="footer-col"><b>안내</b>{a('/guide/cost/','상주 위탁 견적 가이드')}{a('/guide/change/','위탁업체 변경 안내')}{a('/guide/direct-hire/','직접고용 → 위탁 전환')}{a('/about/','회사 소개')}{a('/privacy/','개인정보처리방침')}</div></div></div>
    <div class="business-info"><dl>{info}</dl><p>지역별 안내는 서비스 제공 지역의 구분이며, 각 지역의 지사·영업소 소재지를 뜻하지 않습니다.</p></div>
    <div class="footer-bottom"><span>© {E(BRAND_EN)}. ALL RIGHTS RESERVED.</span><span>SEOUL · INCHEON · GYEONGGI · CHUNGBUK · CHUNGNAM</span></div></div></footer>
    <div class="mobile-cta"><span>전기안전관리자 상주 위탁<br>지역별 견적 문의</span>{btn('/quote/','견적 문의')}</div>'''


def breadcrumb(items:list[tuple[str,str]])->str:
    return '<nav class="breadcrumb" aria-label="현재 위치">'+a('/','홈')+''.join('<span aria-hidden="true">/</span>'+a(p,E(t)) for p,t in items)+'</nav>'

def eyebrow(text:str)->str:return '<span class="eyebrow">'+E(text)+'</span>'

def cta(province='',city='',service='')->str:
    title='우리 현장의 전기안전관리,<br>지금 견적을 문의하세요.'
    if service=='duty':title='직무고시 점검,<br>일정과 범위부터 상담하세요.'
    return f'''<section class="cta-section bg-about"><div class="wrap"><div class="cta-block"><div><h2>{title}</h2><p>현장 지역과 시설 유형만 알려주셔도 상담을 시작할 수 있습니다. 문의 내용은 비공개로 접수됩니다.</p></div>{btn(quote_url(province,city,service),'견적 문의하기','btn-white')}</div></div></section>'''


FAQS=[
 ('전기안전관리자 상주 위탁이란 무엇인가요?','전기안전관리자 선임 의무가 있는 사업장에 자격을 갖춘 안전관리자를 상주 배치하고, 설비 점검·기록·보고 등 안전관리 업무를 위탁 운영하는 방식입니다. 직접 채용 없이 법정 선임과 현장 관리를 함께 해결할 수 있습니다.'),
 ('견적은 어떻게 산정되나요?','수전·발전설비 용량, 필요 인원과 근무형태, 포함 업무 범위를 기준으로 산정합니다. 현장 조건을 확인한 뒤 명확한 견적을 안내해 드립니다.'),
 ('설비용량을 정확히 몰라도 문의할 수 있나요?','네. 문의 시 ‘확인 필요’로 남겨주시면 됩니다. 현장 지역과 시설 유형만으로 상담을 시작하고, 필요한 자료는 이후 함께 정리합니다.'),
 ('기존 위탁업체에서 변경할 수 있나요?','가능합니다. 기존 계약 종료 시점과 인수인계 일정을 확인해 관리 공백 없이 전환할 수 있도록 지원합니다.'),
 ('직무고시 점검만 따로 맡길 수 있나요?','가능합니다. 상주 위탁과 별도로 직무고시 점검·측정 및 결과 정리만 의뢰하실 수 있습니다.')]

def faq(items=None)->str:
    return '<div class="faqs">'+''.join(f'<details><summary>{E(q)}</summary><p>{E(ans)}</p></details>' for q,ans in (items or FAQS))+'</div>'

def process()->str:
    steps=[('문의 접수','서비스와 현장 지역, 시설 유형을 알려주세요. 비공개로 접수됩니다.'),('현장 조건 확인','설비 용량, 필요 인원, 근무형태 등 현장 조건을 확인합니다.'),('견적·범위 안내','포함 업무와 비용을 명확히 정리한 견적을 안내합니다.'),('계약·선임·착수','계약 후 인수인계와 선임 절차를 거쳐 상주 관리를 시작합니다.')]
    return '<div class="process-grid">'+''.join(f'<div class="process-step"><span class="num">STEP 0{i}</span><h3>{E(t)}</h3><p>{E(d)}</p></div>' for i,(t,d) in enumerate(steps,1))+'</div>'

def guides()->str:
    data=[('/guide/cost/','COST GUIDE','상주 위탁 견적,<br>무엇이 포함되나요?','견적 항목과 산정 기준'),('/guide/direct-hire/','TRANSITION','직접고용에서<br>위탁으로 전환하기','비교할 운영 조건'),('/guide/change/','HANDOVER','위탁업체 변경,<br>공백 없이 준비하기','일정·기록·인수인계')]
    return '<div class="guide-grid">'+''.join(a(path,f'<span class="tag">{tag}</span><h3>{title}</h3><div><span>{desc}</span><span class="arrow" aria-hidden="true">→</span></div>','guide-card') for path,tag,title,desc in data)+'</div>'

def region_tabs()->str:
    tabs='<div class="region-tabs" role="tablist" aria-label="서비스 권역">'+''.join(f'<button class="region-tab" type="button" role="tab" id="tab-{r["slug"]}" aria-controls="panel-{r["slug"]}" aria-selected="{str(r["slug"]=="gyeonggi").lower()}" tabindex="{0 if r["slug"]=="gyeonggi" else -1}" data-tab="{r["slug"]}">{E(r["name"])}</button>' for r in REGIONS)+'</div>'
    panels=''
    for r in REGIONS:
        links=''.join(region_link(r,c) for c in r['cities'])
        panels+=f'''<div class="region-panel" id="panel-{r['slug']}" role="tabpanel" aria-labelledby="tab-{r['slug']}" {'' if r['slug']=='gyeonggi' else 'hidden'}>
        <div class="region-panel-intro"><span class="region-overline">{r['slug'].upper()}</span><h3>{E(r['fullName'])}</h3><p>현장이 위치한 지역을 선택하세요.<br>세부 지역은 가나다순입니다.</p>{region_link(r,label=E(r['name'])+' 전체 안내 <span aria-hidden="true">→</span>',cls='text-link')}<div class="region-count">{len(r['cities']):02d}<span>개 세부 지역</span></div></div><div class="region-links">{links}</div></div>'''
    return '<div class="region-directory"><div class="region-toolbar">'+tabs+service_switch()+'</div>'+panels+'</div>'


def hero_visual()->str:
    cards=[('ON-SITE','전기안전관리자 상주 배치','법정 선임 · 일상 점검 · 기록 관리'),('INSPECTION','직무고시 점검 대행','측정 · 점검 · 결과서 정리'),('AREA','서울 · 인천 · 경기 · 충북 · 충남','지역별 전담 상담 · 비공개 견적')]
    return '<div class="hero-visual"><div class="hero-cards">'+''.join(f'<div class="hero-card"><small>{t}</small><b>{E(h)}</b><span>{E(d)}</span></div>' for t,h,d in cards)+'</div></div>'


def circuit_svg()->str:
    # 회로 트레이스 + 흐르는 전류 스파크 + 파형 (장식용)
    traces=['M-20 28H120L150 58H330','M1300 118H1010L968 160H700','M1300 40H1120L1080 80H900','M640 206H780L830 156H900','M820 216H1040L1080 186H1300','M560 22H700L740 52H1300']
    wave='M900 100h34l6-22 7 44 7-44 7 44 7-22h30l6-22 7 44 7-44 7 44 7-22h34'
    nodes=[(120,28),(330,58),(1010,118),(700,160),(1120,40),(900,80),(900,156),(1040,216),(700,22),(1160,100)]
    base=''.join(f'<path d="{d}"/>' for d in traces)
    spark=''.join(f'<path d="{d}" style="--len:{1200+i*137};--dur:{4.5+i*.9}s;--delay:{-i*1.3}s"/>' for i,d in enumerate(traces))
    dots=''.join(f'<g transform="translate({x},{y})"><circle r="9" class="halo"/><circle r="3.5" class="node"/></g>' for x,y in nodes)
    comps='<rect x="1180" y="177" width="46" height="18" rx="3"/><rect x="960" y="151" width="18" height="28" rx="3"/><rect x="1240" y="31" width="30" height="18" rx="3"/>'
    return f'<svg viewBox="0 0 1280 220" preserveAspectRatio="xMidYMid slice"><defs><filter id="glow" x="-20%" y="-200%" width="140%" height="500%"><feGaussianBlur stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs><g class="trace">{base}{comps}<path d="{wave}" class="wave"/></g><g class="spark" filter="url(#glow)">{spark}<path d="{wave}" class="wave-spark" style="--len:520;--dur:3s;--delay:0s"/></g><g class="nodes">{dots}</g></svg>'

def home()->str:
    paths=[('01 / NEW','신규 상주선임','새로 전기안전관리자를 선임해야 하는 사업장. 설비 조건에 맞는 자격·인원을 검토합니다.','new'),('02 / CHANGE','위탁업체 변경','기존 위탁업체의 관리에 아쉬움이 있다면. 인수인계까지 공백 없이 전환합니다.','change'),('03 / TRANSITION','직접고용 → 위탁 전환','직접 채용한 관리자의 퇴사·결원 부담을 줄이고 안정적인 상주 운영으로 전환합니다.','transition')]
    path_cards=''.join(a(quote_url(service='onsite')+'&type='+t,f'<div><span class="num">{n}</span><h3>{E(title)}</h3><p>{E(d)}</p></div><span class="circle" aria-hidden="true">→</span>','path-card') for n,title,d,t in paths)
    icons={'person':'<path d="M24 26a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM10 40c0-7 6.3-11 14-11s14 4 14 11"/>','scope':'<rect x="8" y="10" width="32" height="28" rx="4"/><path d="M8 20h32M16 27h10M16 32h16"/>','handover':'<circle cx="24" cy="24" r="19"/><path d="M13 21h16l-4-4M35 27H19l4 4"/>','lock':'<rect x="10" y="20" width="28" height="22" rx="4"/><path d="M16 20v-6a8 8 0 0 1 16 0v6M24 29v5"/>'}
    features=[('person','전담 상주 관리','자격을 갖춘 전기안전관리자가 현장에 상주하며 설비 점검·기록·법정 업무를 책임집니다.'),('scope','명확한 업무 범위','상주 업무, 지원 업무, 별도 점검 업무를 계약 단계에서 분명하게 구분합니다.'),('handover','공백 없는 인수인계','업체 변경·직접고용 전환 시 기존 기록과 일정을 이어받아 관리 공백을 막습니다.'),('lock','비공개 견적 상담','문의는 공개 게시판이 아닌 비공개로 접수되며, 현장 지역과 서비스에 맞춰 안내합니다.')]
    feature_html=''.join(f'<div class="icon-item"><span class="icon" aria-hidden="true"><svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{icons[k]}</svg></span><h3>{E(t)}</h3><p>{E(d)}</p></div>' for k,t,d in features)
    return f'''<main id="main">
    <section class="hero-light"><div class="wrap">
      <div class="circuit" aria-hidden="true">{circuit_svg()}</div>
      <div class="ghost" aria-hidden="true">ELECTRIC SAFETY PARTNERS</div>
      <div class="hero-light-head"><div>
        <h1 class="visually-hidden">전기안전관리자 상주선임·위탁 전문 전기관리파트너스</h1>
        <div class="hero-chips"><span class="chip" style="--i:0">신규 선임</span><span class="chip" style="--i:1">위탁업체 변경</span><span class="chip" style="--i:2">직접고용 전환</span><span class="chip" style="--i:3">{AREA}</span></div>
      </div></div>
      <div class="hero-photo bg-hero-green" role="img" aria-label="전기 배전반실 이미지"><div class="hero-photo-tag"><small>ON-SITE ELECTRICAL SAFETY</small><b>상주선임 · 위탁업체 변경 · 직접고용 전환</b></div><h2 class="visually-hidden">상담 유형별 안내</h2><div class="path-grid">{path_cards}</div></div>
    </div></section>
    <section class="section section-soft services-overview" id="services"><div class="wrap"><h2 class="visually-hidden">서비스 안내</h2>
    <div class="service-duo"><article class="primary-service"><div class="service-card-top"><span class="pill">01 / ON-SITE</span></div><h3>전기안전관리자<br>상주선임·위탁</h3><p>법정 선임 의무가 있는 사업장에 자격을 갖춘 안전관리자를 상주 배치하고, 설비 점검·기록·보고 업무를 위탁 운영합니다.</p><ul class="service-list"><li>신규 상주선임 · 위탁업체 변경 · 직접고용 전환</li><li>설비 조건에 맞는 자격·인원 검토</li><li>일상 점검, 기록 관리, 법정 보고 지원</li></ul><div class="service-card-bottom">{a('/services/onsite/','서비스 자세히 보기 <span aria-hidden="true">→</span>','text-link')}{btn(quote_url(service='onsite'),'견적 문의')}</div></article>
    <article class="secondary-service"><div class="service-card-top"><span class="pill">02 / INSPECTION</span></div><h3>직무고시<br>대행</h3><p>전기안전관리자 직무고시에 따른 점검·측정 항목을 대행하고, 결과 기록과 결과서 작성을 지원합니다.</p><ul class="service-list"><li>열화상 점검 · 절연·접지저항 측정</li><li>상주 위탁 없이 점검만 별도 의뢰 가능</li><li>측정 기록과 점검 결과서 작성·전달</li></ul><div class="service-card-bottom">{a('/services/duty/','서비스 자세히 보기 <span aria-hidden="true">→</span>','text-link')}{btn(quote_url(service='duty'),'견적 문의')}</div></article></div></div></section>
    <section class="section area-section" id="areas"><div class="wrap"><div class="section-head"><div>{eyebrow('SERVICE AREA')}<h2>어느 지역의 현장인가요?</h2></div><p>권역과 세부 지역을 선택하면<br>해당 지역의 안내 페이지로 이동합니다.</p></div>{region_tabs()}<p class="area-note">서비스 지역은 {AREA}입니다. 착수 일정은 현장 조건 확인 후 안내드립니다.</p></div></section>
{cta()}</main>'''


def all_regions()->str:
    citylinks=''.join(region_link(r,c,label=f'<span><small>{E(r["name"])}</small>{E(c["name"])}</span><span aria-hidden="true">→</span>',search=True) for r in REGIONS for c in r['cities'])
    return f'''<main id="main"><section class="page-hero bg-region"><div class="wrap">{breadcrumb([('/regions/','서비스 지역')])}{eyebrow('SERVICE AREA')}<h1>{AREA}<br>지역별 전기안전관리 안내</h1><p class="lead">현장이 위치한 지역을 선택하면 해당 지역의 전기안전관리자 상주 위탁·직무고시 대행 안내 페이지로 이동합니다.</p></div></section><section class="section-tight"><div class="wrap"><h2 class="visually-hidden">권역별 세부 지역 선택</h2>{region_tabs()}<p class="area-note">세부 지역은 가나다순입니다. 목록에 없는 지역은 견적 문의에서 ‘목록 외 지역’으로 선택해 주세요.</p></div></section><section class="section-tight section-soft"><div class="wrap"><div class="section-head"><div>{eyebrow('QUICK FIND')}<h2>지역명으로 바로 찾기</h2></div><p>서울·인천은 구·군, 경기·충북·충남은 시·군 기준입니다.</p></div><div class="region-search"><label class="field-label" for="region-search">지역명 검색</label><input id="region-search" type="search" placeholder="예: 안산, 강남구, 천안, 청주" autocomplete="off"><p class="search-result" aria-live="polite"></p></div><div class="search-city-list">{citylinks}</div></div></section>{cta()}</main>'''


def side_card(r,c=None,service='onsite')->str:
    label=c['name'] if c else r['name'];text='직무고시 대행' if service=='duty' else '상주선임·위탁'
    return f'''<aside class="side-card">{eyebrow('PRIVATE INQUIRY')}<h3>{E(label)} 현장<br>견적 문의</h3><dl><div><dt>서비스 지역</dt><dd>{E(r['fullName'])}{(' '+E(c['name'])) if c else ''}</dd></div><div><dt>서비스</dt><dd>{text}</dd></div><div><dt>접수 방식</dt><dd>비공개 접수</dd></div></dl>{btn(quote_url(r['slug'],c['slug'] if c else '',service),'이 지역 견적 문의')}<p class="caption">현장 지역과 시설 유형만 알려주셔도<br>상담을 시작할 수 있습니다.</p></aside>'''


def region_page(r,c=None,service='onsite')->str:
    is_duty=service=='duty';name=c['name'] if c else r['name'];label=(r['name']+' '+name) if c else r['name']
    path=region_url(r,c,service);other=region_url(r,c,'onsite' if is_duty else 'duty')
    service_name='직무고시 대행' if is_duty else '전기안전관리자 상주선임·위탁'
    crumb=[('/regions/','서비스 지역'),(region_url(r,None,service),r['name'])]+([(path,name)] if c else [])
    title=f'{E(label)}<br>직무고시 대행' if is_duty else f'{E(label)}<br>전기안전관리자 상주선임·위탁'
    if is_duty:
        intro=f'{label} 사업장의 직무고시 점검·측정을 대행합니다. 상주 위탁 계약 없이 점검·측정과 결과서 작성만 별도로 의뢰하실 수 있습니다.'
        heading=f'{name} 직무고시 대행, 이런 현장에 맞습니다';question='아래 항목 중 하나라도 해당된다면 상담을 시작하세요.'
        checks=['직무고시 점검 주기가 다가왔지만 측정 장비·인력이 부족한 사업장','열화상·절연·접지저항 등 측정 항목별 결과서가 필요한 사업장','상주 관리자는 있지만 정기 점검만 외부에 맡기고 싶은 사업장']
        focus=f'{name} 현장의 점검 항목과 일정을 먼저 확인합니다.'
        detail='수전·발전설비 구성과 요청 항목을 확인한 뒤, 정전 가능 시간과 작업 여건에 맞춰 점검 일정을 정합니다. 측정 결과는 기록과 결과서로 정리해 전달합니다.'
        rows=[('대상 설비·점검 범위 확인','수전·발전설비와 요청 항목, 정전·출입 조건을 확인합니다.'),('방문·측정 일정 협의','현장 가동 일정에 맞춰 점검 일정을 정합니다.'),('점검·측정·결과서 전달','측정 기록과 점검 결과서를 작성해 전달합니다.')]
        supporting='직무고시 대행은 전기안전관리자 선임을 대신하는 서비스가 아니며, 담당 안전관리자와 역할을 구분해 진행합니다.'
        guideslocal=[('/services/duty/','직무고시 대행 서비스 안내'),('/guide/duty-cost/','직무고시 대행 견적 기준'),(other,f'{name} 상주 위탁 안내')]
        faqs=[(f'{name} 사업장, 직무고시 점검만 의뢰할 수 있나요?','가능합니다. 상주 위탁과 별개로 대상 설비·점검 항목·일정을 확인한 뒤 진행합니다.'),('정전 없이도 점검이 가능한가요?','항목에 따라 다릅니다. 정전이 필요한 항목은 일정과 현장 협조 사항을 별도로 협의합니다.'),('결과서는 어떤 형태로 받나요?','측정 항목별 기록과 점검 결과서를 작성해 전달합니다. 작성 범위는 견적 단계에서 확인합니다.')]
    else:
        intro=f'{label} 사업장의 전기안전관리자 상주선임·위탁을 담당합니다. 신규 선임, 기존 위탁업체 변경, 직접고용에서 위탁으로의 전환 모두 상담하실 수 있습니다.'
        heading=f'{name} 상주 위탁, 이런 현장에 맞습니다';question='아래 항목 중 하나라도 해당된다면 상담을 시작하세요.'
        checks=['전기안전관리자를 새로 선임해야 하는 공장·물류시설·건물','기존 위탁업체의 관리 수준이나 대응에 아쉬움이 있는 사업장','직접 채용한 관리자의 퇴사·결원 부담을 줄이고 싶은 사업장']
        focus=f'{name} 현장의 설비와 운영 조건에 맞춰 상주 관리를 준비합니다.'
        detail='수전·발전설비 용량과 필요한 선임 자격, 근무형태를 확인해 상주 인원을 배치합니다. 일상 점검과 기록 관리, 법정 보고 지원까지 업무 범위를 명확히 정해 운영합니다.'
        rows=[('설비·자격 조건 확인','수전·발전설비와 필요한 선임 자격·인원을 확인합니다.'),('근무·업무 범위 확정','상주 운영, 보고·행정 지원, 별도 점검 업무를 구분해 정합니다.'),('인수인계·착수','기존 기록과 일정을 인계받아 관리 공백 없이 착수합니다.')]
        supporting='선임과 계약은 등록 범위와 현장 조건을 확인한 후 진행하며, 착수 일정은 상담 시 안내드립니다.'
        guideslocal=[('/services/onsite/','상주 위탁 서비스 안내'),('/guide/cost/','상주 위탁 견적 기준'),('/guide/change/','위탁업체 변경 절차'),(other,f'{name} 직무고시 대행 안내')]
        faqs=[(f'{name} 현장은 얼마나 빨리 착수할 수 있나요?','현장 조건과 필요 인원, 인수인계 준비 상태를 확인한 뒤 착수일을 안내합니다. 문의 시 희망 시작 시점을 알려주시면 일정에 반영합니다.'),('직무고시 점검도 함께 맡길 수 있나요?','가능합니다. 문의에서 ‘둘 다 상담’을 선택하시면 상주 운영과 별도 점검을 함께 안내합니다.'),FAQS[2]]
    sibling=''.join(a(region_url(r,cc,service),E(cc['name'])+' <span aria-hidden="true">→</span>') for cc in r['cities'] if not c or cc['slug']!=c['slug'])
    blockrows=''.join(f'<article class="scope-row"><span>0{i}</span><div><h3>{E(t)}</h3><p>{E(d)}</p></div></article>' for i,(t,d) in enumerate(rows,1))
    switch='<div class="page-service-links">'+a(region_url(r,c),'상주 위탁','active' if not is_duty else '')+a(region_url(r,c,'duty'),'직무고시 대행','active' if is_duty else '')+'</div>'
    notice=''
    if r['slug']=='gyeonggi' and c and c['slug']=='gwangju':notice='<p class="area-note">이 페이지는 광주광역시가 아닌 경기도 광주시 안내입니다.</p>'
    EXTRA[path]={'faqs':faqs}
    landmark=(c or {}).get('landmark')
    ctx_html='<section class="content-block"><h2>'+E(name)+' 지역 전기안전관리 여건</h2><p>'+E(r['context'])+'</p>'+(('<p>'+E(name)+'은(는) '+E(landmark)+' 등 '+('점검 대상 설비가 많은' if is_duty else '전기안전관리자 선임 의무 사업장이 많은')+' 곳으로, '+E(BRAND)+'는 '+E(name)+' 현장의 '+('직무고시 점검 일정과 정전 조건을 사전에 조율해 운영 중단을 최소화합니다.' if is_duty else '설비 규모와 근무 조건에 맞는 자격자를 배치하고 인수인계까지 책임집니다.')+'</p>') if landmark else '')+'</section>'
    return f'''<main id="main"><section class="page-hero bg-region"><div class="wrap">{breadcrumb(crumb)}{switch}<span class="pill">{E(r['fullName'])} · 서비스 지역</span><h1>{title}</h1><p class="lead">{E(intro)}</p><div class="hero-actions">{btn(quote_url(r['slug'],c['slug'] if c else '',service),'이 지역 견적 문의')}{a('/guide/duty-cost/' if is_duty else '/guide/cost/','견적 기준 보기 <span aria-hidden="true">→</span>','text-link')}</div>{notice}<div class="local-banner"><div><div class="kicker">{'INSPECTION' if is_duty else 'ON-SITE'} / {E(label)}</div><h2>{E(focus)}</h2><p>{'대상 설비 · 점검 항목 · 정전 조건 · 결과서' if is_duty else '필요 인원 · 근무형태 · 업무 범위 · 착수일'}</p></div><span class="pill">{service_name}</span></div></div></section>
    <section class="section-tight"><div class="wrap content-grid"><div><section class="content-block"><h2>{E(heading)}</h2><p>{E(question)}</p><ul class="check-list">{''.join('<li>'+E(q)+'</li>' for q in checks)}</ul></section>{ctx_html}<section class="content-block"><h2>{'점검부터 결과서까지 진행 순서' if is_duty else '상담부터 착수까지 진행 순서'}</h2><p>{detail}</p><div class="scope-list">{blockrows}</div><p class="source-note">{supporting}</p></section><section class="content-block"><h2>함께 보면 좋은 안내</h2><div class="related-links">{''.join(a(p,t+' <span aria-hidden="true">→</span>') for p,t in guideslocal)}</div></section><section class="content-block"><h2>{E(name)} 고객이 자주 묻는 질문</h2>{faq(faqs)}</section></div>{side_card(r,c,service)}</section>
    <section class="section-tight section-soft"><div class="wrap"><div class="section-head"><div>{eyebrow('SAME REGION')}<h2>{E(r['fullName'])}의 {'다른 지역' if c else '세부 지역'}</h2></div><p>가나다순으로 정리했습니다.</p></div><div class="search-city-list">{sibling}</div></div></section>{cta(r['slug'],c['slug'] if c else '',service)}</main>'''


def services()->str:
    cards=[('01 / NEW','신규 상주선임','전기안전관리자 선임 의무가 새로 생긴 사업장. 설비 조건에 맞는 자격·인원을 검토해 선임과 상주 운영을 준비합니다.'),('02 / TRANSITION','직접고용 → 위탁 전환','직접 채용한 관리자의 퇴사·결원 부담을 줄이고, 현재 업무를 그대로 이어받아 안정적인 위탁 운영으로 전환합니다.'),('03 / CHANGE','위탁업체 변경','기존 업체와의 계약 종료 시점에 맞춰 자료 인수인계와 새 운영 시작을 준비해 관리 공백을 막습니다.')]
    sc='<div class="stateless-grid">'+''.join(f'<article class="stateless-card"><b>{n}</b><h3>{t}</h3><p>{d}</p></article>' for n,t,d in cards)+'</div>'
    return f'''<main id="main"><section class="page-hero bg-onsite"><div class="wrap">{breadcrumb([('/services/onsite/','상주 위탁')])}{eyebrow('ON-SITE ELECTRICAL SAFETY MANAGEMENT')}<h1>전기안전관리자<br>상주선임·위탁</h1><p class="lead">법정 선임 의무가 있는 사업장에 자격을 갖춘 전기안전관리자를 상주 배치하고, 설비 점검·기록·보고 업무를 위탁 운영합니다. 직접 채용 없이 선임과 현장 관리를 함께 해결하세요.</p><div class="hero-actions">{btn(quote_url(service='onsite'),'상주 위탁 견적 문의')}{a('/regions/','서비스 지역 보기 <span aria-hidden="true">→</span>','text-link')}</div><div class="service-note-strip"><span>신규 상주선임</span><span>위탁업체 변경</span><span>직접고용 → 위탁 전환</span><span>{AREA}</span></div></div></section>
    <section class="section-tight"><div class="wrap"><div class="section-head"><div>{eyebrow('FOR WHOM')}<h2>이런 사업장에<br>상주 위탁이 필요합니다.</h2></div></div>{sc}</div></section>
    <section class="section-tight section-soft"><div class="wrap article"><div class="content-block"><h2>상주 위탁에 포함되는 업무</h2><p>현장에서 수행하는 전기안전관리 업무와 본사에서 지원하는 업무를 구분해 계약합니다. 실제 업무 범위는 현장 설비와 계약 내용에 따라 확정합니다.</p><ul class="check-list"><li>설비 조건에 맞는 선임 자격·필요 인력 검토 및 선임</li><li>상주 관리자의 일상 점검, 설비 순시, 기록 관리</li><li>법정 점검·보고 및 행정 업무 지원</li><li>장비 제공·교육·기술지원</li><li>결원·교체 시 대체 인력 검토와 인수인계</li></ul><p class="source-note">전기안전관리자 선임 기준 참고: <a href="{KEEA}" target="_blank" rel="noopener noreferrer">한국전기기술인협회 안내</a></p></div><div class="content-block"><h2>계약 전에 확인하는 것</h2><p>견적과 계약은 현장 조건 확인 후 진행합니다. 등록 범위와 수행 조건을 명확히 안내하고, 포함 업무와 별도 업무를 구분한 견적서를 제공합니다.</p><div class="related-links">{a('/guide/cost/','상주 위탁 견적 가이드 <span aria-hidden="true">→</span>')}{a('/about/','회사 소개 <span aria-hidden="true">→</span>')}</div></div></div></section>
    <section class="section section-soft"><div class="wrap faq-grid"><div class="faq-intro">{eyebrow('FAQ')}<h2>상주 위탁<br>자주 묻는 질문</h2></div>{faq()}</div></section>
    <section class="section-tight"><div class="wrap"><div class="section-head"><div>{eyebrow('ON-SITE BY AREA')}<h2>지역별 상주 위탁 안내</h2></div><p>현장이 있는 지역을 선택하면<br>해당 지역 안내 페이지로 이동합니다.</p></div><div class="search-city-list">{''.join(a(region_url(r,c),f'<span><small>{E(r["name"])}</small>{E(c["name"])}</span><span aria-hidden="true">→</span>') for r in REGIONS for c in r['cities'])}</div></div></section>{cta(service='onsite')}</main>'''

GUIDES={
 'cost':{'label':'상주 위탁 견적 가이드','kicker':'COST GUIDE','title':'상주 위탁 견적,<br>이렇게 산정합니다.','lead':'월 비용만 비교하기보다 필요한 인원·근무시간·포함 업무를 먼저 맞춰 보세요. 같은 조건으로 비교해야 정확한 판단이 가능합니다.','sections':[
 ('견적에 영향을 주는 조건',[('설비 용량과 선임 자격','수전·발전설비 용량에 따라 필요한 선임 자격이 달라집니다. 용량을 모르면 확인 가능한 자료부터 정리해 드립니다.'),('인원과 근무형태','요청 인원과 각 인원의 업무, 근무 요일·시간과 교대 여부를 명확히 합니다.'),('포함 업무와 별도 업무','상주 업무, 본사 지원 업무, 별도 점검·공사의 범위를 구분합니다.'),('시작 시점과 인수인계','계약 기간, 희망 시작일, 기존 관리 기록의 인계 여부를 함께 확인합니다.')]),
 ('견적서를 비교할 때 확인할 것',[('같은 조건끼리 비교','인원과 근무 조건이 다른 견적을 월 금액만으로 비교하지 않도록 조건표를 맞춥니다.'),('추가 업무의 처리 기준','별도 업무가 발생했을 때 범위와 비용을 어떻게 협의하는지 확인합니다.'),('확정되지 않은 조건 표시','아직 정해지지 않은 설비·일정·인원 조건은 가정으로 명시하고 확정 시 다시 확인합니다.')])]},
 'direct-hire':{'label':'직접고용 → 위탁 전환','kicker':'TRANSITION GUIDE','title':'직접고용에서 위탁으로,<br>운영 범위부터 비교하세요.','lead':'전환의 목적이 인력 운영 부담 해소인지, 업무 지원인지, 기존 운영의 보완인지 먼저 정리하면 조건을 맞추기 쉽습니다.','sections':[
 ('현재 운영을 먼저 정리합니다',[('관리자가 맡고 있는 업무','현재 전기안전관리자가 하는 업무와 별도로 수행 중인 시설 업무를 나눕니다.'),('회사가 지원하는 업무','장비·교육·행정·기술 검토를 현재 누가 담당하는지 확인합니다.'),('계속 유지할 부분','위탁 이후에도 발주자가 맡을 협의·자료 제공·현장 협조 범위를 정리합니다.')]),
 ('전환할 때 확인할 조건',[('역할과 책임','위탁 후 각 당사자의 역할과 책임 범위를 계약으로 명확히 합니다.'),('근무와 지휘 체계','실제 업무 운영 구조를 검토합니다. 고용·도급 관련 쟁점은 전문가 확인이 필요할 수 있습니다.'),('일정과 기록','전환일과 인수인계 자료, 진행 중인 점검·보완 업무를 정리합니다.')])]},
 'change':{'label':'위탁업체 변경 안내','kicker':'HANDOVER GUIDE','title':'위탁업체 변경,<br>관리 공백 없이 준비하세요.','lead':'기존 계약의 종료 시점과 새 운영의 시작 시점을 맞추고, 자료와 일정을 이어받는 것이 핵심입니다.','sections':[
 ('먼저 정리할 일정',[('기존 계약의 종료 조건','만료·갱신·해지 관련 조항과 통보 시점을 확인합니다.'),('새 운영의 시작 조건','희망 시작일과 설비·인력 조건을 함께 검토합니다.'),('인수인계 기간','기존 담당자와 확인할 수 있는 기간, 현장 방문 가능 시점을 정리합니다.')]),
 ('자료와 진행 중인 업무',[('기록·기본 자료','점검일지, 설비 자료, 선임 관련 서류 등 보유 자료와 인계 범위를 확인합니다.'),('잔여 업무','미완료 보완 사항과 예정된 점검·공사, 후속 협의가 필요한 항목을 정리합니다.'),('접근 권한','기존 접근 권한을 정리하고 새 담당자에게 필요한 자료를 안전하게 전달합니다.')])]}
}

def guide(key)->str:
    g=GUIDES[key];blocks=''
    for title,items in g['sections']:
        blocks+=f'<section class="content-block"><h2>{E(title)}</h2>'+''.join(f'<h3>{E(t)}</h3><p>{E(d)}</p>' for t,d in items)+'</section>'
    if key=='direct-hire':
        blocks+='<p class="source-note">이 페이지는 상담 준비를 위한 일반 안내이며 법률·노무 판단을 대신하지 않습니다. 선임·위탁 기준은 <a href="'+KEEA+'" target="_blank" rel="noopener noreferrer">한국전기기술인협회 안내</a>를 함께 확인하세요.</p>'
    return f'''<main id="main"><section class="page-hero"><div class="wrap">{breadcrumb([(f'/guide/{key}/',g['label'])])}{eyebrow(g['kicker'])}<h1>{g['title']}</h1><p class="lead">{E(g['lead'])}</p></div></section><section class="section-tight"><div class="wrap article">{blocks}<div class="callout">현장 지역과 시설 유형만 알려주셔도 상담을 시작할 수 있습니다. 회사명·상세주소는 첫 문의에서 필수가 아닙니다.</div></div></section><section class="section section-soft guide-section"><div class="wrap">{guides()}</div></section>{cta()}</main>'''

def about()->str:
    o=CONFIG['operator'];p=CONFIG['provider']
    return f'''<main id="main"><section class="page-hero bg-about"><div class="wrap">{breadcrumb([('/about/','회사 소개')])}{eyebrow('ABOUT US')}<h1>현장의 전기안전,<br>기준을 세웁니다.</h1><p class="lead">{E(BRAND)}는 {AREA} 사업장의 전기안전관리자 상주선임·위탁과 직무고시 대행을 제공합니다. 자격을 갖춘 인력과 명확한 업무 기준으로 현장의 전기안전을 책임집니다.</p></div></section>
    <section class="section-tight"><div class="wrap"><h2 class="visually-hidden">전기관리파트너스의 특징</h2><div class="feature-grid"><div class="feature"><span class="num">01</span><h3>상주 위탁 전문</h3><p>전기안전관리자 상주선임·위탁을 주력으로, 신규 선임·업체 변경·직접고용 전환을 담당합니다.</p></div><div class="feature"><span class="num">02</span><h3>명확한 업무 기준</h3><p>포함 업무와 별도 업무를 계약 단계에서 구분해 운영 중 혼선을 없앱니다.</p></div><div class="feature"><span class="num">03</span><h3>다섯 권역 집중</h3><p>{AREA}에 집중해 현장 대응과 인력 운영의 안정성을 높입니다.</p></div><div class="feature"><span class="num">04</span><h3>비공개 상담</h3><p>고객사 정보와 문의 내용은 외부에 공개하지 않습니다.</p></div></div></div></section>
    <section class="section-tight section-soft"><div class="wrap article"><section class="content-block"><h2>사업자 정보</h2><div class="privacy-block"><dl><dt>상호</dt><dd>{E(o['name'])}</dd><dt>대표자</dt><dd>{E(o['representative'])}</dd><dt>사업자등록번호</dt><dd>{E(o['registrationNumber'])}</dd>{('<dt>주소</dt><dd>'+E(o['publicAddress'])+'</dd>') if o['publicAddress'] else ''}{('<dt>상담전화</dt><dd>'+E(CONFIG['phone'])+'</dd>') if CONFIG['phone'] else ''}{('<dt>이메일</dt><dd>'+E(CONFIG['email'])+'</dd>') if CONFIG['email'] else ''}</dl></div></section><section class="content-block"><h2>서비스 수행</h2><div class="light-panel"><h3>{E(p['name'])}</h3><p>전기안전관리 업등록 범위 안에서 견적·계약·선임 및 업무 수행을 담당합니다.</p></div><p class="source-note">전기안전관리 업등록 기준: <a href="https://www.keea.or.kr/head/work/getWWO03R01R03.do" target="_blank" rel="noopener noreferrer">한국전기기술인협회 업등록 안내</a></p></section><section class="content-block"><h2>서비스 지역</h2><p>{AREA}의 시·군·구 사업장을 대상으로 합니다. 지역별 안내 페이지는 서비스 제공 지역의 구분이며, 각 지역의 지사 소재지를 뜻하지 않습니다.</p><div class="related-links">{a('/regions/','서비스 지역 전체 보기 <span aria-hidden="true">→</span>')}</div></section></div></section>{cta()}</main>'''

def privacy()->str:
    p=CONFIG['privacy'];live=not PREVIEW
    if not live:
        content='''<section class="content-block"><h2>수집 항목과 목적</h2><p>견적 문의 응대와 현장 조건 확인을 위해 연락처, 현장 지역, 시설 유형, 문의 유형, 운영 희망 조건을 수집합니다. 담당자명·이메일·설비 정보·요청 사항은 선택 항목입니다.</p></section><section class="content-block"><h2>처리 방식</h2><p>문의는 공개 게시판이 아닌 비공개로 접수되며, 상담 목적 외에 사용하지 않습니다. 첨부파일은 받지 않으며, 주민등록번호 등 민감정보는 입력하지 마세요.</p></section><section class="content-block"><h2>보유 및 권리</h2><p>문의 정보는 상담 처리 후 관련 법령에 따른 보유기간이 지나면 지체 없이 파기합니다. 열람·정정·삭제·처리정지는 아래 연락처로 요청하실 수 있으며, 필수항목 수집에 동의하지 않을 수 있으나 이 경우 상담 처리가 제한됩니다.</p></section>'''
    else:
        recipient=f'<dt>제3자 제공</dt><dd>받는 자: {E(p["thirdPartyRecipient"])}. 목적: 상주 위탁 상담·견적 검토. 항목: 제출한 연락처와 상담정보. 보유기간: {E(p["retentionText"])}. 동의를 거부할 수 있으나 제공을 전제로 한 상담은 제한됩니다.</dd>' if p['thirdPartyTransfer'] else ''
        content=f'''<div class="privacy-block"><dl><dt>개인정보처리자</dt><dd>{E(p['controller'])}</dd><dt>문의·권리행사 연락처</dt><dd>{E(p['contact'])}</dd><dt>처리 목적</dt><dd>견적 문의 응대, 현장 조건 확인, 견적 검토와 문의 처리</dd><dt>필수 항목</dt><dd>연락처, 현장 권역·지역, 시설 유형, 문의 유형, 운영 희망 조건, 동의 이력</dd><dt>선택 항목</dt><dd>담당자명, 이메일, 설비정보, 요청사항, 광고 캠페인 식별정보</dd><dt>보유기간</dt><dd>{E(p['retentionText'])}</dd>{recipient}<dt>권리</dt><dd>안내된 연락처로 열람·정정·삭제·처리정지를 요청할 수 있습니다. 필수항목 수집 동의를 거부할 수 있으나 상담 처리가 제한됩니다.</dd></dl></div>'''
    return f'''<main id="main"><section class="page-hero"><div class="wrap">{breadcrumb([('/privacy/','개인정보처리방침')])}{eyebrow('PRIVACY')}<h1>개인정보처리방침</h1><p class="lead">견적 문의 시 수집하는 정보와 처리 방식을 안내합니다.</p></div></section><section class="section-tight"><div class="wrap article">{content}</div></section></main>'''

def radio(name,items,default='')->str:
    return '<div class="choice-grid">'+''.join(f'<label><input type="radio" name="{E(name)}" value="{E(v)}" '+('checked ' if v==default else '')+f'><span class="choice-label">{E(t)}</span></label>' for v,t in items)+'</div>'

def quote_page()->str:
    opts=''.join(f'<option value="{r["slug"]}">{E(r["name"])}</option>' for r in REGIONS)
    consent='개인정보 수집·이용 안내를 확인하고 상담 목적의 필수항목 처리에 동의합니다.'
    transfer='<label class="consent"><input type="checkbox" name="transferConsent" value="yes"><span>안내된 수행업체에 상담정보를 제공하는 것에 동의합니다. '+a('/privacy/','제공 내용 확인')+'</span></label>' if CONFIG['privacy']['thirdPartyTransfer'] and not PREVIEW else ''
    turnstile=f'<div class="cf-turnstile" data-sitekey="{E(CONFIG["form"]["turnstileSiteKey"])}" data-action="inquiry"></div>' if CONFIG['form']['turnstileSiteKey'] else ''
    return f'''<main id="main" class="quote-main"><div class="wrap"><div class="quote-layout"><div class="quote-intro">{breadcrumb([('/quote/','견적 문의')])}{eyebrow('PRIVATE INQUIRY')}<h1>우리 현장에 맞는<br>전기안전관리,<br>견적을 문의하세요.</h1><p class="lead">상주 위탁 · 직무고시 대행<br>확인 가능한 정보부터 알려주시면 됩니다.</p><div class="quote-service-card"><span class="brand-mark">{logo_svg()}</span><p>문의 내용은 공개되지 않습니다.<br><b>현장 지역과 서비스에 맞춰 안내드립니다.</b></p></div><div class="note-box"><p>서비스 지역: {AREA}</p><p>회사명·상세주소·계약서는 첫 문의에서 필요하지 않습니다.</p><p>문의 후 현장 조건을 확인해 견적을 안내드립니다.</p></div></div>
    <div class="form-card"><div class="form-steps" aria-label="문의 작성 단계"><div class="step-indicator active" data-step-indicator="0"><span>01</span>서비스·지역</div><div class="step-indicator" data-step-indicator="1"><span>02</span>현장 조건</div><div class="step-indicator" data-step-indicator="2"><span>03</span>연락처</div></div>
    <form id="inquiry-form" novalidate><div class="hp" aria-hidden="true"><label>Website<input type="text" name="website" tabindex="-1" autocomplete="off"></label></div>
    <fieldset class="form-step" data-step="0"><legend>어떤 서비스가 필요하신가요?</legend><p class="step-desc">서비스와 현장이 위치한 지역을 선택해 주세요.</p>
    <div class="field"><span class="field-label">필요한 서비스<span class="required-label">필수</span></span>{radio('service',[('onsite','상주 위탁'),('duty','직무고시 대행'),('both','둘 다 상담')],'onsite')}</div>
    <div class="field-grid"><div class="field"><label class="field-label" for="province">현장 권역<span class="required-label">필수</span></label><select id="province" name="province"><option value="">권역 선택</option>{opts}</select></div><div class="field"><label class="field-label" for="city">세부 지역<span class="required-label">필수</span></label><select id="city" name="city"><option value="">권역을 먼저 선택하세요</option></select></div></div>
    <div class="field"><span class="field-label">시설 유형<span class="required-label">필수</span></span>{radio('facility',[('factory','공장'),('logistics','물류시설'),('building','업무·상업용 건물'),('construction','건설현장'),('other','기타 시설')])}</div></fieldset>
    <fieldset class="form-step" data-step="1" hidden><legend id="condition-title">어떤 운영을 원하시나요?</legend><p class="step-desc">아직 정해지지 않은 조건은 ‘협의’로 선택하시면 됩니다.</p>
    <div data-service-fields="onsite"><div class="field"><span class="field-label">상주 위탁 문의 유형<span class="required-label">필수</span></span>{radio('requestType',[('new','신규 상주선임'),('change','기존 위탁업체 변경'),('transition','직접고용 → 위탁 전환'),('consult','조건부터 상담')])}</div><div class="field"><label for="workType" class="field-label">희망 근무형태</label><select id="workType" name="workType"><option value="discuss">협의 필요</option><option value="day">주간 근무</option><option value="shift">교대 근무 검토</option></select></div></div>
    <div data-service-fields="duty" hidden><div class="field-grid"><div class="field"><label for="inspectionType" class="field-label">의뢰할 점검</label><select id="inspectionType" name="inspectionType"><option value="discuss">범위부터 상담</option><option value="periodic">정기 점검</option><option value="annual">연차 점검</option><option value="specific">특정 항목 점검·측정</option></select></div><div class="field"><label for="shutdownPossible" class="field-label">정전 가능 여부</label><select id="shutdownPossible" name="shutdownPossible"><option value="unknown">확인 필요</option><option value="yes">가능한 일정 있음</option><option value="limited">제한된 시간만 가능</option><option value="no">현재 어려움</option></select></div></div></div>
    <div class="field-grid"><div class="field"><label for="start" class="field-label">희망 시작·방문 시점</label><select id="start" name="start"><option value="discuss">일정 협의</option><option value="soon">가능한 빠르게</option><option value="month">한 달 이내</option><option value="later">이후 일정 검토</option></select></div><div class="field"><label class="field-label" for="capacity">설비용량<span class="optional">선택</span></label><input id="capacity" name="capacity" maxlength="120" placeholder="예: 수전 2,000kW / 확인 필요"></div></div></fieldset>
    <fieldset class="form-step" data-step="2" hidden><legend>연락받을 정보를 알려주세요.</legend><p class="step-desc">문의는 공개 게시판에 올라가지 않습니다.</p><div class="summary-card"><dl id="inquiry-summary"></dl></div><div class="field-grid responsive"><div class="field"><label class="field-label" for="contactName">담당자명<span class="optional">선택</span></label><input id="contactName" name="contactName" maxlength="60" autocomplete="name" placeholder="담당자명"></div><div class="field"><label class="field-label" for="phone">연락처<span class="required-label">필수</span></label><input id="phone" name="phone" type="tel" inputmode="tel" autocomplete="tel" maxlength="20" placeholder="연락 가능한 전화번호"></div></div><div class="field"><label class="field-label" for="email">이메일<span class="optional">선택</span></label><input id="email" name="email" type="email" maxlength="254" autocomplete="email" placeholder="견적을 받을 이메일"></div><div class="field"><label class="field-label" for="message">요청 사항<span class="optional">선택</span></label><textarea id="message" name="message" maxlength="2000" rows="3" placeholder="근무 조건이나 필요한 점검 항목을 적어주세요. 주민등록번호 등 민감정보는 입력하지 마세요."></textarea></div><label class="consent"><input type="checkbox" name="privacyConsent" value="yes"><span>{E(consent)} {a('/privacy/','안내 보기')}</span></label>{transfer}{turnstile}</fieldset>
    <div class="form-error" role="alert" aria-live="polite"></div><div class="form-actions"><button type="button" class="btn btn-ghost prev" hidden>이전</button><button type="button" class="btn next">다음 단계 <span aria-hidden="true">→</span></button><button type="submit" class="btn submit" hidden>견적 문의 접수 <span aria-hidden="true">→</span></button></div></form><div class="form-result" hidden aria-live="polite"></div><noscript><p class="draft-note">문의 작성에는 자바스크립트가 필요합니다. 서비스 안내는 자바스크립트 없이도 읽을 수 있습니다.</p></noscript></div></div></div></main>'''


def add(path,title,body,kind='page',description='',light=False,crumbs=None,faqs=None,service=None,keywords=''):
    plain=re.sub('<[^>]+>','',title)
    PAGES[path]={'title':plain+' | '+BRAND,'description':description or (plain+'. 서울·인천·경기·충북·충남 전기안전관리 견적 문의.'),'html':header(light)+body+footer(),'kind':kind,'crumbs':crumbs,'faqs':faqs,'service':service,'keywords':keywords}


def page_doc(path,page):
    public=page['kind'] not in ['privacy','quote','404']
    indexable=INDEXING and public and (not SEO['approvedPaths'] or path in SEO['approvedPaths'])
    robots='index,follow' if indexable else 'noindex,follow'
    canonical=f'<link rel="canonical" href="{E(ORIGIN+path)}">' if ORIGIN else ''
    canonical+=f'<meta property="og:url" content="{E(ORIGIN+path)}">' if ORIGIN else ''
    ver=''
    for key,name in [('googleVerification','google-site-verification'),('naverVerification','naver-site-verification')]:
        vals=SEO.get(key) or [];vals=[vals] if isinstance(vals,str) else vals
        ver+=''.join(f'<meta name="{name}" content="{E(v)}">' for v in vals if v)
    schema=''
    if indexable:
        graph=[{'@type':'WebPage','@id':ORIGIN+path,'name':page['title'],'description':page['description'],'url':ORIGIN+path,'inLanguage':'ko-KR','isPartOf':{'@id':ORIGIN+'/#website'}}]
        if path=='/':
            graph.append({'@type':'WebSite','@id':ORIGIN+'/#website','url':ORIGIN+'/','name':BRAND,'inLanguage':'ko-KR'})
            graph.append({'@type':'Organization','@id':ORIGIN+'/#org','name':BRAND,'alternateName':BRAND_EN,'url':ORIGIN+'/','logo':ORIGIN+'/favicon.svg','areaServed':[r['fullName'] for r in REGIONS],'description':page['description']})
        if page.get('crumbs'):
            graph.append({'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':i+1,'name':n,'item':ORIGIN+u} for i,(u,n) in enumerate(page['crumbs'])]})
        if page.get('service'):
            sv=page['service'];graph.append({'@type':'Service','@id':ORIGIN+path+'#service','name':sv['name'],'serviceType':sv['type'],'description':page['description'],'provider':{'@id':ORIGIN+'/#org'},'areaServed':sv['area'],'url':ORIGIN+path,'availableChannel':{'@type':'ServiceChannel','serviceUrl':ORIGIN+'/quote/','availableLanguage':'ko'}})
        if page.get('faqs'):
            graph.append({'@type':'FAQPage','mainEntity':[{'@type':'Question','name':q,'acceptedAnswer':{'@type':'Answer','text':a}} for q,a in page['faqs']]})
        data={'@context':'https://schema.org','@graph':graph}
        schema='<script type="application/ld+json">'+json.dumps(data,ensure_ascii=False).replace('</','<\\/')+'</script>'
    turnstile='<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>' if CONFIG['form']['turnstileSiteKey'] and page['kind']=='quote' else ''
    fonts='<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Poppins:wght@500;600&family=Outfit:wght@400;500;600&display=swap">'
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="{robots}"><meta name="theme-color" content="#15352D"><title>{E(page['title'])}</title><meta name="description" content="{E(page['description'])}"><meta property="og:type" content="website"><meta property="og:site_name" content="{E(BRAND)}"><meta property="og:locale" content="ko_KR"><meta property="og:title" content="{E(page['title'])}"><meta property="og:description" content="{E(page['description'])}"><meta property="og:image" content="{E(ORIGIN or '')}/assets/img/og.jpg"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image">{('<meta name="keywords" content="'+E(page['keywords'])+'">') if page.get('keywords') else ''}{canonical}{ver}<link rel="icon" href="{BASE}/favicon.svg" type="image/svg+xml">{fonts}<link rel="stylesheet" href="{BASE}/assets/style.css">{schema}</head><body>{page['html']}<script src="{BASE}/assets/data.js" defer></script><script src="{BASE}/assets/app.js" defer></script>{turnstile}</body></html>'''


def verify_production():
    if PREVIEW:return
    checks=[(CONFIG['brandConfirmed'],'brandConfirmed'),(CONFIG['operator']['verified'],'operator.verified'),(CONFIG['provider']['verified'],'provider.verified'),(CONFIG['provider']['registrationScopeVerified'],'provider.registrationScopeVerified'),(CONFIG['privacy']['verified'],'privacy.verified'),(CONFIG['phone'] or CONFIG['email'],'phone/email'),(CONFIG['operator']['publicAddress'],'operator.publicAddress'),(CONFIG['privacy']['controller'],'privacy.controller'),(CONFIG['privacy']['contact'],'privacy.contact'),(CONFIG['privacy']['retentionText'],'privacy.retentionText'),(urlparse(CONFIG['origin']).scheme=='https' and urlparse(CONFIG['origin']).hostname not in [None,'localhost','example.com'],'origin')]
    checks.append(((ROOT/'content/privacy-approved.html').is_file(),'content/privacy-approved.html'))
    if CONFIG['privacy']['thirdPartyTransfer']:checks.append((CONFIG['privacy']['thirdPartyRecipient'],'privacy.thirdPartyRecipient'))
    missing=[label for ok,label in checks if not ok]
    if missing:raise SystemExit('공개 전 확인 필요: '+', '.join(missing))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--preview-output',default=str(ROOT/'전기관리파트너스_미리보기.html'));args=parser.parse_args()
    verify_production()
    for region in REGIONS: region['cities'].sort(key=lambda city:city.get('sortName',city['name']))
    add('/','전기안전관리자 상주선임·위탁 전문',home(),light=True,keywords='전기안전관리자 상주선임, 전기안전관리 위탁, 전기안전관리업체, 직무고시 대행, 전기안전관리자 선임대행',description='전기안전관리자 상주선임·위탁 전문. 신규 선임·위탁업체 변경·직접고용 전환, 직무고시 대행. 서울·인천·경기·충북·충남.')
    add('/regions/','서울·인천·경기·충북·충남 지역별 전기안전관리 안내',all_regions())
    for r in REGIONS:
        body=region_page(r);add(f'/regions/{r["slug"]}/',r['name']+' 전기안전관리자 상주선임·위탁',body,'region',faqs=EXTRA[region_url(r)]['faqs'],service={'name':r['name']+' 전기안전관리자 상주 위탁','type':'전기안전관리자 상주선임·위탁','area':r['fullName']},keywords=f'{r["name"]} 전기안전관리업체, {r["name"]} 전기안전관리자 상주선임, {r["name"]} 전기안전관리 위탁, {r["name"]} 전기안전관리자 선임대행',crumbs=[('/','홈'),('/regions/','서비스 지역'),(region_url(r),r['name'])],description=f'{r["name"]} 전기안전관리업체. 전기안전관리자 상주선임·위탁, 위탁업체 변경, 직접고용 전환 견적 문의.')
        body=region_page(r,service='duty');add(region_url(r,service='duty'),r['name']+' 직무고시 대행',body,'region',faqs=EXTRA[region_url(r,service='duty')]['faqs'],service={'name':r['name']+' 직무고시 대행','type':'전기안전관리자 직무고시 점검 대행','area':r['fullName']},keywords=f'{r["name"]} 직무고시 대행, {r["name"]} 전기설비 점검, {r["name"]} 열화상 점검, {r["name"]} 절연저항 측정',description=f'{r["name"]} 직무고시 대행. 열화상·절연·접지저항 점검과 결과서 작성. 상주 위탁 없이 별도 의뢰 가능.')
        for c in r['cities']:
            label=r['name']+' '+c['name']
            body=region_page(r,c);add(region_url(r,c),label+' 전기안전관리자 상주선임·위탁',body,'region',faqs=EXTRA[region_url(r,c)]['faqs'],service={'name':c['name']+' 전기안전관리자 상주 위탁','type':'전기안전관리자 상주선임·위탁','area':r['fullName']+' '+c['name']},keywords=f'{c["name"]} 전기안전관리업체, {c["name"]} 전기안전관리자 상주선임, {c["name"]} 전기안전관리 위탁, {c["name"]} 전기안전관리자 선임대행, {label} 전기안전관리, {c.get("fullName",c["name"])} 전기안전관리자'+(''.join(', '+a+' 전기안전관리' for a in c.get('aliases',[]))),crumbs=[('/','홈'),('/regions/','서비스 지역'),(region_url(r),r['name']),(region_url(r,c),c['name'])],description=f'{label} 전기안전관리업체. 전기안전관리자 상주선임·위탁, 위탁업체 변경, 직접고용 전환 견적 문의.')
            body=region_page(r,c,'duty');add(region_url(r,c,'duty'),label+' 직무고시 대행',body,'region',faqs=EXTRA[region_url(r,c,'duty')]['faqs'],service={'name':c['name']+' 직무고시 대행','type':'전기안전관리자 직무고시 점검 대행','area':r['fullName']+' '+c['name']},keywords=f'{c["name"]} 직무고시 대행, {c["name"]} 전기설비 점검, {c["name"]} 열화상 점검, {c["name"]} 절연저항 측정',description=f'{label} 직무고시 대행. 열화상·절연·접지저항 점검과 결과서 작성. 상주 위탁 없이 별도 의뢰 가능.')
    add('/services/onsite/','전기안전관리자 상주선임·위탁 서비스',services(),faqs=FAQS,service={'name':'전기안전관리자 상주선임·위탁','type':'전기안전관리자 상주선임·위탁','area':[r['fullName'] for r in REGIONS]},keywords='전기안전관리자 상주선임, 전기안전관리 위탁, 전기안전관리자 선임대행, 전기안전관리업체, 상주 전기안전관리자',crumbs=[('/','홈'),('/services/onsite/','상주 위탁')],description='전기안전관리자 상주선임·위탁 전문. 신규 선임, 위탁업체 변경, 직접고용 전환. 서울·인천·경기·충북·충남.')
    add('/services/duty/','직무고시 대행 서비스',duty_service(),service={'name':'직무고시 대행','type':'전기안전관리자 직무고시 점검 대행','area':[r['fullName'] for r in REGIONS]},keywords='직무고시 대행, 전기안전관리자 직무고시, 전기설비 정기점검, 열화상 점검, 절연저항 측정, 접지저항 측정',crumbs=[('/','홈'),('/services/duty/','직무고시 대행')],description='직무고시 대행. 열화상·절연·접지저항 점검·측정과 결과서 작성. 상주 위탁 없이 별도 의뢰 가능.')
    for k,g in GUIDES.items():add('/guide/'+k+'/',g['label'],guide(k))
    add('/about/','회사 소개',about())
    pv=CONFIG['privacy'];o=CONFIG['operator']
    tokens={'{{BRAND}}':BRAND,'{{CONTROLLER}}':pv['controller'] or o['name'],'{{REPRESENTATIVE}}':o['representative'],'{{CONTACT}}':pv['contact'] or (CONFIG['phone'] or CONFIG['email'] or '홈페이지 견적 문의 양식'),'{{RETENTION}}':pv['retentionText'] or '1년','{{PROVIDER}}':pv['thirdPartyRecipient'] or CONFIG['provider']['name'],'{{EFFECTIVE}}':pv.get('effectiveDate','')}
    priv=(ROOT/'content/privacy-approved.html').read_text('utf-8')
    for k,v in tokens.items():priv=priv.replace(k,E(v))
    priv=priv.replace('href="/"','href="'+E(BASE)+'/"').replace('href="/privacy/"','href="'+E(BASE)+'/privacy/"')
    add('/privacy/','개인정보처리방침',priv,'privacy')
    add('/quote/','상주 위탁·직무고시 대행 견적 문의',quote_page(),'quote')
    add('/404.html','페이지를 찾을 수 없습니다','<main id="main"><div class="wrap not-found"><h1>404</h1><p>페이지 주소를 다시 확인해 주세요.</p>'+btn('/','홈으로 돌아가기')+'</div></main>','404')
    dist=ROOT/'dist';shutil.rmtree(dist,ignore_errors=True);dist.mkdir();shutil.copytree(ROOT/'assets',dist/'assets')
    public={'brand':BRAND,'base':BASE,'mode':CONFIG['mode'],'form':CONFIG['form'],'privacyVersion':CONFIG['privacy']['version'],'thirdPartyTransfer':CONFIG['privacy']['thirdPartyTransfer'],'regions':[{**r,'cities':[{'slug':c['slug'],'name':c.get('displayName',c['name'])} for c in r['cities']]} for r in REGIONS]}
    (dist/'assets/data.js').write_text('window.SITE='+json.dumps(public,ensure_ascii=False).replace('</','<\\/')+';',encoding='utf-8')
    for path,page in PAGES.items():
        target=dist/('404.html' if path=='/404.html' else path.strip('/')+'/index.html' if path!='/' else 'index.html');target.parent.mkdir(parents=True,exist_ok=True);target.write_text(page_doc(path,page),encoding='utf-8')
    (dist/'.nojekyll').write_text('',encoding='utf-8')
    (dist/'favicon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#F4F2EA"/><path fill="#15352D" d="M13 25 26 21 26 48 13 52zM34 14 47 10 47 47 34 51z"/><path fill="#B7E64A" d="M23 30 44 24 44 34 23 40z"/></svg>',encoding='utf-8')
    origin=ORIGIN;urls=[p for p in PAGES if INDEXING and PAGES[p]['kind'] not in ['quote','privacy','404'] and (not SEO['approvedPaths'] or p in SEO['approvedPaths'])]
    today=__import__('datetime').date.today().isoformat()
    def prio(p):return '1.0' if p=='/' else '0.9' if p.startswith('/services/') or p=='/regions/' else '0.8' if p.startswith('/regions/') else '0.6'
    (dist/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{xml_escape(origin+p)}</loc><lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>{prio(p)}</priority></url>\n' for p in urls)+'</urlset>',encoding='utf-8')
    (dist/'robots.txt').write_text('User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /quote/\n'+(f'Sitemap: {origin}/sitemap.xml\n' if INDEXING else '# Review build: every page has a noindex meta tag. This is not access control.\n'),encoding='utf-8')
    if SEO.get('customDomainLive') and origin:(dist/'CNAME').write_text(urlparse(origin).hostname+'\n',encoding='utf-8')
    (dist/'_headers').write_text('/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  X-Frame-Options: DENY\n  Permissions-Policy: camera=(), microphone=(), geolocation=()\n'+('' if INDEXING else '  X-Robots-Tag: noindex, noarchive\n'),encoding='utf-8')
    # Single-file reviewer: all route bodies are embedded; production uses real, pre-rendered pages.
    payload=json.dumps(PAGES,ensure_ascii=False).replace('</','<\\/').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    css=(ROOT/'assets/style.css').read_text('utf-8');js=(ROOT/'assets/app.js').read_text('utf-8');data=(dist/'assets/data.js').read_text('utf-8')
    # 단일 파일 미리보기는 file:// 로 열리므로 이미지를 data URI 로 내장한다.
    import base64
    for img in sorted((ROOT/'assets/img').glob('*.jpg')):
        css=css.replace(f'url(img/{img.name})','url(data:image/jpeg;base64,'+base64.b64encode(img.read_bytes()).decode()+')')
    fonts='<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Poppins:wght@500;600&family=Outfit:wght@400;500;600&display=swap">'
    preview=f'''<!doctype html><html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow,noarchive"><title>{E(PAGES['/']['title'])}</title>{fonts}<style>{css}</style></head><body>{PAGES['/']['html']}<script>{data}\nwindow.SITE.mode='preview';window.SITE.form.enabled=false;window.__PAGES__={payload};window.__OFFLINE__=true;</script><script>{js}</script></body></html>'''
    Path(args.preview_output).write_text(preview,encoding='utf-8')
    (ROOT/'docs/build-report.json').write_text(json.dumps({'mode':CONFIG['mode'],'htmlPages':len(PAGES),'regionalPages':sum(p['kind']=='region' for p in PAGES.values()),'indexablePages':len(urls),'sitemapUrls':len(urls),'routes':list(PAGES)},ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'worker/regions.js').write_text('export const REGION_CITIES = '+json.dumps({r['slug']:[c['slug'] for c in r['cities']]+['other'] for r in REGIONS},ensure_ascii=False)+';\n',encoding='utf-8')
    (ROOT/'docs/route-manifest.json').write_text(json.dumps([{'path':path,'title':page['title'],'type':page['kind']} for path,page in PAGES.items()],ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Built {len(PAGES)} HTML pages, {sum(p["kind"]=="region" for p in PAGES.values())} regional pages. Preview: {args.preview_output}')

def quote_url(province='',city='',service=''):
    values=[('province',province),('city',city),('service',service)]
    query='&'.join(k+'='+quote(v) for k,v in values if v)
    return '/quote/'+('?' +query if query else '')


def region_url(r,c=None,service='onsite'):
    return f'/regions/{r["slug"]}/'+(c['slug']+'/' if c else '')+('duty/' if service=='duty' else '')


def service_switch(service='onsite'):
    return '<div class="region-service-switch" role="group" aria-label="지역 안내 서비스 선택">'+''.join(f'<button type="button" data-region-service="{v}" aria-pressed="{str(v==service).lower()}">{t}</button>' for v,t in [('onsite','상주 위탁'),('duty','직무고시 대행')])+'</div>'


def region_link(r,c=None,label=None,cls='',search=False):
    path=region_url(r,c);duty=region_url(r,c,'duty')
    text=label if label is not None else E(c['name'] if c else r['name'])+'<span aria-hidden="true">→</span>'
    attrs={'data_region_route':path,'data_duty_route':duty}
    if search:
        attrs['data_search']=' '.join([r['name'],r['fullName'],c['name'],c.get('fullName','')]+c.get('aliases',[]))
    return a(path,text,cls,**attrs)


def duty_service()->str:
    items=[('열화상 점검','설비의 발열 상태를 확인하고 점검 결과를 기록합니다.'),('절연·접지저항 측정','대상 설비와 정전 조건을 확인한 뒤 측정합니다.'),('전력품질·추가 시험','필요 항목과 장비·인력을 확인해 수행 범위를 정합니다.'),('결과서 작성','측정 기록과 점검 결과서를 작성해 전달합니다.')]
    cards=''.join(f'<article class="scope-service-card"><span>0{i}</span><h3>{E(t)}</h3><p>{E(d)}</p></article>' for i,(t,d) in enumerate(items,1))
    return f'''<main id="main"><section class="page-hero bg-inspection"><div class="wrap">{breadcrumb([('/services/duty/','직무고시 대행')])}{eyebrow('INSPECTION & REPORTING')}<h1>직무고시 대행,<br>점검부터 결과서까지.</h1><p class="lead">전기안전관리자 직무고시에 따른 점검·측정 항목을 대행하고, 측정 기록과 결과서 작성을 지원합니다. 상주 위탁 계약 없이 점검만 별도로 의뢰하실 수 있습니다.</p><div class="hero-actions">{btn(quote_url(service='duty'),'직무고시 대행 견적 문의')}{a('/regions/?service=duty','지역별 직무고시 안내 <span aria-hidden="true">→</span>','text-link')}</div><div class="service-note-strip"><span>상주 위탁 없이 별도 의뢰</span><span>점검 항목별 견적</span><span>{AREA}</span></div></div></section>
    <section class="section-tight"><div class="wrap"><div class="section-head"><div>{eyebrow('SCOPE')}<h2>대행 가능한<br>점검·측정 항목</h2></div><p>실제 수행 항목은 대상 설비와<br>계약 범위에 따라 확정합니다.</p></div><div class="scope-service-grid">{cards}</div></div></section>
    <section class="section section-soft"><div class="wrap content-grid"><div><h2>현장에 맞는 점검 계획</h2><p class="feature-lead">월·분기·반기·연차 등 예정된 점검 가운데 어떤 범위를 맡길지 먼저 확인하고, 일정과 결과서 범위를 정합니다.</p><div class="scope-list"><article class="scope-row"><span>01</span><div><h3>자료·대상 설비 확인</h3><p>수전·발전설비 정보와 기존 점검 기록, 필요한 점검 범위를 정리합니다.</p></div></article><article class="scope-row"><span>02</span><div><h3>항목·정전·일정 협의</h3><p>가동 일정과 안전한 작업 조건을 확인하고, 정전이 필요한 항목은 따로 협의합니다.</p></div></article><article class="scope-row"><span>03</span><div><h3>현장 점검·결과서 전달</h3><p>합의한 범위에 따라 점검하고, 측정 기록과 결과서를 작성해 전달합니다.</p></div></article></div></div><aside class="side-card">{eyebrow('BEFORE A QUOTE')}<h3>이 정도만 알려주셔도<br>상담을 시작합니다.</h3><ul class="check-list"><li>현장 지역과 시설 유형</li><li>수전·발전설비 정보</li><li>원하는 점검 시기</li><li>정전 가능 여부</li></ul>{btn('/guide/duty-cost/','직무고시 견적 기준 보기','btn-outline')}</aside></div></section>
    <section class="section"><div class="wrap faq-grid"><div class="faq-intro">{eyebrow('FAQ')}<h2>직무고시 대행<br>자주 묻는 질문</h2></div>{faq([('직무고시 대행은 상주선임 대행과 같은가요?','아닙니다. 직무고시 대행은 계약으로 정한 점검·측정과 기록 업무를 수행하는 서비스이며, 전기안전관리자 선임과는 구분됩니다.'),('모든 설비를 정전 없이 점검하나요?','항목과 설비 조건에 따라 정전이 필요할 수 있습니다. 점검 일정과 작업 조건을 담당자와 협의합니다.'),('정밀시험·특수 장비 항목도 포함되나요?','기본 범위에 자동 포함되지 않습니다. 대상 설비에 필요한 장비와 수행 범위를 확인해 별도 항목으로 안내합니다.'),('점검 주기는 현장마다 같은가요?','설비와 관리 조건, 적용 기준에 따라 다릅니다. 현장의 점검 계획을 확인해 항목과 일정을 정합니다.')])}</div><div class="wrap"><p class="source-note">안내 기준: <a href="https://www.law.go.kr/행정규칙/전기안전관리자의직무에관한고시" target="_blank" rel="noopener noreferrer">전기안전관리자의 직무에 관한 고시</a></p></div></section>
    <section class="section-tight section-soft"><div class="wrap"><div class="section-head"><div>{eyebrow('DUTY INSPECTION BY AREA')}<h2>지역별 직무고시 대행</h2></div><p>현장이 있는 지역을 선택하면<br>해당 지역 직무고시 안내 페이지로 이동합니다.</p></div><div class="search-city-list">{''.join(a(region_url(r,c,'duty'),f'<span><small>{E(r["name"])}</small>{E(c["name"])}</span><span aria-hidden="true">→</span>') for r in REGIONS for c in r['cities'])}</div></div></section>{cta(service='duty')}</main>'''


GUIDES['duty-cost']={'label':'직무고시 대행 견적 기준','kicker':'INSPECTION COST GUIDE','title':'직무고시 견적,<br>점검 범위부터 맞춰보세요.','lead':'설비 조건과 의뢰할 항목, 정전 가능 시간, 결과서 범위에 따라 견적을 산정합니다.','sections':[
('견적에 필요한 기본 조건',[('대상 설비','수전·발전설비의 구성과 점검 대상, 기존 점검 기록을 확인합니다.'),('필요한 점검·측정','정기·연차 점검 또는 특정 항목 측정 가운데 필요한 범위를 나눕니다.'),('정전·출입·일정','가동 일정과 정전 가능 시간, 출입 등록 및 작업 여건을 확인합니다.'),('결과서 범위','측정 기록·점검 결과서의 작성·전달 범위를 정합니다.')]),
('포함·별도 업무 구분',[('전문 장비·추가 시험','기본 범위를 넘는 시험은 장비와 수행 가능 여부를 먼저 확인합니다.'),('점검과 보수공사','점검 결과에 따른 보수공사는 자동 포함되지 않으며 필요 시 별도로 안내합니다.'),('상주 위탁과의 구분','상주 계약과 함께 의뢰하더라도 별도 점검의 포함 여부를 확인합니다.')])]}

if __name__=='__main__':main()
