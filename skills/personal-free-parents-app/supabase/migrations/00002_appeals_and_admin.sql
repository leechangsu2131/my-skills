-- ============================================================
-- 00002_appeals_and_admin.sql
-- Appeals and Admin Actions Schema
-- ============================================================

-- 1. TABLES

-- -----------------------------------------------------------
-- appeals – 신고/조치 이의제기
-- -----------------------------------------------------------
create table appeals (
  id              uuid primary key default gen_random_uuid(),
  report_id       uuid not null references reports(id) on delete cascade,
  safety_flag_id  uuid references safety_flags(id) on delete set null,
  appellant_id    uuid not null references users(id) on delete cascade,
  explanation     text not null,
  evidence_urls   text[],
  status          varchar not null default 'pending', -- 'pending', 'reviewed', 'resolved'
  submitted_at    timestamptz not null default now(),
  reviewed_at     timestamptz,
  reviewed_by     uuid references users(id) on delete set null,
  review_note     text
);

comment on table appeals is '신고 또는 계정 차단 조치에 대한 사용자 이의제기 로그';

-- -----------------------------------------------------------
-- admin_actions – 관리자 조치 로그
-- -----------------------------------------------------------
create table admin_actions (
  id                 uuid primary key default gen_random_uuid(),
  admin_id           uuid not null references users(id) on delete cascade,
  action_type        varchar not null,                      -- 'suspend_user', 'resolve_report', etc.
  target_user_id     uuid references users(id) on delete set null,
  related_report_id  uuid references reports(id) on delete set null,
  related_appeal_id  uuid references appeals(id) on delete set null,
  reason             text not null,
  created_at         timestamptz not null default now()
);

comment on table admin_actions is '관리자의 징계 및 조치 이력 로그 (내부 감사용)';

-- 2. INDEXES
create index idx_appeals_report_id on appeals(report_id);
create index idx_appeals_appellant_id on appeals(appellant_id);
create index idx_appeals_status on appeals(status);
create index idx_admin_actions_admin_id on admin_actions(admin_id);
create index idx_admin_actions_target_user_id on admin_actions(target_user_id);

-- 3. ROW LEVEL SECURITY (RLS)
alter table appeals enable row level security;
alter table admin_actions enable row level security;

-- appeals RLS Policies
create policy "appeals_select_involved"
  on appeals for select
  using (appellant_id = auth.uid() or is_admin());

create policy "appeals_insert_appellant"
  on appeals for insert
  with check (appellant_id = auth.uid());

create policy "appeals_update_admin"
  on appeals for update
  using (is_admin())
  with check (is_admin());

-- admin_actions RLS Policies
create policy "admin_actions_select_admin"
  on admin_actions for select
  using (is_admin());

create policy "admin_actions_insert_admin"
  on admin_actions for insert
  with check (is_admin());
