-- ============================================================
-- 00001_initial_schema.sql
-- Free Parents App – Initial Database Schema
-- Created: 2026-06-30
-- ============================================================

-- ============================================================
-- 1. EXTENSIONS
-- ============================================================
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- ============================================================
-- 2. CUSTOM TYPES (ENUMs)
-- ============================================================
create type user_role as enum ('parent', 'helper', 'admin');
create type group_role as enum ('owner', 'admin', 'member');
create type checkin_type as enum ('drop_off', 'pick_up');
create type checkin_status as enum ('pending', 'confirmed', 'cancelled');
create type supervision_status as enum ('requested', 'accepted', 'declined', 'in_progress', 'completed', 'cancelled');
create type report_status as enum ('pending', 'reviewing', 'resolved', 'dismissed');
create type flag_status as enum ('active', 'resolved', 'expired');
create type trust_event_type as enum (
  'checkin_completed',
  'supervision_completed',
  'positive_report',
  'negative_report',
  'vouch_received',
  'affiliation_verified',
  'safety_flag_issued',
  'manual_adjustment'
);
create type consent_action as enum ('granted', 'revoked');

-- ============================================================
-- 3. TABLES
-- ============================================================

-- -----------------------------------------------------------
-- 3-1. users – 사용자 프로필 (auth.users 연동)
-- -----------------------------------------------------------
create table users (
  id            uuid primary key references auth.users(id) on delete cascade,
  email         text unique not null,
  display_name  text not null,
  phone         text,
  avatar_url    text,
  role          user_role not null default 'parent',
  trust_score   numeric not null default 50,
  bio           text,
  is_active     boolean not null default true,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

comment on table users is '사용자 프로필 – auth.users와 1:1 매핑';

-- -----------------------------------------------------------
-- 3-2. affiliations – 소속 기관 (학교, 어린이집 등)
-- -----------------------------------------------------------
create table affiliations (
  id              uuid primary key default uuid_generate_v4(),
  name            text not null,
  type            text not null,          -- 'school', 'daycare', 'academy', etc.
  address         text,
  verified        boolean not null default false,
  verification_code text unique,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

comment on table affiliations is '소속 기관 (학교, 어린이집, 학원 등)';

-- -----------------------------------------------------------
-- 3-3. user_affiliations – 사용자-소속 매핑 (M:N)
-- -----------------------------------------------------------
create table user_affiliations (
  id              uuid primary key default uuid_generate_v4(),
  user_id         uuid not null references users(id) on delete cascade,
  affiliation_id  uuid not null references affiliations(id) on delete cascade,
  verified        boolean not null default false,
  verified_at     timestamptz,
  created_at      timestamptz not null default now(),
  unique (user_id, affiliation_id)
);

comment on table user_affiliations is '사용자 ↔ 소속 기관 연결 (다대다)';

-- -----------------------------------------------------------
-- 3-4. groups – 돌봄 그룹
-- -----------------------------------------------------------
create table groups (
  id              uuid primary key default uuid_generate_v4(),
  name            text not null,
  description     text,
  affiliation_id  uuid references affiliations(id) on delete set null,
  invite_code     text unique,
  max_members     int not null default 20,
  is_active       boolean not null default true,
  created_by      uuid not null references users(id) on delete cascade,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

comment on table groups is '돌봄 그룹 (학부모 커뮤니티 단위)';

-- -----------------------------------------------------------
-- 3-5. group_members – 그룹 멤버십
-- -----------------------------------------------------------
create table group_members (
  id          uuid primary key default uuid_generate_v4(),
  group_id    uuid not null references groups(id) on delete cascade,
  user_id     uuid not null references users(id) on delete cascade,
  role        group_role not null default 'member',
  joined_at   timestamptz not null default now(),
  unique (group_id, user_id)
);

comment on table group_members is '그룹 멤버십 – 한 사용자가 여러 그룹에 소속 가능';

-- -----------------------------------------------------------
-- 3-6. checkins – 체크인/체크아웃 기록
-- -----------------------------------------------------------
create table checkins (
  id              uuid primary key default uuid_generate_v4(),
  group_id        uuid not null references groups(id) on delete cascade,
  child_name      text not null,
  parent_id       uuid not null references users(id) on delete cascade,
  helper_id       uuid references users(id) on delete set null,
  type            checkin_type not null,
  status          checkin_status not null default 'pending',
  scheduled_at    timestamptz not null,
  confirmed_at    timestamptz,
  notes           text,
  location_lat    double precision,
  location_lng    double precision,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

comment on table checkins is '아이 인수인계(체크인/체크아웃) 기록';

-- -----------------------------------------------------------
-- 3-7. supervision_sessions – 돌봄 세션
-- -----------------------------------------------------------
create table supervision_sessions (
  id              uuid primary key default uuid_generate_v4(),
  group_id        uuid not null references groups(id) on delete cascade,
  title           text not null,
  description     text,
  location        text,
  max_children    int not null default 5,
  start_time      timestamptz not null,
  end_time        timestamptz not null,
  status          supervision_status not null default 'requested',
  supervisor_id   uuid not null references users(id) on delete cascade,
  created_by      uuid not null references users(id) on delete cascade,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

comment on table supervision_sessions is '돌봄 세션 (그룹 내 공동 돌봄 일정)';

-- -----------------------------------------------------------
-- 3-8. supervision_assignments – 돌봄 배정 (아이 ↔ 세션)
-- -----------------------------------------------------------
create table supervision_assignments (
  id              uuid primary key default uuid_generate_v4(),
  session_id      uuid not null references supervision_sessions(id) on delete cascade,
  group_id        uuid not null references groups(id) on delete cascade,
  child_name      text not null,
  parent_id       uuid not null references users(id) on delete cascade,
  status          supervision_status not null default 'requested',
  notes           text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

comment on table supervision_assignments is '돌봄 세션에 아이를 배정하는 레코드';

-- -----------------------------------------------------------
-- 3-9. trust_score_events – 신뢰 점수 이벤트 로그
-- -----------------------------------------------------------
create table trust_score_events (
  id              uuid primary key default uuid_generate_v4(),
  user_id         uuid not null references users(id) on delete cascade,
  event_type      trust_event_type not null,
  base_score      numeric not null default 0,
  half_life_days  numeric,               -- NULL = 영구 반영
  description     text,
  reference_id    uuid,                  -- 관련 엔티티 참조 (체크인, 리포트 등)
  created_at      timestamptz not null default now()
);

comment on table trust_score_events is '신뢰 점수 변동 이벤트 (시간 감쇄 모델)';

-- -----------------------------------------------------------
-- 3-10. reports – 신고/피드백
-- -----------------------------------------------------------
create table reports (
  id              uuid primary key default uuid_generate_v4(),
  reporter_id     uuid not null references users(id) on delete cascade,
  reported_user_id uuid not null references users(id) on delete cascade,
  group_id        uuid references groups(id) on delete set null,
  title           text not null,
  description     text not null,
  status          report_status not null default 'pending',
  admin_notes     text,
  resolved_at     timestamptz,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

comment on table reports is '사용자 신고 및 피드백 기록';

-- -----------------------------------------------------------
-- 3-11. safety_flags – 안전 플래그 (관리자 전용)
-- -----------------------------------------------------------
create table safety_flags (
  id              uuid primary key default uuid_generate_v4(),
  user_id         uuid not null references users(id) on delete cascade,
  reason          text not null,
  status          flag_status not null default 'active',
  flagged_by      uuid not null references users(id) on delete cascade,
  resolved_by     uuid references users(id) on delete set null,
  resolved_at     timestamptz,
  expires_at      timestamptz,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

comment on table safety_flags is '안전 플래그 – 관리자가 특정 사용자에 부여';

-- -----------------------------------------------------------
-- 3-12. affiliation_vouches – 소속 보증
-- -----------------------------------------------------------
create table affiliation_vouches (
  id              uuid primary key default uuid_generate_v4(),
  voucher_id      uuid not null references users(id) on delete cascade,
  vouchee_id      uuid not null references users(id) on delete cascade,
  affiliation_id  uuid not null references affiliations(id) on delete cascade,
  message         text,
  created_at      timestamptz not null default now(),
  unique (voucher_id, vouchee_id, affiliation_id)
);

comment on table affiliation_vouches is '소속 보증 – 기존 회원이 신규 회원을 보증';

-- -----------------------------------------------------------
-- 3-13. consent_logs – 동의 기록
-- -----------------------------------------------------------
create table consent_logs (
  id              uuid primary key default uuid_generate_v4(),
  user_id         uuid not null references users(id) on delete cascade,
  consent_type    text not null,          -- 'terms_of_service', 'privacy_policy', 'photo_sharing', etc.
  action          consent_action not null,
  ip_address      inet,
  user_agent      text,
  created_at      timestamptz not null default now()
);

comment on table consent_logs is '사용자 동의/철회 기록 (법적 추적용)';

-- ============================================================
-- 4. INDEXES – 자주 조회되는 외래 키 및 컬럼
-- ============================================================

-- users
create index idx_users_email on users(email);
create index idx_users_role on users(role);

-- user_affiliations
create index idx_user_affiliations_user_id on user_affiliations(user_id);
create index idx_user_affiliations_affiliation_id on user_affiliations(affiliation_id);

-- groups
create index idx_groups_affiliation_id on groups(affiliation_id);
create index idx_groups_created_by on groups(created_by);
create index idx_groups_invite_code on groups(invite_code);

-- group_members
create index idx_group_members_group_id on group_members(group_id);
create index idx_group_members_user_id on group_members(user_id);

-- checkins
create index idx_checkins_group_id on checkins(group_id);
create index idx_checkins_parent_id on checkins(parent_id);
create index idx_checkins_helper_id on checkins(helper_id);
create index idx_checkins_scheduled_at on checkins(scheduled_at);
create index idx_checkins_status on checkins(status);

-- supervision_sessions
create index idx_supervision_sessions_group_id on supervision_sessions(group_id);
create index idx_supervision_sessions_supervisor_id on supervision_sessions(supervisor_id);
create index idx_supervision_sessions_start_time on supervision_sessions(start_time);
create index idx_supervision_sessions_status on supervision_sessions(status);

-- supervision_assignments
create index idx_supervision_assignments_session_id on supervision_assignments(session_id);
create index idx_supervision_assignments_group_id on supervision_assignments(group_id);
create index idx_supervision_assignments_parent_id on supervision_assignments(parent_id);

-- trust_score_events
create index idx_trust_score_events_user_id on trust_score_events(user_id);
create index idx_trust_score_events_event_type on trust_score_events(event_type);
create index idx_trust_score_events_created_at on trust_score_events(created_at);

-- reports
create index idx_reports_reporter_id on reports(reporter_id);
create index idx_reports_reported_user_id on reports(reported_user_id);
create index idx_reports_group_id on reports(group_id);
create index idx_reports_status on reports(status);

-- safety_flags
create index idx_safety_flags_user_id on safety_flags(user_id);
create index idx_safety_flags_status on safety_flags(status);
create index idx_safety_flags_flagged_by on safety_flags(flagged_by);

-- affiliation_vouches
create index idx_affiliation_vouches_voucher_id on affiliation_vouches(voucher_id);
create index idx_affiliation_vouches_vouchee_id on affiliation_vouches(vouchee_id);
create index idx_affiliation_vouches_affiliation_id on affiliation_vouches(affiliation_id);

-- consent_logs
create index idx_consent_logs_user_id on consent_logs(user_id);
create index idx_consent_logs_consent_type on consent_logs(consent_type);

-- ============================================================
-- 5. RPC FUNCTIONS
-- ============================================================

-- -----------------------------------------------------------
-- 5-1. calculate_trust_score – 시간 감쇄 기반 신뢰 점수 계산
-- -----------------------------------------------------------
create or replace function calculate_trust_score(target_user_id uuid)
returns numeric as $$
declare
  base numeric := 50;
  total numeric := 0;
  event record;
  days_elapsed numeric;
  decay_factor numeric;
begin
  for event in
    select * from trust_score_events where user_id = target_user_id
  loop
    days_elapsed := extract(epoch from (now() - event.created_at)) / 86400;
    if event.half_life_days is null then
      decay_factor := 1;
    else
      decay_factor := power(0.5, days_elapsed / event.half_life_days);
    end if;
    total := total + (event.base_score * decay_factor);
  end loop;
  return greatest(0, least(100, base + total));
end;
$$ language plpgsql;

comment on function calculate_trust_score(uuid) is '시간 감쇄 모델 기반으로 사용자 신뢰 점수를 계산 (0~100)';

-- -----------------------------------------------------------
-- 5-2. is_safety_flagged – 안전 플래그 여부 확인
-- -----------------------------------------------------------
create or replace function is_safety_flagged(target_user_id uuid)
returns boolean as $$
begin
  return exists (
    select 1
    from safety_flags
    where user_id = target_user_id
      and status = 'active'
      and (expires_at is null or expires_at > now())
  );
end;
$$ language plpgsql;

comment on function is_safety_flagged(uuid) is '해당 사용자에게 활성 안전 플래그가 있는지 확인';

-- ============================================================
-- 6. TRIGGERS
-- ============================================================

-- -----------------------------------------------------------
-- 6-1. updated_at 자동 갱신 트리거 함수
-- -----------------------------------------------------------
create or replace function update_updated_at_column()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

-- updated_at 트리거 적용 (updated_at 컬럼이 있는 모든 테이블)
create trigger trg_users_updated_at
  before update on users for each row execute function update_updated_at_column();

create trigger trg_affiliations_updated_at
  before update on affiliations for each row execute function update_updated_at_column();

create trigger trg_groups_updated_at
  before update on groups for each row execute function update_updated_at_column();

create trigger trg_checkins_updated_at
  before update on checkins for each row execute function update_updated_at_column();

create trigger trg_supervision_sessions_updated_at
  before update on supervision_sessions for each row execute function update_updated_at_column();

create trigger trg_supervision_assignments_updated_at
  before update on supervision_assignments for each row execute function update_updated_at_column();

create trigger trg_reports_updated_at
  before update on reports for each row execute function update_updated_at_column();

create trigger trg_safety_flags_updated_at
  before update on safety_flags for each row execute function update_updated_at_column();

-- -----------------------------------------------------------
-- 6-2. Auth 회원가입 시 users 프로필 자동 생성 트리거
-- -----------------------------------------------------------
create or replace function handle_new_auth_user()
returns trigger as $$
begin
  insert into public.users (id, email, display_name, role, trust_score)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'display_name', split_part(new.email, '@', 1)),
    'parent',
    50
  );
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function handle_new_auth_user();

comment on function handle_new_auth_user() is 'auth.users 가입 시 public.users 프로필 자동 생성';

-- ============================================================
-- 7. ROW LEVEL SECURITY (RLS)
-- ============================================================

-- -----------------------------------------------------------
-- 7-0. Enable RLS on ALL tables
-- -----------------------------------------------------------
alter table users enable row level security;
alter table affiliations enable row level security;
alter table user_affiliations enable row level security;
alter table groups enable row level security;
alter table group_members enable row level security;
alter table checkins enable row level security;
alter table supervision_sessions enable row level security;
alter table supervision_assignments enable row level security;
alter table trust_score_events enable row level security;
alter table reports enable row level security;
alter table safety_flags enable row level security;
alter table affiliation_vouches enable row level security;
alter table consent_logs enable row level security;

-- -----------------------------------------------------------
-- Helper: 현재 사용자가 특정 그룹에 속해 있는지 확인
-- -----------------------------------------------------------
create or replace function is_group_member(check_group_id uuid)
returns boolean as $$
begin
  return exists (
    select 1 from group_members
    where group_id = check_group_id
      and user_id = auth.uid()
  );
end;
$$ language plpgsql security definer;

-- Helper: 현재 사용자가 admin 역할인지 확인
create or replace function is_admin()
returns boolean as $$
begin
  return exists (
    select 1 from users
    where id = auth.uid()
      and role = 'admin'
  );
end;
$$ language plpgsql security definer;

-- -----------------------------------------------------------
-- 7-1. users – 자신의 행만 읽기/수정 가능
-- -----------------------------------------------------------
create policy "users_select_own"
  on users for select
  using (id = auth.uid());

create policy "users_update_own"
  on users for update
  using (id = auth.uid())
  with check (id = auth.uid());

-- 같은 그룹원의 프로필은 읽기 허용 (그룹 기능에 필요)
create policy "users_select_group_members"
  on users for select
  using (
    exists (
      select 1 from group_members gm1
      join group_members gm2 on gm1.group_id = gm2.group_id
      where gm1.user_id = auth.uid()
        and gm2.user_id = users.id
    )
  );

-- -----------------------------------------------------------
-- 7-2. affiliations – 인증된 사용자 모두 읽기 가능
-- -----------------------------------------------------------
create policy "affiliations_select_authenticated"
  on affiliations for select
  using (auth.uid() is not null);

create policy "affiliations_insert_admin"
  on affiliations for insert
  with check (is_admin());

create policy "affiliations_update_admin"
  on affiliations for update
  using (is_admin())
  with check (is_admin());

-- -----------------------------------------------------------
-- 7-3. user_affiliations – 자신의 소속만 관리
-- -----------------------------------------------------------
create policy "user_affiliations_select_own"
  on user_affiliations for select
  using (user_id = auth.uid());

create policy "user_affiliations_insert_own"
  on user_affiliations for insert
  with check (user_id = auth.uid());

create policy "user_affiliations_delete_own"
  on user_affiliations for delete
  using (user_id = auth.uid());

-- -----------------------------------------------------------
-- 7-4. groups – 그룹원이면 읽기, 생성은 인증 사용자
-- -----------------------------------------------------------
create policy "groups_select_member"
  on groups for select
  using (is_group_member(id) or created_by = auth.uid());

create policy "groups_insert_authenticated"
  on groups for insert
  with check (auth.uid() is not null);

create policy "groups_update_owner"
  on groups for update
  using (created_by = auth.uid())
  with check (created_by = auth.uid());

-- -----------------------------------------------------------
-- 7-5. group_members – 같은 그룹 내에서만 SELECT
-- -----------------------------------------------------------
create policy "group_members_select_same_group"
  on group_members for select
  using (is_group_member(group_id));

create policy "group_members_insert_self"
  on group_members for insert
  with check (user_id = auth.uid());

create policy "group_members_delete_self_or_admin"
  on group_members for delete
  using (
    user_id = auth.uid()
    or exists (
      select 1 from group_members
      where group_id = group_members.group_id
        and user_id = auth.uid()
        and role in ('owner', 'admin')
    )
  );

-- -----------------------------------------------------------
-- 7-6. checkins – 같은 그룹 내에서만 SELECT
-- -----------------------------------------------------------
create policy "checkins_select_same_group"
  on checkins for select
  using (is_group_member(group_id));

create policy "checkins_insert_parent"
  on checkins for insert
  with check (parent_id = auth.uid() and is_group_member(group_id));

create policy "checkins_update_involved"
  on checkins for update
  using (parent_id = auth.uid() or helper_id = auth.uid())
  with check (parent_id = auth.uid() or helper_id = auth.uid());

-- -----------------------------------------------------------
-- 7-7. supervision_sessions – 그룹원만 조회
-- -----------------------------------------------------------
create policy "supervision_sessions_select_group"
  on supervision_sessions for select
  using (is_group_member(group_id));

create policy "supervision_sessions_insert_group"
  on supervision_sessions for insert
  with check (is_group_member(group_id) and created_by = auth.uid());

create policy "supervision_sessions_update_supervisor"
  on supervision_sessions for update
  using (supervisor_id = auth.uid() or created_by = auth.uid());

-- -----------------------------------------------------------
-- 7-8. supervision_assignments – 같은 그룹 내에서만 SELECT
-- -----------------------------------------------------------
create policy "supervision_assignments_select_group"
  on supervision_assignments for select
  using (is_group_member(group_id));

create policy "supervision_assignments_insert_parent"
  on supervision_assignments for insert
  with check (parent_id = auth.uid() and is_group_member(group_id));

create policy "supervision_assignments_update_involved"
  on supervision_assignments for update
  using (parent_id = auth.uid());

-- -----------------------------------------------------------
-- 7-9. trust_score_events – 자신의 이벤트만 조회
-- -----------------------------------------------------------
create policy "trust_score_events_select_own"
  on trust_score_events for select
  using (user_id = auth.uid());

create policy "trust_score_events_insert_system"
  on trust_score_events for insert
  with check (is_admin());

-- -----------------------------------------------------------
-- 7-10. reports – 신고자 또는 admin만 조회
-- -----------------------------------------------------------
create policy "reports_select_reporter_or_admin"
  on reports for select
  using (reporter_id = auth.uid() or is_admin());

create policy "reports_insert_authenticated"
  on reports for insert
  with check (reporter_id = auth.uid());

create policy "reports_update_admin"
  on reports for update
  using (is_admin());

-- -----------------------------------------------------------
-- 7-11. safety_flags – admin만 관리
-- -----------------------------------------------------------
create policy "safety_flags_select_admin"
  on safety_flags for select
  using (is_admin());

create policy "safety_flags_insert_admin"
  on safety_flags for insert
  with check (is_admin());

create policy "safety_flags_update_admin"
  on safety_flags for update
  using (is_admin())
  with check (is_admin());

create policy "safety_flags_delete_admin"
  on safety_flags for delete
  using (is_admin());

-- -----------------------------------------------------------
-- 7-12. affiliation_vouches – 보증 관련
-- -----------------------------------------------------------
create policy "affiliation_vouches_select_involved"
  on affiliation_vouches for select
  using (voucher_id = auth.uid() or vouchee_id = auth.uid());

create policy "affiliation_vouches_insert_voucher"
  on affiliation_vouches for insert
  with check (voucher_id = auth.uid());

-- -----------------------------------------------------------
-- 7-13. consent_logs – 자신의 기록만 조회
-- -----------------------------------------------------------
create policy "consent_logs_select_own"
  on consent_logs for select
  using (user_id = auth.uid());

create policy "consent_logs_insert_own"
  on consent_logs for insert
  with check (user_id = auth.uid());

-- ============================================================
-- MIGRATION COMPLETE
-- ============================================================
