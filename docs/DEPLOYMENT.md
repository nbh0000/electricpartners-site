# 실운영 연결 인수인계

## 0. 현재 배포 상태 — 디자인 02 / 2026-09-17

외부 계정에 접속하거나 실제 서비스를 배포하지 않았습니다. 파일에 있는 `wrangler.example.toml`은 설정 예제일 뿐입니다. API와 DB 코드는 기본적으로 비활성화됩니다.

## 1. 공개 전 승인

`config/site.json`의 브랜드, 운영 사업자, 실제 수행업체, 등록범위, 공식 연락처·공개 주소, 개인정보 문서를 확인합니다. 해당 `verified` 값은 실제 검토를 완료했을 때만 변경합니다. `content/privacy-approved.html`에는 승인된 처리방침 본문 전체를 넣습니다. 처리위탁과 제3자 제공 중 실제 관계를 확정하고 폼의 고지·동의 문구도 맞춰 검토합니다.

공개와 수집을 동시에 시작할 필요는 없습니다. `mode=production`, `form.enabled=false`로 안내만 먼저 공개할 수 있으나 이때 문의 화면은 실제 제출 준비 중임을 안내합니다. 사업자/연락처/운영 구조의 공개 전 검증은 여전히 필요합니다.

## 2. Cloudflare 자원 준비

계정 소유자의 승인하에 Cloudflare Workers의 정적 자산, D1, Turnstile을 연결합니다. Wrangler는 별도 설치가 필요하며 사용할 버전의 공식 문서를 확인해 설치·고정하세요. 자원 생성이나 과금·결제는 자동 실행하지 않았습니다.

예시 명령:

```sh
cp wrangler.example.toml wrangler.toml
wrangler d1 create electricpartners-private-inquiries
```

생성된 실제 database_id를 wrangler.toml에 넣고, 승인된 계정인지 재확인한 후:

```sh
wrangler d1 migrations apply electricpartners-private-inquiries --remote
```

신규 환경에서는 `0001_inquiries.sql`과 `0002_services.sql` 두 마이그레이션을 순서대로 적용합니다. 이전 버전 DB를 사용한다면 0001을 다시 생성하지 않고 적용 이력을 확인한 후 0002를 적용합니다. 추가 필드는 `service`, `inspection_type`, `shutdown_possible`입니다.

## 3. 환경변수

| 변수 | 설정 |
|---|---|
| SITE_ORIGIN | 최종 HTTPS 도메인의 origin, 끝 슬래시 없이 |
| ENABLE_INQUIRIES | 실제 접수 테스트 이후 true |
| PRIVACY_VERIFIED | 운영관계·개인정보 검토 완료 이후 true |
| PRIVACY_VERSION | 프론트엔드 site.json의 privacy.version과 같은 값 |
| TURNSTILE_HOSTNAME | 최종 도메인의 hostname만 |
| RETENTION_DAYS | 승인한 문의 보유기간을 일수로 설정. 기본 0은 접수 차단 |
| REQUIRE_TRANSFER_CONSENT | 실제 제3자 제공이면 true, 프론트엔드와 일치 |

다음은 secret으로 설정합니다. 프론트엔드에 노출하지 마세요.

```sh
wrangler secret put TURNSTILE_SECRET_KEY
wrangler secret put RATE_LIMIT_SALT
```

RATE_LIMIT_SALT는 충분히 긴 독립적인 무작위 비밀값을 사용합니다. 이 프로젝트에 적힌 테스트용 문자열을 운영에 재사용하지 마세요.
Turnstile 공개 Site Key는 `site.json`의 form.turnstileSiteKey에 넣고 비밀키와 혼동하지 않습니다.

선택 알림 연결:

```sh
wrangler secret put LEAD_NOTIFY_URL
wrangler secret put LEAD_NOTIFY_TOKEN
```

수신처는 신뢰하는 HTTPS 엔드포인트로만 지정합니다. 기본 발송 내용은 접수번호·권역·서비스 종류·문의 유형이며 개인정보 본문을 포함하지 않습니다. 문자·이메일·카카오 실발송 기능은 수신처에서 별도 구현·과금·검증해야 합니다.

## 4. 빌드·배포

`python3 scripts/build.py`로 최신 dist를 만들고, 먼저 별도의 접근통제된 스테이징에서 확인합니다. `dist/`의 HTML이 Workers static assets에서 실제 200으로 제공되는지, 잘못된 경로가 실제 404인지 확인하세요.

```sh
wrangler deploy
```

사용할 도메인 라우트·Custom Domain은 계정에서 추가해야 합니다. Workers의 외부 공개·DNS 변경은 도메인 소유자의 승인 후 수행하세요.

`noindex`는 보안 기능이 아닙니다. 스테이징 페이지와 서버 환경은 Access 등으로 보호하세요. 내부 검토자료를 호스팅 정적 자산으로 잘못 올리지 않도록 배포 대상은 `dist/`만 사용합니다.

## 5. 운영 테스트 체크리스트

실제 접수 테스트는 개인정보 주체의 동의가 있는 자체 테스트 정보로 진행합니다. 상주·직무고시·복합 세 유형을 각각 시험하고 DB의 service·inspection_type·shutdown_possible 값이 선택과 일치하는지 확인합니다.

1. 설정 누락·잘못된 Origin·허용되지 않은 HTTP 메서드가 접수를 차단하는지 확인합니다.
2. 실제 Turnstile 토큰을 발급받고 서버 검증까지 성공하는지 확인합니다. 검증 응답의 hostname과 action을 확인합니다.
3. 한 번 제출한 문의가 실제 D1에 저장되는지, 성공 화면은 저장 이후에만 보이는지 확인합니다.
4. 프론트엔드에서 연락처·이메일·본문이 로그나 분석 서비스로 전달되지 않는지 네트워크에서 확인합니다.
5. 문의 전체 조회용 공개 API·공개 저장 파일이 없는지 확인합니다.
6. 필요한 운영자만 Cloudflare/D1에 접근할 수 있도록 역할·다중인증을 설정합니다.
7. 선택한 알림 수신처에서 알림 도착, 장애 모니터링·재처리 절차를 확인합니다.
8. 보유기간 만료 삭제 작업, 백업 및 플랫폼 로그의 보유정책을 함께 확인합니다. application 테이블 삭제만으로 플랫폼 백업·로그 정책까지 제어되는 것은 아닙니다.
9. 기관 등록·사업자 표시·개인정보 문서를 운영 구조에 맞게 재확인합니다.
10. 테스트 문의를 삭제하고 광고·실제 접수를 시작합니다.

## 6. 현재 보안 구현 범위와 남은 운영 과제

구현: 서버 측 권역·세부 지역·입력 검증, 필수 동의 및 정책 버전 확인, 같은 Origin 제한, 본문 크기 제한, Turnstile 서버 검증, HMAC IP 기반 5분 버킷 요청 제한, SQL 바인딩, 비공개 D1 저장 어댑터, 만료 기록 정리 스케줄.

구현하지 않음: 인증된 웹 관리자 UI, 접수 재시도 idempotency 보장, 알림 실패 큐·재발송 대시보드, 운영 감사로그, 광고 플랫폼 서버 전환 업로드, 데이터 수출·삭제 관리자 UX, 독립 보안감사.

정상 사용자가 다수인 공용 IP에서는 동일 버킷 제한이 영향을 줄 수 있습니다. 실제 트래픽을 보고 WAF 및 제한 기준을 조정해야 합니다. 전달한 코드는 기본 출발점이며 무제한 방어·무중단·법적 준수를 보장하지 않습니다.

## 7. 도메인 선택·검색 공개·광고

후보는 `electricpartners.com`과 `elecpartners.com`입니다. `config/site.json`의 `origin`, Worker의 `SITE_ORIGIN`, Turnstile 허용 hostname 및 `TURNSTILE_HOSTNAME`을 최종 선택에 맞게 통일합니다. 도메인 구입·DNS 설정은 이 제작물에서 실행하지 않았습니다. 영문 로고 ELECTRIC PARTNERS는 도메인 철자와 독립적인 브랜드 표기입니다.


`seo.approvedPaths`에 추가한 경로만 색인 허용·사이트맵에 포함됩니다. 각 페이지를 자동으로 전체 승인하지 마세요. 지역별 운영조건·고유 정보가 부족하면 해당 권역 안내로 통합하는 방향도 검토합니다.

광고 링크에는 운영자가 정한 UTM을 붙일 수 있습니다. 예:

```text
/regions/gyeonggi/siheung/?utm_source=naver&utm_medium=cpc&utm_campaign=siheung_onsite
```

추적 파라미터는 링크에 실제 존재할 때만 이어받습니다. 자동으로 모든 자연검색어·구글 검색어를 알아내는 기능이 아닙니다. 네이버 키워드 치환값은 해당 광고 설정과 실제 지원 형식을 확인해야 합니다. 광고 순위·중복 사이트 심사는 별도입니다.
