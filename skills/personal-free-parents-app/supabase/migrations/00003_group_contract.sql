-- ============================================================
-- 00003_group_contract.sql
-- Align the existing parent-watch tables with the Flutter group flow.
-- This migration is additive: it preserves the original user_id-based schema.
-- ============================================================

begin;

-- App models expose location and verification metadata for affiliations.
alter table public.affiliations
  add column if not exists latitude double precision,
  add column if not exists longitude double precision,
  add column if not exists radius_m integer not null default 300;

alter table public.user_affiliations
  add column if not exists verification_level integer not null default 0;

-- Playgrounds remain independent locations; affiliation is optional context.
alter table public.playgrounds
  add column if not exists affiliation_id uuid references public.affiliations(id) on delete set null;

-- A group is a scheduled gathering at an official playground.
alter table public.groups
  add column if not exists affiliation_id uuid references public.affiliations(id) on delete set null,
  add column if not exists scheduled_start timestamptz,
  add column if not exists scheduled_end timestamptz,
  add column if not exists supervision_mode text not null default 'rotation',
  add column if not exists status text not null default 'pending';

update public.groups
set
  scheduled_start = coalesce(scheduled_start, created_at),
  scheduled_end = coalesce(scheduled_end, created_at + interval '2 hours'),
  supervision_mode = coalesce(supervision_mode, 'rotation'),
  status = coalesce(status, case when is_active then 'pending' else 'completed' end);

alter table public.groups
  alter column scheduled_start set not null,
  alter column scheduled_end set not null;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'groups_scheduled_range_check'
  ) then
    alter table public.groups add constraint groups_scheduled_range_check
      check (scheduled_end > scheduled_start);
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'groups_status_check'
  ) then
    alter table public.groups add constraint groups_status_check
      check (status in ('pending', 'active', 'completed', 'cancelled'));
  end if;
end $$;

create index if not exists idx_groups_affiliation_scheduled_start
  on public.groups (affiliation_id, scheduled_start);

-- Keep user_id as the canonical member identity used by existing RLS policies.
alter table public.group_members
  add column if not exists child_nickname text,
  add column if not exists child_age_range text,
  add column if not exists status text not null default 'joined',
  add column if not exists left_at timestamptz;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'group_members_status_check'
  ) then
    alter table public.group_members add constraint group_members_status_check
      check (status in ('joined', 'checked_in', 'left', 'no_show'));
  end if;
end $$;

-- Preserve the existing check-in record while adding the fields used by Flutter.
alter table public.checkins
  add column if not exists group_member_id uuid references public.group_members(id) on delete set null,
  add column if not exists latitude double precision,
  add column if not exists longitude double precision,
  add column if not exists checked_in_at timestamptz,
  add column if not exists method text not null default 'gps';

create index if not exists idx_checkins_group_member_id
  on public.checkins (group_member_id);

alter table public.playgrounds enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'playgrounds'
      and policyname = 'playgrounds_select_authenticated'
  ) then
    create policy "playgrounds_select_authenticated"
      on public.playgrounds for select
      using (auth.uid() is not null);
  end if;
end $$;

commit;
