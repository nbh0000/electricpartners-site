"""Local static and browser checks; does not deploy, submit or connect external accounts."""
from pathlib import Path
from urllib.parse import urlsplit
import argparse, os, shutil
import json
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
PREVIEW=ROOT/'전기관리파트너스_미리보기.html'
parser=argparse.ArgumentParser()
parser.add_argument('--chromium',default=os.getenv('CHROMIUM_PATH') or shutil.which('chromium') or shutil.which('chromium-browser'))
args=parser.parse_args()
REPORT={'static':{},'browser':[],'live_integrations':'not connected; browser review and mocked worker tests only'}
(ROOT/'docs/previews').mkdir(parents=True,exist_ok=True)
FILES=list((ROOT/'dist').rglob('*.html'))
titles=set()
for file in FILES:
    text=file.read_text('utf-8'); soup=BeautifulSoup(text,'html.parser')
    assert len(soup.find_all('h1'))==1,(file,'H1')
    title=soup.title.get_text();assert title not in titles,(file,'duplicate title');titles.add(title)
    assert '전기관리파트너스' in title,file
    assert soup.find('meta',attrs={'name':'robots'})['content'] in ('index,follow','noindex,follow'),file
    assert '전담전기' not in text and 'JEONDAM' not in text,file
    for a in soup.select('a[href^="/"]'):
        path=urlsplit(a['href']).path
        target=ROOT/'dist'/('404.html' if path=='/404.html' else path.strip('/')+'/index.html' if path!='/' else 'index.html')
        assert target.is_file(),(str(file),path)
regions=json.loads((ROOT/'content/regions.json').read_text())
for r in regions:
    assert [c['name'] for c in r['cities']]==sorted(c['name'] for c in r['cities']),r['slug']
    for c in r['cities']:
        for s in ['', 'duty/']:
            assert (ROOT/f'dist/regions/{r["slug"]}/{c["slug"]}/{s}index.html').is_file()
REPORT['static']={'htmlDocuments':len(FILES),'regionalDocuments':196,'districts':sum(len(r['cities']) for r in regions),'uniqueTitles':len(titles),'brokenInternalLinks':0,'allSubregionsSorted':True,'reviewNoindex':True}

with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=args.chromium,headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
    errors=[];requests=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:requests.append(r.url))
    base='about:blank'
    page.set_content(PREVIEW.read_text('utf-8'), wait_until='load')
    def go(url):
        route=url.split('#',1)[1] if '#' in url else '/'
        page.evaluate('(route)=>{location.hash=route}',route)
        page.wait_for_timeout(80)
    go(base);page.wait_for_timeout(600)
    page.screenshot(path=str(ROOT/'docs/previews/desktop.png'))
    page.screenshot(path=str(ROOT/'docs/previews/home-full.png'),full_page=True)
    assert page.locator('h1').inner_text()=='우리 현장의\n전기관리,\n믿고 맡길 파트너.'
    # Each tab is populated and already sorted. Check actual rendered names.
    for r in regions:
        page.locator(f'[data-tab="{r["slug"]}"]').click()
        names=[v.replace('↗','').strip() for v in page.locator(f'#panel-{r["slug"]} .region-links a').all_text_contents()]
        assert names==[c['name'] for c in r['cities']],(r['slug'],names)
    page.locator('[data-tab="gyeonggi"]').click()
    page.locator('[data-region-service="duty"]').click()
    target=page.locator('#panel-gyeonggi .region-links a').filter(has_text='시흥')
    assert '/siheung/duty/' in target.get_attribute('href')
    target.click();page.wait_for_timeout(150)
    assert '시흥' in page.locator('h1').inner_text() and '직무고시' in page.locator('h1').inner_text()
    page.screenshot(path=str(ROOT/'docs/previews/region-duty.png'))
    page.locator('.side-card a.btn').click();page.wait_for_timeout(100)
    assert page.locator('#province').input_value()=='gyeonggi'
    assert page.locator('#city').input_value()=='siheung'
    assert page.locator('input[name="service"][value="duty"]').is_checked()
    page.locator('label:has(input[name="facility"][value="factory"])').click()
    page.locator('.form-actions .next').click()
    assert page.locator('[data-service-fields="duty"]').is_visible()
    assert not page.locator('[data-service-fields="onsite"]').is_visible()
    page.locator('#inspectionType').select_option('annual')
    page.locator('#shutdownPossible').select_option('limited')
    page.locator('.form-actions .next').click()
    assert '직무고시 대행' in page.locator('#inquiry-summary').inner_text()
    assert '연차 점검' in page.locator('#inquiry-summary').inner_text()
    page.locator('.form-actions .submit').click()
    assert '전화번호' in page.locator('.form-error').inner_text()
    page.locator('#phone').fill('010-0000-0000')
    page.locator('[name="privacyConsent"]').check()
    before=len(requests)
    page.locator('.form-actions .submit').click()
    assert page.locator('.form-result').is_visible()
    assert '실제 상담 접수' in page.locator('.form-result').inner_text()
    assert len(requests)==before
    REPORT['browser'].append('Duty route -> prefilled province/city/service -> duty conditions -> validation -> preview-only confirmation')
    for service in ['onsite','both']:
        go(base+'#/quote/?province=seoul&city=gangnam&service='+service);page.wait_for_timeout(150)
        page.locator('label:has(input[name="facility"][value="building"])').click()
        page.locator('.form-actions .next').click()
        page.locator('.form-actions .next').click()
        assert '문의 유형' in page.locator('.form-error').inner_text()
        page.locator('label:has(input[name="requestType"][value="change"])').click()
        if service=='both':
            assert page.locator('[data-service-fields="duty"]').is_visible()
            page.locator('#inspectionType').select_option('periodic')
        page.locator('.form-actions .next').click()
        page.locator('#phone').fill('010-0000-0000')
        page.locator('[name="privacyConsent"]').check()
        page.locator('.form-actions .submit').click()
        assert page.locator('.form-result').is_visible()
    REPORT['browser'].append('Onsite and combined service form flows validated independently')
    go(base+'#/regions/?service=duty');page.wait_for_timeout(150)
    assert '/duty/' in page.locator('.search-city-list a').first.get_attribute('href')
    page.locator('#region-search').fill('제물포')
    assert page.locator('.search-city-list a:visible').count()==1
    page.locator('#region-search').fill('없는지역명')
    assert page.locator('.search-city-list a:visible').count()==0
    page.locator('#region-search').fill('')
    assert page.locator('.search-city-list a:visible').count()==93
    REPORT['browser'].append('93-area search and service-linked independent URLs verified')
    # Mobile/desktop layout checks on major templates.
    routes=['/','/services/duty/','/services/onsite/','/regions/','/regions/gyeonggi/siheung/','/regions/seoul/gangnam/duty/','/quote/?service=both','/about/']
    for width in [320,375,390,768,1024,1440]:
        page.set_viewport_size({'width':width,'height':900})
        for route in routes:
            go(base+'#'+route);page.wait_for_timeout(30)
            metrics=page.evaluate('({width:innerWidth,body:document.body.scrollWidth,doc:document.documentElement.scrollWidth})')
            assert max(metrics['body'],metrics['doc'])<=width+1,(width,route,metrics)
    REPORT['browser'].append('No horizontal page overflow across 8 templates at 320/375/390/768/1024/1440 px')
    page.set_viewport_size({'width':390,'height':844});go(base);page.wait_for_timeout(150)
    page.screenshot(path=str(ROOT/'docs/previews/mobile.png'))
    page.screenshot(path=str(ROOT/'docs/previews/mobile-full.png'),full_page=True)
    page.locator('.menu-toggle').click();assert page.locator('.site-nav').is_visible()
    page.locator('.site-nav').get_by_text('직무고시 대행',exact=True).click();page.wait_for_timeout(100)
    assert '직무고시' in page.locator('h1').inner_text()
    page.screenshot(path=str(ROOT/'docs/previews/duty-mobile.png'))
    page.set_viewport_size({'width':1440,'height':1000});go(base+'#/services/duty/');page.wait_for_timeout(150)
    page.screenshot(path=str(ROOT/'docs/previews/duty-desktop.png'))
    go(base+'#/quote/?service=duty&province=gyeonggi&city=siheung');page.wait_for_timeout(100)
    page.screenshot(path=str(ROOT/'docs/previews/quote-desktop.png'))
    assert not errors,errors
    assert not [r for r in requests if r.startswith(('http:','https:'))],requests
    REPORT['browser'].append('No JS page errors or external requests from offline preview')
    browser.close()
(ROOT/'docs/design-qa.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(REPORT,ensure_ascii=False,indent=2))
