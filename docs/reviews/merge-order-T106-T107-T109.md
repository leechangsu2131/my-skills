# 검토 모음: PR #179(T106)·#181(T109)·#183(T107) 함께 합치기

세 PR 은 모두 `assistant_server.py` 의 `import` 줄과 길 안내 줄 바로 옆(그리고 T106·T109 는 `web/index.html` 의 `<script>` 줄 바로 옆)에 **줄을 하나씩 더해서**, 하나를 먼저 합치면 나머지는 충돌이 남. 내용이 부딪히는 것이 아니라 '둘 다 남기면 되는' 충돌임.

- 합쳐 본 결과(내 컴퓨터에서 시험 삼아): 세 PR 을 순서대로 합치고 충돌마다 **양쪽 줄을 모두 남겨** 풀면, `assistant_server.py` 문법 정상, `index.html` 에 `ment.js`·`agenda.js`·`school_info.js`·`overdue.js`·`recording_export.js` 가 한 번씩, 그 폴더 `pytest tests` **555 통과**(기존 xfail 4), 수업 비서 서버 시험 88개, `node` 시험(ment 13·agenda 8·school_info 6·recording_export 5) 통과.
- 권하는 순서: 먼저 **#183(T107)**·**#179(T106)** 처럼 고칠 것이 없는 것부터 하나씩 합치고, 나머지는 작성자가 `main` 을 받아 충돌 줄을 양쪽 남기기로 풀어 다시 올림. **#181(T109)** 은 설정 이름을 고칠 때 같이 하면 한 번에 끝남.
- 교사 PC 의 `merge_ready.py` 가 충돌로 멈추면 위 방법(양쪽 줄 남기기)으로 풀면 됨.
