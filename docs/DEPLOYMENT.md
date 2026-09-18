# 운영 배포 가이드 — 가비아 · Cloudflare · Supabase · 카카오 알림

순서대로 진행합니다. ✅ 표시는 이미 코드에 준비된 항목, 🔑 는 계정 주인이 대시보드에서 직접 하는 항목입니다.

## 0. 준비된 것 ✅
- `worker/index.js` — Supabase(PostgREST) 저장 + Turnstile 검증 + 요청 제한 + 카카오톡 알림 + 매일 만료 삭제
- `supabase/schema.sql` — 테이블·RLS·RPC·관리자용 보기(`inquiries_admin`)
- `wrangler.example.toml` — Workers 설정 템플릿
- `content/privacy-approved.html` — 개인정보처리방침 (config 값으로 채워짐)
- `.github/workflows/cloudflare.yml` — push 시 자동 배포 (저장소 변수 `CLOUDFLARE_DEPLOY=true` 로 활성화)

## 1. Supabase 🔑 (10분)
1. https://supabase.com → New project → 이름 `electricpartners`, Region **Northeast Asia (Seoul)**, DB 비밀번호는 보관
2. 좌측 **SQL Editor** → `supabase/schema.sql` 내용 전체 붙여넣기 → Run
3. **Project Settings → API** 에서 두 값을 복사해 둠 (Worker 시크릿으로 씀)
   - `Project URL`  → `SUPABASE_URL`
   - `service_role` 키 → `SUPABASE_SERVICE_KEY` (절대 프론트/깃에 넣지 않음)
4. 문의 확인: **Table Editor → inquiries_admin** (한글 라벨 보기) 또는 `inquiries`. 상태(status)·메모(memo)는 여기서 직접 수정

## 2. Cloudflare 🔑 (15분)
1. https://dash.cloudflare.com → **Add a site** → `elecmanagepartners.com` → Free → 안내되는 **네임서버 2개** 메모
2. **Turnstile** → Add widget → 도메인 `elecmanagepartners.com`, Managed → `Site Key`, `Secret Key` 메모
3. **My Profile → API Tokens → Create Token → "Edit Cloudflare Workers"** 템플릿 → 토큰 메모, 대시보드 우측의 **Account ID** 메모
4. GitHub 저장소 → Settings → Secrets and variables → Actions
   - Secrets: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`
   - Variables: `CLOUDFLARE_DEPLOY` = `true`

## 3. 가비아 🔑 (5분)
My가비아 → 도메인 관리 → **네임서버 설정** → 2단계에서 받은 Cloudflare 네임서버 2개로 교체 → 저장. (반영 수 분~24시간, Cloudflare 대시보드가 "Active" 로 바뀌면 완료)

## 4. 카카오톡 알림 🔑 (15분) — "나에게 보내기" 방식
1. https://developers.kakao.com → 내 애플리케이션 → 앱 추가 (이름: 전기관리파트너스 알림)
2. **앱 키 → REST API 키** 메모 → `KAKAO_REST_KEY`
3. **카카오 로그인** 활성화, Redirect URI 에 `https://elecmanagepartners.com/` 추가
4. **동의항목** → "카카오톡 메시지 전송(talk_message)" 사용 설정
5. 브라우저에서 아래 주소를 열어 로그인·동의 → 주소창의 `code=` 값 복사
   `https://kauth.kakao.com/oauth/authorize?client_id=REST키&redirect_uri=https://elecmanagepartners.com/&response_type=code&scope=talk_message`
6. 터미널에서 토큰 발급 (code 는 1회용, 몇 분 내 사용)
   ```sh
   curl -X POST https://kauth.kakao.com/oauth/token -d grant_type=authorization_code -d client_id=REST키 -d redirect_uri=https://elecmanagepartners.com/ -d code=복사한값
   ```
   응답의 `refresh_token` → `KAKAO_REFRESH_TOKEN` (약 2개월마다 자동 갱신되므로 Worker 가 계속 사용 가능)
   알림은 **로그인한 카카오 계정 본인의 카카오톡**으로 옵니다. 팀 공유가 필요하면 나중에 알림톡(솔라피 등)으로 확장.

## 5. 코드 쪽 마무리 (제가 진행, 값만 전달)
1. `wrangler.example.toml` → `wrangler.toml` 복사 (값은 이미 채워져 있음)
2. 시크릿 등록 — 프로젝트 폴더에서 계정 주인이 직접 실행 (값이 채팅에 남지 않게)
   ```sh
   npx wrangler login
   npx wrangler secret put SUPABASE_URL
   npx wrangler secret put SUPABASE_SERVICE_KEY
   npx wrangler secret put TURNSTILE_SECRET_KEY
   npx wrangler secret put RATE_LIMIT_SALT          # openssl rand -hex 32 결과
   npx wrangler secret put KAKAO_REST_KEY
   npx wrangler secret put KAKAO_REFRESH_TOKEN
   ```
3. `config/site.json`
   - `mode`: `"production"`, `form.enabled`: `true`, `form.turnstileSiteKey`: Turnstile Site Key
   - `phone` 또는 `email`, `operator.publicAddress`, `privacy.contact` 입력
   - `operator.verified`, `provider.verified`, `provider.registrationScopeVerified`, `privacy.verified` → `true` (내용 확인 후)
   - `seo.customDomainLive`: `true`, `seo.naverVerification`: 네이버 태그 값
4. `git push` → GitHub Actions 가 `wrangler deploy` 실행 → `https://elecmanagepartners.com` 에서 사이트 + `/api/inquiries` 동작
5. GitHub Pages 워크플로(`pages.yml`)는 비활성화하거나 삭제

## 6. 검증 체크리스트
- [ ] `https://elecmanagepartners.com/` 200, HTTPS 자물쇠
- [ ] 견적 문의 테스트 제출 → Supabase `inquiries_admin` 에 행 생성, 카카오톡 알림 수신
- [ ] 같은 IP 로 6회 연속 제출 시 429
- [ ] `/sitemap.xml`, `/robots.txt` 정상
- [ ] 네이버 서치어드바이저 소유확인 → 사이트맵 제출 → 수집 요청 (docs/SEO.md)
