-- Atomically create a group and its owner membership.
-- Apply 00003_group_contract.sql before this migration.

begin;

create or replace function public.create_group_with_owner(
  p_name text,
  p_affiliation_id uuid,
  p_playground_id uuid,
  p_scheduled_start timestamptz,
  p_scheduled_end timestamptz
)
returns uuid
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_user_id uuid := auth.uid();
  v_group_id uuid;
begin
  if v_user_id is null then
    raise exception using errcode = '42501', message = 'Authentication required';
  end if;

  if p_name is null or length(btrim(p_name)) = 0 or length(btrim(p_name)) > 80 then
    raise exception using errcode = '22023', message = 'Group name must be between 1 and 80 characters';
  end if;

  if p_scheduled_start is null or p_scheduled_start <= now() then
    raise exception using errcode = '22023', message = 'Group start time must be in the future';
  end if;

  if p_scheduled_end is null or p_scheduled_end <= p_scheduled_start then
    raise exception using errcode = '22023', message = 'Group end time must be after its start time';
  end if;

  if not exists (
    select 1
    from public.user_affiliations ua
    where ua.user_id = v_user_id
      and ua.affiliation_id = p_affiliation_id
  ) then
    raise exception using errcode = '42501', message = 'Selected affiliation is not linked to this account';
  end if;

  if not exists (
    select 1 from public.playgrounds p where p.id = p_playground_id
  ) then
    raise exception using errcode = '23503', message = 'Selected playground does not exist';
  end if;

  insert into public.groups (
    name,
    affiliation_id,
    playground_id,
    scheduled_start,
    scheduled_end,
    supervision_mode,
    status,
    created_by,
    is_active
  ) values (
    btrim(p_name),
    p_affiliation_id,
    p_playground_id,
    p_scheduled_start,
    p_scheduled_end,
    'full',
    'pending',
    v_user_id,
    true
  ) returning id into v_group_id;

  insert into public.group_members (group_id, user_id, role)
  values (v_group_id, v_user_id, 'owner');

  return v_group_id;
end;
$$;

revoke all on function public.create_group_with_owner(text, uuid, uuid, timestamptz, timestamptz)
  from public, anon;
grant execute on function public.create_group_with_owner(text, uuid, uuid, timestamptz, timestamptz)
  to authenticated;

commit;
