# 네이버 검색 등록 작업 안내 (elecmanagepartners.com)

## 1. 현재 적용 상태 (빌드에 반영됨)

| 항목 | 상태 |
|---|---|
| 공개 페이지 robots | 메인·서비스·지역 205개 페이지 `index,follow` |
| 비공개 유지 | `/quote/`(견적 폼), `/privacy/`, `404` → `noindex`, robots.txt에서 `/quote/`·`/api/` 차단 |
| canonical / og:url | 모든 페이지 `https://elecmanagepartners.com/...` 기준 (GitHub 임시 주소 아님) |
| 사이트맵 | `https://elecmanagepartners.com/sitemap.xml` (205 URL, lastmod·priority 포함) |
| robots.txt | `https://elecmanagepartners.com/robots.txt` — 전체 허용 + Sitemap 선언 |
| 구조화 데이터 | 메인: WebSite·Organization, 지역 페이지: WebPage·BreadcrumbList (JSON-LD) |
| 네이버 소유확인 태그 | `config/site.json` → `seo.naverVerification` 에 content 값 입력 후 배포 |

지역 페이지 제목·설명 예시
- `<title>경기 안산 전기안전관리자 상주선임·위탁 | 전기관리파트너스</title>`
- description: "경기 안산 전기안전관리업체를 찾으신다면. 안산 사업장의 전기안전관리자 상주선임·상주 위탁, 위탁업체 변경, 직접고용 전환 견적 문의."

## 2. 도메인 연결 (선행 필수)

검색로봇은 실제 도메인에서 페이지를 읽으므로, 아래가 끝나야 소유확인·사이트맵 제출이 가능합니다.

1. 도메인 DNS 설정 (도메인 구입처 관리 화면)
   - `A` 레코드 `@` → `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
   - `CNAME` 레코드 `www` → `nbh0000.github.io`
2. `config/site.json` 의 `seo.customDomainLive` 를 `true` 로 바꾸고 push
   - 빌드가 자동으로 루트 경로(`/`) 기준으로 전환되고 `CNAME` 파일이 생성됩니다.
3. GitHub 저장소 → Settings → Pages → Custom domain 에 `elecmanagepartners.com` 입력, "Enforce HTTPS" 체크 (인증서 발급까지 수 분~1시간)

## 3. 네이버 서치어드바이저 (클라이언트 계정에서 진행)

1. https://searchadvisor.naver.com → 웹마스터 도구 → 사이트 등록: `https://elecmanagepartners.com`
2. 소유확인 → "HTML 태그" 선택 → `<meta name="naver-site-verification" content="XXXX">` 의 **content 값**을 전달
   → `config/site.json` `seo.naverVerification` 에 입력 후 push → 1분 뒤 "소유확인" 버튼
3. 요청 → 사이트맵 제출: `https://elecmanagepartners.com/sitemap.xml`
4. 요청 → RSS 제출: 해당 없음(블로그형 아님)
5. 요청 → 웹 페이지 수집: 아래 URL 우선 요청
   - `https://elecmanagepartners.com/`
   - `https://elecmanagepartners.com/services/onsite/`
   - `https://elecmanagepartners.com/services/duty/`
   - `https://elecmanagepartners.com/regions/`
   - 광고 랜딩으로 쓸 지역 페이지 (예: `/regions/gyeonggi/ansan/`, `/regions/seoul/gangnam/`)
6. 검증 → robots.txt 검증 / 사이트맵 검증 / "웹 페이지 최적화" 로 메인·대표 지역 페이지 검사 후 결과 캡처

## 4. 확인용 명령 (터미널)

```sh
curl -sI https://elecmanagepartners.com/regions/gyeonggi/ansan/ | head -1        # HTTP/2 200
curl -s  https://elecmanagepartners.com/regions/gyeonggi/ansan/ | grep -o '<meta name="robots"[^>]*>'
curl -s  https://elecmanagepartners.com/robots.txt
curl -s  https://elecmanagepartners.com/sitemap.xml | grep -c '<loc>'              # 205
```
