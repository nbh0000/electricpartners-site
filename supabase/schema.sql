-- 전기관리파트너스 문의 저장소 (Supabase / PostgreSQL)
-- Supabase 대시보드 → SQL Editor 에 붙여넣고 Run.
-- 브라우저에서는 어떤 정책도 열지 않는다. Worker 만 service_role 키로 접근한다.

create table if not exists public.inquiries (
  id text primary key,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  province text not null,
  city text not null,
  facility text not null,
  request_type text not null,
  start_preference text not null,
  work_type text not null,
  capacity text not null default '',
  contact_name text not null default '',
  phone text not null,
  email text not null default '',
  message text not null default '',
  entry_path text not null default '/',
  attribution_json text not null default '{}',
  privacy_version text not null,
  privacy_consent int not null check (privacy_consent = 1),
  transfer_consent int not null check (transfer_consent in (0,1)),
  status text not null default 'new' check (status in ('new','contacted','quoted','won','closed')),
  service text not null default 'onsite' check (service in ('onsite','duty','both')),
  inspection_type text not null default 'discuss' check (inspection_type in ('discuss','periodic','annual','specific')),
  shutdown_possible text not null default 'unknown' check (shutdown_possible in ('unknown','yes','limited','no')),
  memo text not null default ''   -- 관리자 메모(대시보드에서 직접 입력)
);
create index if not exists idx_inquiries_created on public.inquiries (created_at desc);
create index if not exists idx_inquiries_expiry  on public.inquiries (expires_at);
create index if not exists idx_inquiries_service on public.inquiries (service, created_at desc);

create table if not exists public.request_limits (
  fingerprint text primary key,
  count int not null,
  expires_at timestamptz not null
);
create index if not exists idx_request_limits_expiry on public.request_limits (expires_at);

-- 5분 버킷당 요청 횟수 증가 (Worker 가 RPC 로 호출)
create or replace function public.bump_request_limit(p_fingerprint text, p_expires_at timestamptz)
returns int language sql security definer set search_path = public as $$
  insert into public.request_limits (fingerprint, count, expires_at)
  values (p_fingerprint, 1, p_expires_at)
  on conflict (fingerprint) do update set count = public.request_limits.count + 1
  returning count;
$$;

-- RLS: 켜두고 정책은 만들지 않는다 → anon/authenticated 키로는 읽기·쓰기 모두 불가
alter table public.inquiries      enable row level security;
alter table public.request_limits enable row level security;
revoke all on public.inquiries, public.request_limits from anon, authenticated;
revoke execute on function public.bump_request_limit(text, timestamptz) from anon, authenticated;

-- 관리자용 보기: 지역·서비스 한글 라벨 포함 (대시보드 Table Editor 에서 조회)
create or replace view public.inquiries_admin as
select id, created_at, status,
  case province when 'seoul' then '서울' when 'incheon' then '인천' when 'gyeonggi' then '경기' when 'chungbuk' then '충북' when 'chungnam' then '충남' else province end as 권역,
  city as 세부지역,
  case service when 'onsite' then '상주 위탁' when 'duty' then '직무고시 대행' else '상주+직무고시' end as 서비스,
  case request_type when 'new' then '신규 상주선임' when 'change' then '위탁업체 변경' when 'transition' then '직접고용→위탁' else '조건부터 상담' end as 문의유형,
  case facility when 'factory' then '공장' when 'logistics' then '물류시설' when 'building' then '업무·상업용 건물' when 'construction' then '건설현장' else '기타' end as 시설,
  contact_name as 담당자, phone as 연락처, email as 이메일, capacity as 설비용량, message as 요청사항, entry_path as 유입페이지, memo as 메모, expires_at as 파기예정일
from public.inquiries order by created_at desc;
revoke all on public.inquiries_admin from anon, authenticated;
