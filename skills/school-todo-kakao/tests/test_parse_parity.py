"""챗봇(chatbot/kakao_chatbot.gs)의 '추가' 날짜 해석·키가 python 빠른입력(inbox.parse_line, sync.make_key)과 같은지 본다.
node가 없으면 건너뛴다."""
import json
import shutil
import subprocess
from datetime import date
from pathlib import Path

import pytest

from schooltodo.inbox import parse_line
from schooltodo.sync import make_key

GS = Path(__file__).resolve().parent.parent / "chatbot" / "kakao_chatbot.gs"
NODE = shutil.which("node")

CASES = [
    "내일 학부모 상담 전화",
    "오늘, 공문 확인",
    "모레 체육대회 물품",
    "글피 출장 복명서",
    "12/3 안전교육 자료",
    "12.3 안전교육",
    "12월 3일 회의",
    "1/5 방학 계획",
    "2027-01-10 연수 신청",
    "2026년 12월 25일 성탄 행사",
    "2/30 없는 날짜 그대로",
    "다음주 화요일 출장 보고",
    "다음 주 금 회의",
    "이번주 수요일 상담",
    "다다음주 월요일 행사",
    "금요일 공문 마감",
    "토요일 주말 행사",
    "장학지도 자료 준비",
    "날짜 없이   띄어쓰기   많은 일",
    "내일",
    "😀 이모지가 들어간 아주 긴 할 일 이름입니다",
]
TODAYS = [date(2026, 11, 28), date(2026, 12, 30), date(2026, 11, 23)]  # 토요일, 연말, 월요일

JS = r"""
const fs = require('fs'), vm = require('vm');
const ctx = { console, Date, JSON, String, Math, Object, Number, Array };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), ctx);
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const out = input.map(([line, today]) => {
  const p = ctx.parseLine_(line, today);
  return p ? [p.date, p.category, p.text, ctx.makeKey_(p.date, p.text)] : null;
});
process.stdout.write(JSON.stringify(out));
"""


@pytest.mark.skipif(NODE is None, reason="node 없음")
def test_chatbot_add_matches_python_inbox():
    pairs = [(line, t.isoformat()) for t in TODAYS for line in CASES]
    res = subprocess.run(
        [NODE, "-e", JS, str(GS)], input=json.dumps(pairs), capture_output=True, text=True, encoding="utf-8", check=True
    )
    got = json.loads(res.stdout)
    for (line, t), g in zip(pairs, got):
        p = parse_line(line, date.fromisoformat(t))
        want = None if p is None else [p.date.isoformat(), p.category, p.text, make_key(p.date, p.text)]
        assert g == want, f"{t} '{line}': 챗봇 {g} != python {want}"
