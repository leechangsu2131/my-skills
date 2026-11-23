-- =====================================================================
-- 학교 퀴즈 듀얼 (Supabase) — 테이블, 보안 규칙, 서버 함수
-- 사용법: Supabase 대시보드 > SQL Editor 에 이 파일 전체를 붙여 넣고 Run.
--         그다음 seed_questions.sql 도 같은 방법으로 실행.
-- 전제: Authentication > Sign In / Providers 에서 "Allow anonymous sign-ins" 켜기.
-- 원칙: 학생 정보는 별명(12자 이하)과 팀 이름(8자 이하, 예: 5-2반)만 저장. 실명·IP·위치 저장 없음.
--       정답·점수·승패는 모두 서버 함수가 정한다. 화면(브라우저)은 아무것도 판정하지 않는다.
-- =====================================================================

-- ---------- 테이블 ----------
create table if not exists public.players (
  id         uuid primary key references auth.users(id) on delete cascade,
  nickname   text not null check (char_length(nickname) between 1 and 12),
  team       text check (team is null or char_length(team) <= 8),
  code       text not null unique,                    -- 내 QR에 들어가는 6자리 초대 코드
  created_at timestamptz not null default now()
);

create table if not exists public.questions (
  id      serial primary key,
  topic   text not null default '일반',
  body    text not null,
  choices jsonb not null check (jsonb_typeof(choices) = 'array' and jsonb_array_length(choices) = 4),
  answer  int  not null check (answer between 0 and 3),   -- 정답 번호(0~3). 학생에게 절대 보내지 않음
  active  boolean not null default true
);

create table if not exists public.duels (
  id               uuid primary key default gen_random_uuid(),
  p1               uuid not null references public.players(id),   -- 코드를 찍은 사람
  p2               uuid not null references public.players(id),   -- QR을 보여 준 사람
  status           text not null default 'playing' check (status in ('playing','finished','cancelled')),
  total_rounds     int  not null default 5,
  round            int  not null default 1,
  q_ids            int[] not null,
  p1_score         int  not null default 0,
  p2_score         int  not null default 0,
  p1_done          boolean not null default false,                 -- 이번 라운드에 답했는지(무슨 답인지는 숨김)
  p2_done          boolean not null default false,
  round_started_at timestamptz not null default now(),
  last_result      jsonb,                                          -- 직전 라운드 결과(정답·양쪽 선택·점수)
  winner           uuid,
  created_at       timestamptz not null default now(),
  finished_at      timestamptz,
  check (p1 <> p2)
);
create index if not exists duels_p1_idx on public.duels (p1) where status = 'playing';
create index if not exists duels_p2_idx on public.duels (p2) where status = 'playing';

create table if not exists public.duel_answers (
  duel_id     uuid not null references public.duels(id) on delete cascade,
  round       int  not null,
  player      uuid not null,
  choice      int  not null check (choice between 0 and 3),
  correct     boolean not null,
  answered_at timestamptz not null default now(),
  primary key (duel_id, round, player)
);

-- ---------- 보안(RLS): 브라우저는 표를 직접 만지지 못하고 함수로만 한다 ----------
alter table public.players      enable row level security;
alter table public.questions    enable row level security;
alter table public.duels        enable row level security;
alter table public.duel_answers enable row level security;

revoke all on public.players, public.questions, public.duels, public.duel_answers from anon, authenticated;
revoke all on sequence public.questions_id_seq from anon, authenticated;

-- 실시간 알림(Postgres Changes)용: 대결 참가자만 자기 대결 행을 읽을 수 있다.
grant select on public.duels to authenticated;
drop policy if exists duels_participants_read on public.duels;
create policy duels_participants_read on public.duels
  for select to authenticated using (auth.uid() = p1 or auth.uid() = p2);

-- ---------- 내부 도우미 ----------
create or replace function public.new_code() returns text
language plpgsql as $$
declare
  alphabet constant text := 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  c text;
begin
  loop
    c := '';
    for i in 1..6 loop
      c := c || substr(alphabet, 1 + floor(random() * length(alphabet))::int, 1);
    end loop;
    exit when not exists (select 1 from public.players where code = c);
  end loop;
  return c;
end $$;

-- 라운드 하나를 마무리한다 (양쪽이 답했거나 시간이 끝났을 때). 호출자 보호를 위해 함수 안에서만 쓰인다.
create or replace function public.resolve_round(did uuid) returns void
language plpgsql security definer set search_path = public, pg_temp as $$
declare
  d public.duels; qa int; a1 public.duel_answers; a2 public.duel_answers;
  pts1 int := 0; pts2 int := 0; n1 int; n2 int;
begin
  select * into d from public.duels where id = did for update;
  if not found or d.status <> 'playing' then return; end if;

  select answer into qa from public.questions where id = d.q_ids[d.round];
  select * into a1 from public.duel_answers where duel_id = did and round = d.round and player = d.p1;
  select * into a2 from public.duel_answers where duel_id = did and round = d.round and player = d.p2;

  if a1.correct then pts1 := 10; end if;
  if a2.correct then pts2 := 10; end if;
  if a1.correct and a2.correct then                      -- 둘 다 맞히면 먼저 답한 쪽에 보너스 +3
    if a1.answered_at < a2.answered_at then pts1 := pts1 + 3;
    elsif a2.answered_at < a1.answered_at then pts2 := pts2 + 3; end if;
  end if;

  n1 := d.p1_score + pts1; n2 := d.p2_score + pts2;
  if d.round >= d.total_rounds then
    update public.duels set
      p1_score = n1, p2_score = n2, status = 'finished', finished_at = now(),
      winner = case when n1 > n2 then p1 when n2 > n1 then p2 else null end,
      last_result = jsonb_build_object('round', d.round, 'correct', qa, 'p1_choice', a1.choice, 'p2_choice', a2.choice, 'p1_points', pts1, 'p2_points', pts2)
    where id = did;
  else
    update public.duels set
      p1_score = n1, p2_score = n2, round = d.round + 1, p1_done = false, p2_done = false, round_started_at = now(),
      last_result = jsonb_build_object('round', d.round, 'correct', qa, 'p1_choice', a1.choice, 'p2_choice', a2.choice, 'p1_points', pts1, 'p2_points', pts2)
    where id = did;
  end if;
end $$;

-- ---------- 화면이 부르는 함수들 ----------
-- 1) 별명 등록(처음 한 번). 내 초대 코드를 돌려준다.
create or replace function public.ensure_player(nick text, team_in text default null) returns text
language plpgsql security definer set search_path = public, pg_temp as $$
declare uid uuid := auth.uid(); n text := btrim(coalesce(nick, '')); t text := nullif(btrim(coalesce(team_in, '')), ''); c text;
begin
  if uid is null then raise exception '로그인이 필요해요'; end if;
  if char_length(n) < 1 or char_length(n) > 12 then raise exception '별명은 1~12글자로 써 주세요'; end if;
  if t is not null and char_length(t) > 8 then raise exception '팀 이름은 8글자 이하로 써 주세요'; end if;
  select code into c from public.players where id = uid;
  if c is null then
    c := public.new_code();
    insert into public.players (id, nickname, team, code) values (uid, n, t, c);
  else
    update public.players set nickname = n, team = t where id = uid;
  end if;
  return c;
end $$;

-- 2) 내가 지금 하고 있는 대결(없으면 null)
create or replace function public.my_active_duel() returns uuid
language sql security definer set search_path = public, pg_temp stable as $$
  select id from public.duels
  where status = 'playing' and (p1 = auth.uid() or p2 = auth.uid()) and round_started_at > now() - interval '10 minutes'
  order by created_at desc limit 1
$$;

-- 3) 상대의 QR(코드)을 찍어서 대결 시작
create or replace function public.join_duel_by_code(opp_code text) returns uuid
language plpgsql security definer set search_path = public, pg_temp as $$
declare uid uuid := auth.uid(); opp uuid; qs int[]; did uuid;
begin
  if uid is null or not exists (select 1 from public.players where id = uid) then raise exception '먼저 별명을 정해 주세요'; end if;
  select id into opp from public.players where code = upper(btrim(coalesce(opp_code, '')));
  if opp is null then raise exception '코드를 찾을 수 없어요'; end if;
  if opp = uid then raise exception '나와는 대결할 수 없어요'; end if;

  perform pg_advisory_xact_lock(hashtext(least(uid, opp)::text || greatest(uid, opp)::text));
  update public.duels set status = 'cancelled', finished_at = now()                 -- 10분 넘게 멈춘 대결은 정리
   where status = 'playing' and round_started_at < now() - interval '10 minutes' and (p1 in (uid, opp) or p2 in (uid, opp));
  if exists (select 1 from public.duels where status = 'playing' and (p1 in (uid, opp) or p2 in (uid, opp))) then
    raise exception '둘 중 한 명이 이미 대결 중이에요';
  end if;

  select array_agg(id) into qs from (select id from public.questions where active order by random() limit 5) t;
  if qs is null or array_length(qs, 1) < 5 then raise exception '문제가 부족해요 (선생님께 알려 주세요)'; end if;
  insert into public.duels (p1, p2, q_ids, total_rounds) values (uid, opp, qs, 5) returning id into did;
  return did;
end $$;

-- 4) 대결 상태 읽기 (정답은 지난 라운드 것만 보여 줌)
create or replace function public.get_duel(did uuid) returns jsonb
language plpgsql security definer set search_path = public, pg_temp stable as $$
declare uid uuid := auth.uid(); d public.duels; me1 boolean; q public.questions; res text;
begin
  select * into d from public.duels where id = did;
  if not found or uid is null or uid not in (d.p1, d.p2) then raise exception '대결을 찾을 수 없어요'; end if;
  me1 := (d.p1 = uid);
  if d.status = 'playing' then select * into q from public.questions where id = d.q_ids[d.round]; end if;
  res := case when d.status <> 'finished' then null when d.winner is null then 'draw' when d.winner = uid then 'win' else 'lose' end;
  return jsonb_build_object(
    'id', d.id, 'status', d.status, 'round', d.round, 'total_rounds', d.total_rounds, 'i_am_p1', me1,
    'my_score', case when me1 then d.p1_score else d.p2_score end,
    'opp_score', case when me1 then d.p2_score else d.p1_score end,
    'my_done', case when me1 then d.p1_done else d.p2_done end,
    'opp_done', case when me1 then d.p2_done else d.p1_done end,
    'opp_nickname', (select nickname from public.players where id = case when me1 then d.p2 else d.p1 end),
    'question', case when d.status = 'playing' then jsonb_build_object('body', q.body, 'choices', q.choices) end,
    'round_started_at', d.round_started_at, 'server_now', now(), 'round_seconds', 20,
    'last_result', d.last_result, 'result', res);
end $$;

-- 5) 답 제출 (고른 번호 0~3). 양쪽이 모두 답하면 서버가 바로 채점하고 다음 라운드로.
create or replace function public.submit_answer(did uuid, ch int) returns jsonb
language plpgsql security definer set search_path = public, pg_temp as $$
declare uid uuid := auth.uid(); d public.duels; me1 boolean; qa int;
begin
  select * into d from public.duels where id = did for update;
  if not found or uid is null or uid not in (d.p1, d.p2) then raise exception '대결을 찾을 수 없어요'; end if;
  if d.status <> 'playing' then return public.get_duel(did); end if;
  if ch is null or ch < 0 or ch > 3 then raise exception '보기 번호가 올바르지 않아요'; end if;
  me1 := (d.p1 = uid);

  if now() > d.round_started_at + interval '25 seconds' then       -- 시간 초과: 이번 라운드는 답하지 않은 것으로 마감
    perform public.resolve_round(did);
    return public.get_duel(did);
  end if;
  if exists (select 1 from public.duel_answers where duel_id = did and round = d.round and player = uid) then
    return public.get_duel(did);                                      -- 이미 답함: 바꿀 수 없음
  end if;

  select answer into qa from public.questions where id = d.q_ids[d.round];
  insert into public.duel_answers (duel_id, round, player, choice, correct) values (did, d.round, uid, ch, ch = qa);
  if me1 then update public.duels set p1_done = true where id = did; else update public.duels set p2_done = true where id = did; end if;
  if (select p1_done and p2_done from public.duels where id = did) then perform public.resolve_round(did); end if;
  return public.get_duel(did);
end $$;

-- 6) 20초가 지났는데 한쪽이 답하지 않았으면 마감 (화면의 타이머가 끝나면 부름. 누가 불러도 한 번만 처리됨)
create or replace function public.tick_duel(did uuid) returns jsonb
language plpgsql security definer set search_path = public, pg_temp as $$
declare uid uuid := auth.uid(); d public.duels;
begin
  select * into d from public.duels where id = did for update;
  if not found or uid is null or uid not in (d.p1, d.p2) then raise exception '대결을 찾을 수 없어요'; end if;
  if d.status = 'playing' and now() >= d.round_started_at + interval '20 seconds' then perform public.resolve_round(did); end if;
  return public.get_duel(did);
end $$;

-- 7) 그만두기
create or replace function public.cancel_duel(did uuid) returns void
language plpgsql security definer set search_path = public, pg_temp as $$
begin
  update public.duels set status = 'cancelled', finished_at = now()
   where id = did and status = 'playing' and (p1 = auth.uid() or p2 = auth.uid());
end $$;

-- 8) 팀(학급) 순위: 개인 순위는 만들지 않는다
create or replace function public.team_leaderboard() returns table(team text, wins bigint, games bigint)
language sql security definer set search_path = public, pg_temp stable as $$
  with t as (
    select p.team, (d.winner = p.id) as won
    from public.duels d join public.players p on p.id in (d.p1, d.p2)
    where d.status = 'finished' and p.team is not null)
  select team, count(*) filter (where won) as wins, count(*) as games
  from t group by team order by wins desc, games desc limit 10
$$;

-- ---------- 함수 실행 권한: 로그인(익명 포함)한 사용자만, 내부 함수는 아무도 못 부름 ----------
revoke execute on all functions in schema public from public, anon, authenticated;
grant execute on function
  public.ensure_player(text, text), public.my_active_duel(), public.join_duel_by_code(text), public.get_duel(uuid),
  public.submit_answer(uuid, int), public.tick_duel(uuid), public.cancel_duel(uuid), public.team_leaderboard()
to authenticated;

-- 실시간 구독 대상에 duels 추가
do $$ begin
  if exists (select 1 from pg_publication where pubname = 'supabase_realtime')
     and not exists (select 1 from pg_publication_tables where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'duels') then
    alter publication supabase_realtime add table public.duels;
  end if;
end $$;
