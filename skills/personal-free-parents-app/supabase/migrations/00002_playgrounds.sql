-- ============================================================
-- 00002_playgrounds.sql
-- Gyeongju Centum Sky Daycare & Playground Real Data Integration
-- ============================================================

-- 1. 신규 놀이터(playgrounds) 마스터 테이블 생성
-- 타 서비스 테이블과 충돌하지 않도록 명확하게 parent_watch 관련 도메인용으로 생성
create table public.playgrounds (
  id              uuid primary key default uuid_generate_v4(),
  name            text not null,          -- 예: "건천초 앞 놀이터", "센텀스카이 중앙 놀이터"
  latitude        double precision not null,
  longitude       double precision not null,
  affiliation_id  uuid references public.affiliations(id) on delete set null, -- 인근 대표 소속 기관
  is_verified     boolean not null default false, -- 공식 등록 여부
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

comment on table public.playgrounds is '돌봄 대상 놀이터 마스터 정보';

-- updated_at 자동 갱신 트리거 적용
create trigger trg_playgrounds_updated_at
  before update on public.playgrounds for each row execute function update_updated_at_column();

-- playgrounds RLS 활성화
alter table public.playgrounds enable row level security;

-- 누구나 조회 가능 (인증된 사용자 대상)
create policy "playgrounds_select_authenticated"
  on public.playgrounds for select
  using (auth.uid() is not null);

-- 생성/수정/삭제는 admin만 가능
create policy "playgrounds_all_admin"
  on public.playgrounds for all
  using (is_admin())
  with check (is_admin());


-- 2. 기존 groups 테이블 수정 (자유입력 방지 및 놀이터 마스터 연동)
-- 타 학생/물품 서비스에 영향을 미치지 않도록 오직 groups 테이블만 조심스럽게 수정
alter table public.groups
  add column playground_id uuid references public.playgrounds(id) on delete set null;

comment on column public.groups.playground_id is '그룹이 지정된 공식 놀이터 ID';


-- 3. 파일럿용 경주 신경주역세권 실데이터 주입 (소속 6개 + 놀이터 4개)
-- 타 서비스 ID나 시퀀스에 혼선이 없도록 임의의 표준 36자리 uuidv4를 생성하여 독립적으로 데이터 insert

-- A. 소속 기관 (어린이집 3곳 + 아파트 3곳)
insert into public.affiliations (id, name, type, address, verified) values
  ('11111111-1111-4111-a111-111111111111', '천년가 센텀스카이 아파트', 'apartment', '경상북도 경주시 건천읍 경주역세권1로 75', true),
  ('22222222-2222-4222-a222-222222222222', '해링턴플레이스 신경주역 아파트', 'apartment', '경상북도 경주시 건천읍 화천리 953-2', true),
  ('33333333-3333-4333-a333-333333333333', '신경주 더퍼스트 데시앙 아파트', 'apartment', '경상북도 경주시 건천읍 화천리 1032', true),
  ('44444444-4444-4444-a444-444444444444', '방주 어린이집', 'daycare', '경상북도 경주시 건천읍 천포우회길 63', true),
  ('55555555-5555-4555-a555-555555555555', '라라 어린이집', 'daycare', '경상북도 경주시 건천읍 건천시장길 22', true),
  ('66666666-6666-4666-a666-666666666666', '미래 어린이집', 'daycare', '경상북도 경주시 건천읍 건천중앙길 59-15', true);

-- B. 각 소속 기관 주변 놀이터 실데이터 (경주 센텀스카이 및 건천읍 일대 4곳)
insert into public.playgrounds (id, name, latitude, longitude, affiliation_id, is_verified) values
  -- 천년가 센텀스카이 단지 내 중앙 놀이터 (Gyeongju Daycare 바로 근처)
  ('11111111-1111-4111-b111-111111111112', '센텀스카이 중앙 놀이터', 35.804879, 129.138367, '11111111-1111-4111-a111-111111111111', true),
  -- 해링턴플레이스 신경주역 아파트 놀이터
  ('22222222-2222-4222-b222-222222222222', '해링턴플레이스 어린이 놀이터', 35.804540, 129.135862, '22222222-2222-4222-a222-222222222222', true),
  -- 신경주 더퍼스트 데시앙 아파트 놀이터
  ('33333333-3333-4333-b333-333333333333', '더퍼스트 데시앙 숲속 놀이터', 35.801884, 129.138390, '33333333-3333-4333-a333-333333333333', true),
  -- 건천초등학교 앞 어린이 공원 놀이터 (방주/라라어린이집 원아들이 자주 찾음)
  ('44444444-4444-4444-b444-444444444445', '건천초 앞 어린이 공원 놀이터', 35.803500, 129.137000, '55555555-5555-4555-a555-555555555555', true);
