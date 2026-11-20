"""schema.sql 시험 (로컬 PostgreSQL 전용). 데이터베이스 t 에 /tmp/stubs.sql 로 auth 스텁을 만든 뒤 schema.sql, seed_questions.sql 을 적용하고 실행.
Supabase에는 실행하지 마세요(테스트 사용자를 만듭니다). stubs.sql 은 같은 폴더의 test_stubs.sql 참고."""
import subprocess, json, uuid, sys
def psql(sql, uid=None, role='authenticated', ok_fail=False):
    pre = ''
    if uid is not None or role:
        pre = f"set local role {role}; select set_config('request.jwt.claim.sub', '{uid or ''}', true);"
    full = f"begin; {pre} {sql}; commit;"
    r = subprocess.run(['su', 'postgres', '-c', f"psql -tA -v ON_ERROR_STOP=1 -d t -c \"{full}\""], capture_output=True, text=True)
    out = [l for l in r.stdout.strip().split('\n') if l and l not in ('BEGIN','COMMIT','SET') and not l.startswith('set_config')]
    return r.returncode, (out[-1] if out else ''), r.stderr.strip()
def admin(sql):  # superuser, no role switch
    r = subprocess.run(['su','postgres','-c',f"psql -tA -d t -c \"{sql}\""], capture_output=True, text=True)
    return r.stdout.strip()
def call(uid, sql):
    rc, out, err = psql(sql, uid)
    return rc, out, err
passed = failed = 0
def check(name, cond, extra=''):
    global passed, failed
    if cond: passed += 1; print('  OK ', name)
    else: failed += 1; print('  FAIL', name, extra)
A, B, C = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
for u in (A, B, C): admin(f"insert into auth.users values ('{u}')")
def err_has(res, text): return res[0] != 0 and text in res[2]

print('1) 등록')
ca = call(A, "select public.ensure_player('하늘','5-2')")[1]; cb = call(B, "select public.ensure_player('바다','5-2')")[1]; call(C, "select public.ensure_player('구름','6-1')")
check('코드 6자리', len(ca) == 6 and len(cb) == 6 and ca != cb, (ca, cb))
check('별명 13글자 거절', err_has(call(C, "select public.ensure_player('가나다라마바사아자차카타파','x')"), '1~12'))
check('로그인 없이 호출 거절', psql("select public.ensure_player('x')", uid='')[0] != 0)

print('2) 대결 시작')
check('내 코드로 시작 거절', err_has(call(A, f"select public.join_duel_by_code('{ca}')"), '나와는'))
check('없는 코드 거절', err_has(call(A, "select public.join_duel_by_code('ZZZZZZ')"), '찾을 수 없'))
did = call(B, f"select public.join_duel_by_code(lower('{ca}'))")[1]
check('대결 생성(소문자 코드도 허용)', len(did) == 36, did)
check('A가 활성 대결을 찾음', call(A, "select public.my_active_duel()")[1] == did)
check('이미 대결 중이면 다른 사람도 시작 불가', err_has(call(C, f"select public.join_duel_by_code('{ca}')"), '이미'))
check('제3자는 대결을 읽을 수 없음', err_has(call(C, f"select public.get_duel('{did}')"), '찾을 수 없'))

print('3) 정답이 새지 않음')
st = json.loads(call(A, f"select public.get_duel('{did}')")[1])
check('문제에 answer 키 없음', 'answer' not in json.dumps(st['question']) and set(st['question'].keys()) == {'body','choices'})
check('A는 p2(QR 보여 준 쪽)', st['i_am_p1'] is False and st['opp_nickname'] == '바다')
check('questions 표 직접 조회 거절', psql("select * from public.questions limit 1", uid=A)[0] != 0)
check('duels 직접 수정 거절', psql(f"update public.duels set p1_score=99 where id='{did}'", uid=A)[0] != 0)
check('내부 함수 resolve_round 호출 거절', psql(f"select public.resolve_round('{did}')", uid=A)[0] != 0)
check('player 표 직접 조회 거절', psql("select * from public.players", uid=A)[0] != 0)
check('duels 읽기는 내 것만 (제3자 0행)', call(C, "select count(*) from public.duels")[1] == '0')
check('duels 읽기 (참가자 1행)', call(A, "select count(*) from public.duels")[1] == '1')

def correct_of(round_no):
    return int(admin(f"select q.answer from public.duels d join public.questions q on q.id=d.q_ids[{round_no}] where d.id='{did}'"))
def state(uid): return json.loads(call(uid, f"select public.get_duel('{did}')")[1])

print('4) 라운드 1: B 정답, A 오답')
c1 = correct_of(1); wrong = (c1 + 1) % 4
r = json.loads(call(B, f"select public.submit_answer('{did}', {c1})")[1])
check('B 제출 후 my_done', r['my_done'] and not r['opp_done'])
sa = state(A); check('A 화면: 상대 답함 표시(내용은 모름)', sa['opp_done'] and not sa['my_done'] and sa['last_result'] is None)
r = json.loads(call(A, f"select public.submit_answer('{did}', {wrong})")[1])
check('양쪽 답하면 자동 채점 → 2라운드', r['round'] == 2 and r['my_score'] == 0 and r['opp_score'] == 10, r)
lr = r['last_result']; check('last_result 정답/선택 공개', lr['correct'] == c1 and lr['p1_choice'] == c1 and lr['p2_choice'] == wrong and lr['p1_points'] == 10)

print('5) 라운드 2: 둘 다 정답, A가 먼저(+3)')
c2 = correct_of(2)
call(A, f"select public.submit_answer('{did}', {c2})"); admin("select pg_sleep(0.05)")
dup = json.loads(call(A, f"select public.submit_answer('{did}', {(c2+1)%4})")[1])
check('같은 라운드 중복 제출 무시(여전히 2라운드, 답 바꿀 수 없음)', dup['round'] == 2 and dup['my_done'] and not dup['opp_done'], dup)
r = json.loads(call(B, f"select public.submit_answer('{did}', {c2})")[1])
check('A 13점, B 20점 → 3라운드', r['opp_score'] == 13 and r['my_score'] == 20 and r['round'] == 3, r)
check('채점은 A의 첫 답 기준(정답)', r['last_result']['p2_points'] == 13, r['last_result'])

print('6) 라운드 3: 한쪽만 답 → 시간 마감')
c3 = correct_of(3)
call(A, f"select public.submit_answer('{did}', {c3})")
r = json.loads(call(B, f"select public.tick_duel('{did}')")[1]); check('20초 전 tick은 마감 안 함', r['round'] == 3)
admin(f"update public.duels set round_started_at = now() - interval '21 seconds' where id='{did}'")
r = json.loads(call(B, f"select public.tick_duel('{did}')")[1])
check('20초 후 tick → 마감, A만 득점', r['round'] == 4 and r['opp_score'] == 23 and r['my_score'] == 20, r)
lr = r['last_result']; check('답 안 한 쪽 choice null', lr['p1_choice'] is None and lr['p2_choice'] == c3)

print('7) 라운드 4: 25초 넘긴 뒤 제출 → 마감 처리')
admin(f"update public.duels set round_started_at = now() - interval '26 seconds' where id='{did}'")
r = json.loads(call(B, f"select public.submit_answer('{did}', {correct_of(4)})")[1])
check('늦은 제출은 점수 없이 마감 → 5라운드', r['round'] == 5 and r['my_score'] == 20, r)

print('8) 라운드 5 → 종료')
c5 = correct_of(5)
call(A, f"select public.submit_answer('{did}', {c5})"); r = json.loads(call(B, f"select public.submit_answer('{did}', {c5})")[1])
check('종료·결과 표시', r['status'] == 'finished' and r['result'] in ('win','lose','draw'), r)
sa, sb = state(A), state(B)
check('A 승, B 패', sa['result'] == 'win' and sb['result'] == 'lose', (sa['result'], sb['result'], sa['my_score'], sb['my_score']))
check('종료 후 제출은 상태만 반환', json.loads(call(A, f"select public.submit_answer('{did}', 0)")[1])['status'] == 'finished')
check('종료 후 질문 숨김', sa['question'] is None)
check('종료 후 새 대결 가능', len(call(A, f"select public.join_duel_by_code('{cb}')")[1]) == 36)

print('9) 팀 순위/취소')
lb = call(C, "select json_agg(t) from public.team_leaderboard() t")[1]
check('팀 순위 집계(5-2 승1)', '"team":"5-2"' in lb.replace(' ', '') and '"wins":1' in lb.replace(' ', ''), lb)
d2 = call(A, "select public.my_active_duel()")[1]
call(A, f"select public.cancel_duel('{d2}')"); check('취소하면 활성 대결 없음', call(A, "select coalesce(public.my_active_duel()::text,'none')")[1] == 'none')
check('제3자는 취소 못 함(무시)', (call(C, f"select public.cancel_duel('{d2}')")[0] == 0))
print(f'\n통과 {passed} / 실패 {failed}')
sys.exit(1 if failed else 0)
