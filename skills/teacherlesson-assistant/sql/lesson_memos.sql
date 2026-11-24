-- lesson_memos: 수업 메모(👍좋았음 🔧고칠점 📝메모 🎤음성메모 ▶단계 ⏱시스템)를 집·학교 PC 가 같이 보려고 두는 표.
--
-- 상태: **제안입니다. 아직 실행하지 않았습니다.** Supabase 대시보드의 SQL Editor 에서 교사가 내용을 확인한 뒤 실행합니다.
--       (여러 번 실행해도 되게 `if not exists` 로 썼습니다.)
--
-- 쓰는 쪽: skills/teacherlesson-assistant/memo_sync.py (push_session / pull)
--
-- ■ 보안 전제 (중요)
--   * 행 수준 보안(RLS)을 켜고 정책을 하나도 만들지 않습니다. 그러면 anon·authenticated 키로는 읽기·쓰기가 모두 막히고,
--     RLS 를 건너뛰는 service_role 키로만 접근됩니다.
--   * service_role 키는 중앙 .env 의 SUPABASE_SERVICE_ROLE_KEY 로만 두고, 로컬 Python(memo_sync.py)에서만 씁니다.
--     브라우저 화면(web/index.html)·깃·홈페이지에는 절대 넣지 않습니다.
--   * 메모에는 수업 중 적은 글이 그대로 들어갑니다. 🙋 학생 발표 메모(kind='student')는 이 표에 올리지 않기로 했습니다
--     (학생 기록 표는 따로 정함). memo_sync.py 가 올리기 전에 걸러냅니다.
--
-- ■ 열 설명
--   id         내부 번호(자동). memo_sync.py 의 내려받기 순서·쪽 나누기에 씀
--   date       수업 날짜
--   period     교시(숫자). 교시를 알 수 없으면 null
--   subject    과목
--   record_key 진도표 차시 키(lesson_lessons.legacy_lesson_id 와 같은 값). 진도표 밖 수업이면 빈 문자열
--   unit       대단원 이름, lesson 차시 번호(글자), title 수업 제목
--   kind       good(좋았음) fix(고칠점) note(메모) voice(음성메모) step(단계) sys(시스템) 외에 화면이 쓰는 star·adj.
--              새 종류가 생겨도 올리기가 막히지 않도록 check 제약은 두지 않았습니다.
--   text       메모 내용
--   t          메모를 적은 때. 녹음 중이면 녹음 기준 mm:ss, 아니면 시계 HH:MM (화면의 relTime() 값 그대로)
--   pc         어느 PC 에서 적었는지(중앙 .env 의 MEMO_PC, 없으면 컴퓨터 이름)
--   extra      화면이 되살릴 때 필요한 값: at(적은 시각 ISO), idx(단계 번호), delta(시간 조정 분).
--              ※ 요청한 열 목록에는 없지만, 다른 PC 에서 합칠 때 순서(at)와 '새로고침해도 단계 이어짐'(idx)을
--                잃지 않으려고 더했습니다. 필요 없으면 이 열과 memo_sync.py 의 extra 처리를 함께 빼면 됩니다.
--   memo_key   중복 방지용 고유값(날짜·교시·과목·적은 시각·종류·내용의 SHA-1). 같은 메모를 다시 올려도 한 번만 들어갑니다.
--   created_at 이 표에 들어온 시각(서버가 채움)

create table if not exists public.lesson_memos (
  id          bigint generated always as identity primary key,
  date        date        not null,
  period      smallint,
  subject     text        not null,
  record_key  text        not null default '',
  unit        text        not null default '',
  lesson      text        not null default '',
  title       text        not null default '',
  kind        text        not null,
  text        text        not null default '',
  t           text        not null default '',
  pc          text        not null default '',
  extra       jsonb       not null default '{}'::jsonb,
  memo_key    text        not null,
  created_at  timestamptz not null default now(),
  constraint lesson_memos_memo_key_key unique (memo_key)
);

-- 내려받기는 날짜 범위로 읽고(date >= …), 과목·날짜순으로 찾아볼 일이 많아서 둔다.
create index if not exists lesson_memos_date_idx         on public.lesson_memos (date);
create index if not exists lesson_memos_subject_date_idx on public.lesson_memos (subject, date desc);

-- RLS 켜기 + 정책 없음 = service_role 키 말고는 아무도 못 읽고 못 씀.
alter table public.lesson_memos enable row level security;

-- 겹쳐서 막아 둔다: 나중에 누가 실수로 정책을 만들어도 anon·authenticated 에 표 권한 자체가 없게.
revoke all on table public.lesson_memos from anon, authenticated;
